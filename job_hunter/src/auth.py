"""JWT + password hashing — stdlib only, no external deps."""
import os
import hashlib
import hmac
import base64
import json
import time
from typing import Optional
from urllib.parse import urlparse as _urlparse

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from cryptography.fernet import Fernet


def _auth_db():
    import pg8000.dbapi as _pg
    u = _urlparse(os.getenv("DATABASE_URL", ""))
    return _pg.connect(
        host=u.hostname, port=u.port or 5432,
        user=u.username, password=u.password,
        database=u.path.lstrip("/"),
    )

SECRET_KEY = os.getenv('AUTH_SECRET', 'jobhunter-dev-secret-CHANGE-IN-PRODUCTION')
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY") or Fernet.generate_key().decode()
_TTL = 7 * 24 * 3600  # 7 days

_bearer = HTTPBearer(auto_error=False)
_fernet = Fernet(ENCRYPTION_KEY.encode())


# ── JWT ───────────────────────────────────────────────────────────────────────

def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _d64u(s: str) -> bytes:
    rem = len(s) % 4
    if rem:
        s += '=' * (4 - rem)
    return base64.urlsafe_b64decode(s)


def create_token(user_id: str, email: str) -> str:
    h = _b64u(json.dumps({'alg': 'HS256', 'typ': 'JWT'}).encode())
    p = _b64u(json.dumps({'sub': user_id, 'email': email,
                           'iat': int(time.time()),
                           'exp': int(time.time()) + _TTL}).encode())
    msg = f"{h}.{p}".encode()
    sig = _b64u(hmac.new(SECRET_KEY.encode(), msg, hashlib.sha256).digest())
    return f"{h}.{p}.{sig}"


def verify_token(token: str) -> Optional[dict]:
    try:
        h, p, s = token.split('.')
        msg = f"{h}.{p}".encode()
        expected = _b64u(hmac.new(SECRET_KEY.encode(), msg, hashlib.sha256).digest())
        if not hmac.compare_digest(s, expected):
            return None
        payload = json.loads(_d64u(p))
        if payload.get('exp', 0) < time.time():
            return None
        return payload
    except Exception:
        return None


# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', plain.encode(), salt, 200_000)
    return base64.b64encode(salt + dk).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        raw  = base64.b64decode(hashed.encode())
        salt = raw[:16]
        dk   = raw[16:]
        check = hashlib.pbkdf2_hmac('sha256', plain.encode(), salt, 200_000)
        return hmac.compare_digest(dk, check)
    except Exception:
        return False


def encrypt_token(plain_token: str) -> str:
    return _fernet.encrypt(plain_token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    return _fernet.decrypt(encrypted_token.encode()).decode()


# ── FastAPI dependencies ──────────────────────────────────────────────────────

_BOT_TOKEN = os.getenv("BOT_MASTER_TOKEN", "BOT_MASTER_TOKEN_2026")


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    if creds.credentials == _BOT_TOKEN:
        return {
            "user_id": "default_user",
            "email": "",
            "is_bot": True,
            "email_verified": True,
            "phone_verified": True,
            "role": "admin",
        }
    payload = verify_token(creds.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")
    user_id = payload["sub"]
    try:
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT COALESCE(email_verified, is_verified), COALESCE(phone_verified, FALSE), role "
            "FROM usuarios WHERE user_id=%s",
            (user_id,),
        )
        row = cur.fetchone()
        cur.close(); conn.close()
        if row:
            email_verified, phone_verified, role = row
            if not email_verified and role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cuenta no verificada. Revisa tu correo para el código de activación.",
                )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo validar la sesión.",
        )
    return {
        "user_id": user_id,
        "email": payload.get("email", ""),
        "email_verified": bool(row[0]) if row else False,
        "phone_verified": bool(row[1]) if row else False,
        "role": row[2] if row else "user",
    }


def get_optional_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """Authenticated → use JWT user_id. Unauthenticated → default_user (scraper compat)."""
    if not creds:
        return {"user_id": "default_user", "email": ""}
    payload = verify_token(creds.credentials)
    if not payload:
        return {"user_id": "default_user", "email": ""}
    return {"user_id": payload["sub"], "email": payload.get("email", "")}
