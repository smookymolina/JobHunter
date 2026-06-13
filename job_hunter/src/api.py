import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import logging
import random
import uuid
import pg8000.dbapi as _pg8000
from urllib.parse import urlparse as _urlparse
import os
import shutil
import subprocess
import time
from contextlib import asynccontextmanager

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO)
_log = logging.getLogger("api")

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field

from auth import (
    get_current_user,
    get_optional_user,
    hash_password,
    verify_password,
    create_token,
    encrypt_token,
    decrypt_token,
)
from gemini_engine import (
    TEMPLATES_DIR, DB_PATH, OUTPUTS_DIR, CONTEXT_DIR,
    get_user_outputs_dir, get_user_profile_path,
    compilar_pdf, evaluar_compatibilidad_rapida, generar_terminos_busqueda,
    clear_compat_cache,
)
from watcher import DeepHealthWatcher, deep_health_check

try:
    import PyPDF2 as _pypdf2
    _HAS_PYPDF2 = True
except ImportError:
    _HAS_PYPDF2 = False

_DATA_DIR           = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data'))
PERFIL_MAESTRO_PATH = os.path.join(_DATA_DIR, 'perfil_maestro.json')   # default_user legacy path

_scrape_status: dict = {"running": False, "last": None}


# ── DB helpers ────────────────────────────────────────────────────────────────

def _db():
    _u = _urlparse(os.getenv('DATABASE_URL'))
    return _pg8000.connect(host=_u.hostname, port=_u.port or 5432, user=_u.username, password=_u.password, database=_u.path.lstrip('/'))


def _ts(v):
    """Convert datetime to ISO string; pass through other values unchanged."""
    if v is None:
        return None
    return v.strftime('%Y-%m-%d %H:%M:%S') if hasattr(v, 'strftime') else v


def _row_dict(cols, row):
    return {k: _ts(v) for k, v in zip(cols, row)}


def _set_status(vid: int, status: str, user_id: str = 'default_user'):
    conn = _db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE vacantes SET status=%s WHERE id=%s AND user_id=%s",
        (status, vid, user_id)
    )
    conn.commit()
    cur.close()
    conn.close()


def _is_blacklisted(conn, enlace: str, user_id: str = 'default_user') -> bool:
    if not enlace:
        return False
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM vacantes_eliminadas WHERE enlace=%s AND user_id=%s",
        (enlace, user_id)
    )
    result = cur.fetchone()
    cur.close()
    return result is not None


def _blacklist_add(conn, enlace: str, titulo: str, user_id: str = 'default_user'):
    if not enlace:
        return
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO vacantes_eliminadas (user_id, enlace, titulo) VALUES (%s,%s,%s) "
        "ON CONFLICT (user_id, enlace) DO NOTHING",
        (user_id, enlace, titulo or "")
    )
    conn.commit()
    cur.close()


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    conn = _db()
    cur = conn.cursor()
    cur.execute("SELECT role FROM usuarios WHERE user_id=%s", (current_user["user_id"],))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row or row[0] != 'admin':
        raise HTTPException(status_code=403, detail="Acceso restringido a administradores.")
    return current_user


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    app.state.bot_last_heartbeat = 0.0
    app.state.mcp_last_heartbeat = 0.0
    _mc = _db()
    try:
        _cur = _mc.cursor()
        _log.info("Iniciando validación de esquema de base de datos...")
        _cur.execute("""
            CREATE TABLE IF NOT EXISTS vacantes (
                id                SERIAL PRIMARY KEY,
                user_id           VARCHAR(50) NOT NULL DEFAULT 'default_user',
                titulo            TEXT NOT NULL,
                empresa           TEXT,
                enlace            TEXT,
                requerimientos    TEXT,
                compatibilidad    TEXT DEFAULT 'Nula',
                status            TEXT DEFAULT 'No_Creado',
                fecha_registro    TIMESTAMP DEFAULT NOW(),
                fecha_postulacion TIMESTAMP,
                favorito          INTEGER DEFAULT 0
            )
        """)
        _cur.execute("""
            CREATE TABLE IF NOT EXISTS vacantes_eliminadas (
                id                SERIAL PRIMARY KEY,
                user_id           VARCHAR(50) NOT NULL DEFAULT 'default_user',
                enlace            TEXT NOT NULL,
                titulo            TEXT,
                fecha_eliminacion TIMESTAMP DEFAULT NOW(),
                UNIQUE(user_id, enlace)
            )
        """)
        _cur.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id            UUID PRIMARY KEY,
                type              VARCHAR(50) NOT NULL,
                user_id           VARCHAR(50) NOT NULL,
                payload           JSONB NOT NULL,
                status            VARCHAR(50) NOT NULL,
                priority          INTEGER DEFAULT 1,
                retries_current   INTEGER DEFAULT 0,
                retries_max       INTEGER DEFAULT 3,
                idempotency_key   VARCHAR(255) UNIQUE,
                correlation_id    VARCHAR(255),
                created_at        TIMESTAMP DEFAULT NOW(),
                dispatched_at     TIMESTAMP,
                started_at        TIMESTAMP,
                finished_at       TIMESTAMP,
                failed_at         TIMESTAMP,
                error_context     JSONB
            )
        """)
        _cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
        _cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id)")
        _cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'vacantes'
        """)
        existing_cols = {r[0] for r in _cur.fetchall()}
        if 'fecha_postulacion' not in existing_cols:
            _log.info("Migración: Añadiendo columna fecha_postulacion a vacantes")
            _cur.execute("ALTER TABLE vacantes ADD COLUMN fecha_postulacion TIMESTAMP")
        if 'favorito' not in existing_cols:
            _log.info("Migración: Añadiendo columna favorito a vacantes")
            _cur.execute("ALTER TABLE vacantes ADD COLUMN favorito INTEGER DEFAULT 0")
        if 'user_id' not in existing_cols:
            _log.info("Migración: Añadiendo columna user_id a vacantes")
            _cur.execute("ALTER TABLE vacantes ADD COLUMN user_id VARCHAR(50) NOT NULL DEFAULT 'default_user'")
        # usuarios table
        _cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id                       SERIAL PRIMARY KEY,
                user_id                  VARCHAR(50) UNIQUE NOT NULL,
                email                    VARCHAR(255) UNIQUE NOT NULL,
                hashed_password          TEXT NOT NULL,
                tier                     VARCHAR(20) DEFAULT 'free' NOT NULL,
                role                     VARCHAR(20) DEFAULT 'user' NOT NULL,
                telegram_token_encrypted VARCHAR(500) DEFAULT NULL,
                vacantes_limite          INT DEFAULT 5 NOT NULL,
                latex_limite             INT DEFAULT 3 NOT NULL,
                latex_generados          INT DEFAULT 0 NOT NULL,
                created_at               TIMESTAMP DEFAULT NOW()
            )
        """)
        # Migrate: add columns to existing installations
        _cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='usuarios'")
        _usr_cols = {r[0] for r in _cur.fetchall()}
        if 'tier' not in _usr_cols:
            _cur.execute("ALTER TABLE usuarios ADD COLUMN tier VARCHAR(20) DEFAULT 'free' NOT NULL")
        if 'role' not in _usr_cols:
            _cur.execute("ALTER TABLE usuarios ADD COLUMN role VARCHAR(20) DEFAULT 'user' NOT NULL")
        if 'telegram_token_encrypted' not in _usr_cols:
            _cur.execute("ALTER TABLE usuarios ADD COLUMN telegram_token_encrypted VARCHAR(500) DEFAULT NULL")
        if 'vacantes_limite' not in _usr_cols:
            _cur.execute("ALTER TABLE usuarios ADD COLUMN vacantes_limite INT DEFAULT 5 NOT NULL")
        if 'latex_limite' not in _usr_cols:
            _cur.execute("ALTER TABLE usuarios ADD COLUMN latex_limite INT DEFAULT 3 NOT NULL")
        if 'latex_generados' not in _usr_cols:
            _cur.execute("ALTER TABLE usuarios ADD COLUMN latex_generados INT DEFAULT 0 NOT NULL")
        if 'is_verified' not in _usr_cols:
            _cur.execute("ALTER TABLE usuarios ADD COLUMN is_verified BOOLEAN DEFAULT FALSE NOT NULL")
        if 'verification_code' not in _usr_cols:
            _cur.execute("ALTER TABLE usuarios ADD COLUMN verification_code VARCHAR(10) DEFAULT NULL")
        if 'phone_number' not in _usr_cols:
            _cur.execute("ALTER TABLE usuarios ADD COLUMN phone_number VARCHAR(20) DEFAULT NULL")
        # Drop any legacy CHECK constraint on vacantes.status (blocks "Entrevista")
        _cur.execute("""
            DO $$
            DECLARE cname text;
            BEGIN
                FOR cname IN
                    SELECT tc.constraint_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.check_constraints cc
                         ON tc.constraint_name = cc.constraint_name
                        AND tc.constraint_schema = cc.constraint_schema
                    WHERE tc.table_name = 'vacantes'
                      AND tc.constraint_type = 'CHECK'
                      AND cc.check_clause LIKE '%status%'
                LOOP
                    EXECUTE 'ALTER TABLE vacantes DROP CONSTRAINT IF EXISTS ' || quote_ident(cname);
                END LOOP;
            END $$;
        """)
        # Seed default_user — keeps link to the 33 migrated vacantes
        _cur.execute("SELECT id FROM usuarios WHERE user_id='default_user'")
        if not _cur.fetchone():
            _log.info("Sembrando usuario por defecto (default_user)")
            _cur.execute(
                "INSERT INTO usuarios (user_id, email, hashed_password) VALUES ('default_user', %s, %s)",
                ('test@jobhunter.com', hash_password('jobhunter123'))
            )
        # God Mode: default_user always admin + unlimited credits
        _cur.execute(
            "UPDATE usuarios SET tier='pro', role='admin', vacantes_limite=9999, latex_limite=9999 "
            "WHERE user_id='default_user'"
        )
        # Elevate founder account + unlimited credits
        _cur.execute(
            "UPDATE usuarios SET role='admin', vacantes_limite=9999, latex_limite=9999 "
            "WHERE email='speedysmoking@gmail.com'"
        )
        # All admin/default accounts are pre-verified; clear pending OTPs for them
        _cur.execute(
            "UPDATE usuarios SET is_verified=TRUE, verification_code=NULL "
            "WHERE role='admin' OR user_id='default_user'"
        )
        _mc.commit()
        _cur.close()
        _log.info("Validación de esquema completada exitosamente.")
    except Exception as e:
        _log.error("Fallo crítico durante la inicialización de la DB: %s", e)
        # We don't raise here to allow the API to start even with DB issues, 
        # but subsequent requests will fail gracefully via _db() retries.
    finally:
        _mc.close()
    app.state.health_watcher = DeepHealthWatcher(interval_seconds=20, dry_run=False)
    app.state.health_watcher.start()
    # Sync inmediato al arrancar: corrige huérfanos Revisado_IA sin archivos
    app.state.health_watcher.check_now(dry_run=False)
    yield
    watcher = getattr(app.state, "health_watcher", None)
    if watcher:
        watcher.stop()


app = FastAPI(title="Job Hunter API", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ────────────────────────────────────────────────────────────────────

class VacanteCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    empresa: str = Field(default="Desconocida", max_length=100)
    enlace: str = Field(default="", max_length=500)
    requerimientos: str = Field(default="", max_length=5000)
    compatibilidad: str = Field(default="Nula")
    user_id: str | None = Field(default=None, description="Internal: override user (only honored with BOT_MASTER_TOKEN)")


class VacanteBulkItem(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    empresa: str = Field(default="Desconocida", max_length=100)
    enlace: str = Field(default="", max_length=500)
    requerimientos: str = Field(default="", max_length=5000)


class FiltrosBusqueda(BaseModel):
    ubicacion:  str            = Field(default="", description="Ciudad o estado. Soporta alias: CDMX, GDL, MTY, NL, EdomEx, etc.")
    modalidad:  str            = Field(default="any", description="any | remoto | hibrido | presencial")
    pais:       str            = Field(default="Mexico", description="Mexico | España | Argentina | Colombia | Internacional")
    min_salary: int | None     = Field(default=None, description="Salario mensual mínimo en MXN (opcional)")
    platforms:  list[str] | None = Field(default=None, description="Plataformas: computrabajo, occ, indeed, bumeran, getonbrd, remotive, linkedin")


class ScrapeRequest(BaseModel):
    cantidad:   int            = Field(ge=1, le=200, description="Vacantes a extraer (máximo global)")
    terminos:   list[str] | None = Field(default=None, description="Términos de búsqueda (None = usar perfil_maestro.json)")
    filtros:    FiltrosBusqueda  = Field(default_factory=FiltrosBusqueda)
    min_compat: str            = Field(default="Media", description="Compatibilidad mínima: Alta | Media | Baja | Nula")


class TierUpdate(BaseModel):
    tier: str


class TelegramTokenSetRequest(BaseModel):
    password: str = Field(min_length=1)
    telegram_token: str = Field(min_length=1, max_length=500)


class TelegramTokenRevealRequest(BaseModel):
    password: str = Field(min_length=1)


# ── Heartbeats ────────────────────────────────────────────────────────────────

@app.post("/bot/heartbeat")
def bot_heartbeat():
    app.state.bot_last_heartbeat = time.time()
    return {"ok": True}


@app.post("/mcp/heartbeat")
def mcp_heartbeat():
    app.state.mcp_last_heartbeat = time.time()
    return {"ok": True}


@app.get("/")
def root_health():
    bot_last = getattr(app.state, "bot_last_heartbeat", 0.0)
    mcp_last = getattr(app.state, "mcp_last_heartbeat", 0.0)
    return {
        "ok": True,
        "service": "job-hunter-api",
        "scrape": dict(_scrape_status),
        "bot_active": (time.time() - bot_last) < 45,
        "mcp_active": (time.time() - mcp_last) < 45,
    }


# ── Auth endpoints ────────────────────────────────────────────────────────────

@app.post("/auth/login")
async def login(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido.")
    email    = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email y contraseña requeridos.")
    conn = _db()
    cur  = conn.cursor()
    cur.execute("SELECT user_id, hashed_password FROM usuarios WHERE email=%s", (email,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row or not verify_password(password, row[1]):
        raise HTTPException(status_code=401, detail="Credenciales inválidas.")
    token = create_token(row[0], email)
    return {"access_token": token, "token_type": "bearer", "user_id": row[0]}


@app.post("/auth/register", status_code=201)
async def register(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido.")
    email    = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    phone    = (body.get("phone") or "").strip() or None
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email y contraseña requeridos.")
    conn = _db()
    cur  = conn.cursor()
    cur.execute("SELECT id FROM usuarios WHERE email=%s", (email,))
    if cur.fetchone():
        cur.close(); conn.close()
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")
    user_id = uuid.uuid4().hex
    otp = str(random.randint(100000, 999999))
    cur.execute(
        "INSERT INTO usuarios (user_id, email, hashed_password, verification_code, phone_number) "
        "VALUES (%s, %s, %s, %s, %s)",
        (user_id, email, hash_password(password), otp, phone)
    )
    conn.commit()
    cur.close(); conn.close()
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(get_user_profile_path(user_id), "w", encoding="utf-8") as f:
        json.dump({"nombre": "", "titulo": "", "skills": []}, f)
    from notifier_agent import NotificationAgent
    agent = NotificationAgent()
    background_tasks.add_task(agent.send_email_otp, email, otp)
    if phone:
        background_tasks.add_task(agent.trigger_whatsapp_bot, phone, otp)
    return JSONResponse(status_code=201, content={
        "ok": True, "user_id": user_id,
        "msg": "Cuenta creada. Revisa tu correo para el código de verificación.",
    })


@app.post("/auth/verify")
async def verify_account(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido.")
    email = (body.get("email") or "").strip().lower()
    code  = str(body.get("code") or "").strip()
    if not email or not code:
        raise HTTPException(status_code=400, detail="Email y código requeridos.")
    conn = _db()
    cur  = conn.cursor()
    cur.execute("SELECT user_id, verification_code FROM usuarios WHERE email=%s", (email,))
    row = cur.fetchone()
    if not row or row[1] != code:
        cur.close(); conn.close()
        raise HTTPException(status_code=401, detail="Código incorrecto o expirado.")
    user_id = row[0]
    cur.execute(
        "UPDATE usuarios SET is_verified=TRUE, verification_code=NULL WHERE user_id=%s",
        (user_id,)
    )
    conn.commit()
    cur.close(); conn.close()
    token = create_token(user_id, email)
    return {"ok": True, "access_token": token, "token_type": "bearer", "user_id": user_id}


@app.post("/auth/resend")
async def resend_otp(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido.")
    email = (body.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email requerido.")
    conn = _db()
    cur  = conn.cursor()
    cur.execute("SELECT user_id, is_verified FROM usuarios WHERE email=%s", (email,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="Email no registrado.")
    if row[1]:
        cur.close(); conn.close()
        return {"ok": True, "msg": "Cuenta ya verificada."}
    new_otp = str(random.randint(100000, 999999))
    cur.execute("UPDATE usuarios SET verification_code=%s WHERE user_id=%s", (new_otp, row[0]))
    conn.commit()
    cur.close(); conn.close()
    from notifier_agent import NotificationAgent
    background_tasks.add_task(NotificationAgent().send_email_otp, email, new_otp)
    return {"ok": True, "msg": "Nuevo código enviado."}


@app.get("/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    conn = _db()
    cur = conn.cursor()
    cur.execute(
        "SELECT email, tier, role, telegram_token_encrypted, vacantes_limite, latex_limite, latex_generados "
        "FROM usuarios WHERE user_id=%s", (uid,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return {
        "user_id": uid, "email": row[0], "tier": row[1], "role": row[2],
        "has_telegram_bot": bool(row[3]),
        "vacantes_limite": row[4], "latex_limite": row[5], "latex_generados": row[6],
    }


@app.post("/perfil/telegram/set")
def set_telegram_token(body: TelegramTokenSetRequest, current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    conn = _db()
    cur = conn.cursor()
    cur.execute("SELECT hashed_password FROM usuarios WHERE user_id=%s", (uid,))
    row = cur.fetchone()
    if not row or not verify_password(body.password, row[0]):
        cur.close()
        conn.close()
        raise HTTPException(status_code=401, detail="Contraseña incorrecta.")
    encrypted = encrypt_token(body.telegram_token.strip())
    cur.execute(
        "UPDATE usuarios SET telegram_token_encrypted=%s WHERE user_id=%s",
        (encrypted, uid),
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"ok": True}


@app.post("/perfil/telegram/reveal")
def reveal_telegram_token(body: TelegramTokenRevealRequest, current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    conn = _db()
    cur = conn.cursor()
    cur.execute("SELECT hashed_password, telegram_token_encrypted FROM usuarios WHERE user_id=%s", (uid,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    if not verify_password(body.password, row[0]):
        cur.close()
        conn.close()
        raise HTTPException(status_code=401, detail="Contraseña incorrecta.")
    if not row[1]:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Token de Telegram no configurado.")
    token = decrypt_token(row[1])
    cur.close()
    conn.close()
    return {"telegram_token": token}


@app.get("/bot/telegram-token")
def get_bot_telegram_token(current_user: dict = Depends(get_current_user)):
    """Internal: bot.py calls this at startup to auto-load the user's Telegram token.
    Authenticated via BOT_MASTER_TOKEN — no password required (internal service only)."""
    uid = current_user["user_id"]
    conn = _db()
    cur = conn.cursor()
    cur.execute("SELECT telegram_token_encrypted FROM usuarios WHERE user_id=%s", (uid,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row or not row[0]:
        raise HTTPException(
            status_code=404,
            detail="Token de Telegram no configurado. Guárdalo en Perfil → Configurar Token."
        )
    return {"telegram_token": decrypt_token(row[0]), "user_id": uid}


# ── Perfil Maestro helpers ────────────────────────────────────────────────────

def _regenerate_mi_perfil(data: dict) -> None:
    os.makedirs(CONTEXT_DIR, exist_ok=True)
    habs = data.get("habilidades", {})
    skill_lines = [
        f"- **{cat.replace('_', ' ').title()}**: {', '.join(vals)}"
        for cat, vals in habs.items() if vals
    ]
    exp_lines = []
    for e in data.get("experiencia", []):
        exp_lines.append(f"### {e.get('puesto','')} — {e.get('empresa','')} ({e.get('periodo','')})")
        for l in e.get("logros", []):
            exp_lines.append(f"- {l}")
    edu_lines = [
        f"- **{e.get('titulo','')}** — {e.get('institucion','')} ({e.get('anio','')})"
        for e in data.get("educacion", [])
    ]
    proj_lines = []
    for p in data.get("proyectos", []):
        proj_lines.append(f"### {p.get('nombre','')}")
        proj_lines.append(p.get("descripcion",""))
        if p.get("tecnologias"):
            proj_lines.append(f"Tecnologías: {', '.join(p['tecnologias'])}")

    md = "\n".join([
        f"# {data.get('nombre','')} {data.get('apellidos','')}",
        f"**{data.get('titulo_profesional','')}**",
        f"",
        f"Email: {data.get('email','')}  |  Tel: {data.get('telefono','')}",
        f"Ubicación: {data.get('ubicacion','')}  |  LinkedIn: {data.get('linkedin','')}  |  GitHub: {data.get('github','')}",
        f"",
        f"## Resumen",
        data.get("resumen", ""),
        f"",
        f"## Habilidades",
        *skill_lines,
        f"",
        f"## Experiencia",
        *exp_lines,
        f"",
        f"## Educación",
        *edu_lines,
        f"",
        f"## Proyectos",
        *proj_lines,
    ])
    with open(os.path.join(CONTEXT_DIR, "mi_perfil.md"), "w", encoding="utf-8") as f:
        f.write(md)


# ── Endpoint constants ────────────────────────────────────────────────────────

_VCOLS = ["id", "titulo", "empresa", "enlace", "requerimientos", "compatibilidad", "status", "fecha_registro", "fecha_postulacion", "favorito"]
_VSEL  = ("SELECT id, titulo, empresa, enlace, requerimientos, compatibilidad, status, "
           "fecha_registro, fecha_postulacion, favorito FROM vacantes")


# ── Vacantes endpoints ────────────────────────────────────────────────────────

@app.get("/vacantes")
def listar_vacantes(limit: int = 50, status: str | None = None, current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    conn = _db()
    cur = conn.cursor()
    if status:
        cur.execute(
            f"{_VSEL} WHERE user_id=%s AND status=%s ORDER BY id DESC LIMIT %s",
            (uid, status, limit)
        )
    else:
        cur.execute(
            f"{_VSEL} WHERE user_id=%s ORDER BY id DESC LIMIT %s",
            (uid, limit)
        )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    result = [_row_dict(_VCOLS, r) for r in rows]
    _log.info("GET /vacantes → %d filas (status=%s, limit=%d, uid=%s)", len(result), status or "all", limit, uid)
    return JSONResponse(content=result, headers={"Cache-Control": "no-store"})


@app.get("/vacantes/eliminadas")
def listar_eliminadas(limit: int = 200, current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    conn = _db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, enlace, titulo, fecha_eliminacion FROM vacantes_eliminadas "
        "WHERE user_id=%s ORDER BY id DESC LIMIT %s",
        (uid, limit)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    cols = ["id", "enlace", "titulo", "fecha_eliminacion"]
    return JSONResponse(content=[_row_dict(cols, r) for r in rows], headers={"Cache-Control": "no-store"})


@app.delete("/vacantes/eliminadas/{eid}")
def restaurar_eliminada(eid: int, current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    conn = _db()
    cur = conn.cursor()
    cur.execute("DELETE FROM vacantes_eliminadas WHERE id=%s AND user_id=%s", (eid, uid))
    conn.commit()
    changes = cur.rowcount
    cur.close()
    conn.close()
    if not changes:
        raise HTTPException(status_code=404, detail=f"Entrada #{eid} no encontrada en el archivo.")
    return {"ok": True, "id": eid}


@app.get("/vacantes/{vid}")
def detalle_vacante(vid: int, current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    conn = _db()
    cur = conn.cursor()
    cur.execute(f"{_VSEL} WHERE id=%s AND user_id=%s", (vid, uid))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail=f"Vacante #{vid} no encontrada.")
    return _row_dict(_VCOLS, row)


@app.patch("/vacantes/{vid}/status")
def cambiar_status(vid: int, body: dict, current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    VALIDOS = {"No_Creado", "En_Proceso", "Revisado_IA", "Listo_Manual", "Requiere_Correccion", "Entrevista"}
    nuevo = body.get("status", "")
    if nuevo not in VALIDOS:
        raise HTTPException(status_code=400, detail=f"Status inválido. Usa: {VALIDOS}")
    conn = _db()
    cur = conn.cursor()
    if nuevo == "Listo_Manual":
        cur.execute(
            "UPDATE vacantes SET status=%s, fecha_postulacion=NOW() WHERE id=%s AND user_id=%s",
            (nuevo, vid, uid)
        )
    else:
        cur.execute(
            "UPDATE vacantes SET status=%s WHERE id=%s AND user_id=%s",
            (nuevo, vid, uid)
        )
    conn.commit()
    changes = cur.rowcount
    cur.close()
    conn.close()
    if not changes:
        raise HTTPException(status_code=404, detail=f"Vacante #{vid} no encontrada.")
    return {"ok": True, "id": vid, "status": nuevo}


@app.post("/vacantes/{vid}/sync")
def sync_vacante(vid: int, current_user: dict = Depends(get_current_user)):
    uid      = current_user["user_id"]
    out_dir  = get_user_outputs_dir(uid)
    pdf_path = os.path.join(out_dir, f"cv_vacante_{vid}.pdf")
    tex_path = os.path.join(out_dir, f"cv_vacante_{vid}.tex")
    if os.path.exists(pdf_path):
        _set_status(vid, "Revisado_IA", uid)
        return {"ok": True, "synced": True, "status": "Revisado_IA", "pdf": pdf_path, "tex_exists": os.path.exists(tex_path)}
    if os.path.exists(tex_path):
        try:
            result_pdf = compilar_pdf(tex_path)
            _set_status(vid, "Revisado_IA", uid)
            return {"ok": True, "synced": True, "status": "Revisado_IA", "pdf": result_pdf}
        except Exception as e:
            _set_status(vid, "Requiere_Correccion", uid)
            return {"ok": False, "synced": False, "status": "Requiere_Correccion", "error": str(e)}
    return {"ok": False, "synced": False, "detail": f"No existe .tex ni .pdf para vacante #{vid}."}


@app.get("/debug/sync-health")
def debug_sync_health():
    watcher = getattr(app.state, "health_watcher", None)
    snapshot = deep_health_check(dry_run=True)
    bot_last = getattr(app.state, "bot_last_heartbeat", 0.0)
    mcp_last = getattr(app.state, "mcp_last_heartbeat", 0.0)
    watcher_snapshot = (
        watcher.snapshot() if watcher
        else {"running": False, "interval_seconds": None, "last_error": "watcher no inicializado", "last_snapshot": {}}
    )
    snapshot["watcher"] = watcher_snapshot
    snapshot["bot_active"] = (time.time() - bot_last) < 45
    snapshot["mcp_active"] = (time.time() - mcp_last) < 45
    return JSONResponse(content=snapshot, headers={"Cache-Control": "no-store"})


@app.patch("/vacantes/{vid}/compatibilidad")
def cambiar_compatibilidad(vid: int, body: dict, current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    VALIDOS = {"Alta", "Media", "Baja", "Nula"}
    nuevo = body.get("compatibilidad", "")
    if nuevo not in VALIDOS:
        raise HTTPException(status_code=400, detail=f"Compatibilidad inválida. Usa: {VALIDOS}")
    conn = _db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE vacantes SET compatibilidad=%s WHERE id=%s AND user_id=%s",
        (nuevo, vid, uid)
    )
    conn.commit()
    changes = cur.rowcount
    cur.close()
    conn.close()
    if not changes:
        raise HTTPException(status_code=404, detail=f"Vacante #{vid} no encontrada.")
    return {"ok": True, "id": vid, "compatibilidad": nuevo}


@app.patch("/vacantes/{vid}/favorito")
def toggle_favorito(vid: int, current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    conn = _db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE vacantes SET favorito = 1 - COALESCE(favorito,0) WHERE id=%s AND user_id=%s",
        (vid, uid)
    )
    conn.commit()
    cur.execute("SELECT favorito FROM vacantes WHERE id=%s AND user_id=%s", (vid, uid))
    nuevo = cur.fetchone()
    cur.close()
    conn.close()
    if not nuevo:
        raise HTTPException(status_code=404, detail=f"Vacante #{vid} no encontrada.")
    return {"ok": True, "id": vid, "favorito": bool(nuevo[0])}


# ── LaTeX / PDF endpoints ─────────────────────────────────────────────────────

@app.get("/latex/{vid}", response_class=PlainTextResponse)
def get_latex(vid: int, current_user: dict = Depends(get_current_user)):
    uid      = current_user["user_id"]
    tex_path = os.path.join(get_user_outputs_dir(uid), f"cv_vacante_{vid}.tex")
    if not os.path.exists(tex_path):
        raise HTTPException(status_code=404, detail=f"LaTeX no encontrado para vacante #{vid}.")
    with open(tex_path, "r", encoding="utf-8") as f:
        return f.read()


@app.post("/latex/{vid}")
async def save_latex(vid: int, request: Request, current_user: dict = Depends(get_current_user)):
    uid         = current_user["user_id"]
    tex_content = (await request.body()).decode("utf-8")
    if not tex_content.strip():
        raise HTTPException(status_code=400, detail="El cuerpo LaTeX está vacío.")
    out_dir  = get_user_outputs_dir(uid)
    tex_path = os.path.join(out_dir, f"cv_vacante_{vid}.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(tex_content)
    pdf_path = None
    error: str | None = None
    try:
        pdf_path = compilar_pdf(tex_path)
    except Exception as e:
        error = str(e)
    if pdf_path and os.path.exists(pdf_path):
        _set_status(vid, "Revisado_IA", uid)
        return {"ok": True, "pdf": True, "tex_path": tex_path, "pdf_path": pdf_path}
    _set_status(vid, "Requiere_Correccion", uid)
    return {"ok": True, "pdf": False, "error": error or "pdflatex no generó el archivo."}


@app.post("/upload_template")
async def upload_template(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.tex'):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .tex")
    dest = os.path.join(TEMPLATES_DIR, 'mi_estilo.tex')
    with open(dest, 'wb') as out:
        shutil.copyfileobj(file.file, out)
    return {"ok": True, "mensaje": "Plantilla visual actualizada con éxito.", "ruta": dest}


@app.post("/generar_cv/{vid}")
async def generar_cv_endpoint(vid: int, current_user: dict = Depends(get_current_user)):
    import asyncio
    import functools
    from gemini_engine import generar_y_compilar
    from inspector import evaluar_cv

    uid  = current_user["user_id"]

    # LaTeX credit gate
    _cv_conn = _db()
    _cv_cur  = _cv_conn.cursor()
    _cv_cur.execute("SELECT latex_limite, latex_generados FROM usuarios WHERE user_id=%s", (uid,))
    _cv_row = _cv_cur.fetchone()
    _cv_cur.close()
    _cv_conn.close()
    if _cv_row and _cv_row[1] >= _cv_row[0]:
        raise HTTPException(
            status_code=403,
            detail="Límite de generaciones LaTeX agotado. Adquiere un paquete para continuar."
        )

    loop = asyncio.get_event_loop()
    try:
        tex_path, pdf_path = await loop.run_in_executor(
            None, functools.partial(generar_y_compilar, vid, uid)
        )
    except Exception as e:
        _set_status(vid, "Requiere_Correccion", uid)
        raise HTTPException(status_code=500, detail=f"Error generando CV: {e}")

    if not tex_path:
        raise HTTPException(status_code=500, detail="Falló la generación del LaTeX.")

    auditoria = await loop.run_in_executor(None, evaluar_cv, vid, tex_path, uid)
    tiene_pdf = bool(pdf_path and os.path.exists(pdf_path))

    # Increment LaTeX counter
    _inc_conn = _db()
    _inc_cur  = _inc_conn.cursor()
    _inc_cur.execute("UPDATE usuarios SET latex_generados = latex_generados + 1 WHERE user_id=%s", (uid,))
    _inc_conn.commit()
    _inc_cur.close()
    _inc_conn.close()

    return {
        "ok":         True,
        "aprobado":   auditoria["aprobado"],
        "comentarios":auditoria["comentarios"],
        "pdf":        tiene_pdf,
        "tex_path":   tex_path,
        "pdf_path":   pdf_path if tiene_pdf else None,
    }


# ── CRUD vacantes ─────────────────────────────────────────────────────────────

@app.post("/vacantes")
def crear_vacante(body: VacanteCreate, current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    if current_user.get("is_bot") and body.user_id:
        uid = body.user_id
    enlace = body.enlace.strip()
    conn = _db()
    if _is_blacklisted(conn, enlace, uid):
        conn.close()
        return JSONResponse(status_code=409, content={"ok": False, "detail": "Vacante eliminada previamente", "blacklisted": True})
    cur = conn.cursor()
    # Strict dedup: title+company in vacantes UNION title in vacantes_eliminadas
    _nt = body.titulo.strip().lower()
    _ne = (body.empresa.strip() or "desconocida").lower()
    cur.execute(
        """SELECT 1 FROM vacantes
           WHERE user_id=%s AND LOWER(titulo)=%s AND LOWER(empresa)=%s
           UNION
           SELECT 1 FROM vacantes_eliminadas
           WHERE user_id=%s AND LOWER(titulo)=%s
           LIMIT 1""",
        (uid, _nt, _ne, uid, _nt)
    )
    if cur.fetchone():
        cur.close(); conn.close()
        return JSONResponse(status_code=409, content={"ok": False, "detail": "Vacante duplicada (título+empresa)", "blacklisted": False})
    # Paywall: credit-based vacante limit
    cur.execute("SELECT vacantes_limite FROM usuarios WHERE user_id=%s", (uid,))
    _lim = (cur.fetchone() or [5])[0]
    cur.execute("SELECT COUNT(*) FROM vacantes WHERE user_id=%s", (uid,))
    if cur.fetchone()[0] >= _lim:
        cur.close()
        conn.close()
        return JSONResponse(status_code=403, content={"ok": False, "detail": "Límite de vacantes alcanzado. Adquiere un paquete para continuar."})
    cur.execute("SELECT id FROM vacantes WHERE enlace=%s AND user_id=%s", (enlace, uid))
    existing = cur.fetchone()
    if existing:
        cur.close()
        conn.close()
        return JSONResponse(status_code=409, content={"ok": False, "detail": "Vacante duplicada", "id": existing[0]})

    reqs   = body.requerimientos.strip()[:5000]
    compat = body.compatibilidad if body.compatibilidad in {"Alta", "Media", "Baja"} else None
    if compat is None and reqs:
        compat = evaluar_compatibilidad_rapida(reqs, uid)
    compat = compat or "Nula"

    cur.execute(
        "INSERT INTO vacantes (user_id, titulo, empresa, enlace, requerimientos, compatibilidad, status) "
        "VALUES (%s,%s,%s,%s,%s,%s,'No_Creado') RETURNING id",
        (
            uid,
            body.titulo.strip()[:200],
            body.empresa.strip()[:100] or "Desconocida",
            enlace,
            reqs,
            compat,
        )
    )
    row_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return {"ok": True, "id": row_id, "compatibilidad": compat}


@app.post("/vacantes/bulk")
def crear_vacantes_bulk(items: list[VacanteBulkItem], current_user: dict = Depends(get_current_user)):
    if not items:
        raise HTTPException(status_code=400, detail="El arreglo JSON esta vacio.")

    uid = current_user["user_id"]
    conn = _db()
    cur = conn.cursor()
    # Paywall: credit-based vacante limit
    cur.execute("SELECT vacantes_limite FROM usuarios WHERE user_id=%s", (uid,))
    _lim = (cur.fetchone() or [5])[0]
    cur.execute("SELECT COUNT(*) FROM vacantes WHERE user_id=%s", (uid,))
    if cur.fetchone()[0] >= _lim:
        cur.close()
        conn.close()
        return JSONResponse(status_code=403, content={"ok": False, "detail": "Límite de vacantes alcanzado. Adquiere un paquete para continuar."})
    insertados = 0
    duplicados = 0
    omitidos = 0
    ids: list[int] = []
    try:
        for item in items:
            enlace_b = item.enlace.strip()
            if _is_blacklisted(conn, enlace_b, uid):
                omitidos += 1
                continue
            reqs_b = item.requerimientos.strip()[:5000]
            compat_b = evaluar_compatibilidad_rapida(reqs_b, uid) if reqs_b else "Nula"
            cur.execute(
                "INSERT INTO vacantes (user_id, titulo, empresa, enlace, requerimientos, compatibilidad, status) "
                "VALUES (%s,%s,%s,%s,%s,%s,'No_Creado') ON CONFLICT (user_id, enlace) DO NOTHING RETURNING id",
                (
                    uid,
                    item.titulo.strip()[:200],
                    item.empresa.strip()[:100] or "Desconocida",
                    enlace_b,
                    reqs_b,
                    compat_b,
                )
            )
            conn.commit()
            row = cur.fetchone()
            if row:
                insertados += 1
                ids.append(row[0])
            else:
                duplicados += 1
    finally:
        cur.close()
        conn.close()

    return {
        "ok": True,
        "insertadas": insertados,
        "duplicadas": duplicados,
        "omitidas_blacklist": omitidos,
        "ids": ids,
        "status": "No_Creado",
    }


@app.get("/pdf/{vid}")
def descargar_pdf(vid: int, download: bool = False, current_user: dict = Depends(get_current_user)):
    uid      = current_user["user_id"]
    pdf_path = os.path.join(get_user_outputs_dir(uid), f"cv_vacante_{vid}.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF no encontrado.")
    disposition = "attachment" if download else "inline"
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="cv_vacante_{vid}.pdf"',
            "X-Frame-Options": "SAMEORIGIN",
            "Content-Security-Policy": "frame-ancestors 'self' http://localhost:3000",
        },
    )


@app.get("/download/cv/{vid}")
def download_cv_secure(vid: int, current_user: dict = Depends(get_current_user)):
    """Descarga protegida: valida ownership antes de entregar el PDF."""
    uid = current_user["user_id"]
    conn = _db()
    cur  = conn.cursor()
    cur.execute("SELECT id FROM vacantes WHERE id=%s AND user_id=%s", (vid, uid))
    exists = cur.fetchone()
    cur.close()
    conn.close()
    if not exists:
        raise HTTPException(status_code=404, detail=f"Vacante #{vid} no encontrada.")
    pdf_path = os.path.join(get_user_outputs_dir(uid), f"cv_vacante_{vid}.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF no generado aún para esta vacante.")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"cv_vacante_{vid}.pdf",
    )


@app.post("/scrape")
async def iniciar_scrape(body: ScrapeRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_optional_user)):
    if _scrape_status["running"]:
        raise HTTPException(status_code=409, detail="Ya hay un scraping en curso. Espera a que termine.")
    user_id = current_user["user_id"]
    terms = body.terminos or generar_terminos_busqueda(user_id)
    filtros = body.filtros.model_dump()
    _scrape_status["running"] = True
    _scrape_status["last"] = None
    _scrape_status["terminos"] = terms
    _scrape_status["filtros"] = filtros
    background_tasks.add_task(_scrape_task, body.cantidad, terms, filtros, user_id, body.min_compat)
    return {
        "ok": True,
        "mensaje": f"Scraping de {body.cantidad} vacantes iniciado con {len(terms)} términos (compat ≥ {body.min_compat}).",
        "terminos": terms,
        "filtros": filtros,
    }


@app.get("/scrape/status")
def scrape_status():
    return JSONResponse(content=_scrape_status, headers={"Cache-Control": "no-store"})


@app.delete("/vacantes/{vid}")
def borrar_vacante(vid: int, current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    conn = _db()
    cur = conn.cursor()
    cur.execute("SELECT enlace, titulo FROM vacantes WHERE id=%s AND user_id=%s", (vid, uid))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"Vacante #{vid} no encontrada.")
    enlace, titulo = row
    _blacklist_add(conn, enlace, titulo, uid)
    cur.execute("DELETE FROM vacantes WHERE id=%s AND user_id=%s", (vid, uid))
    conn.commit()
    cur.close()
    conn.close()
    return {"ok": True, "id": vid}


# ── Perfil endpoints ──────────────────────────────────────────────────────────

@app.post("/perfil/upload")
async def upload_perfil(files: list[UploadFile] = File(...)):
    import io as _io
    # Security: Limit total upload size to prevent memory exhaustion
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB per file
    MAX_TOTAL_SIZE = 15 * 1024 * 1024 # 15MB total
    total_received = 0

    os.makedirs(CONTEXT_DIR, exist_ok=True)
    profile_md = os.path.join(CONTEXT_DIR, "mi_perfil.md")
    sections: list[str] = []
    saved: list[str] = []

    for file in files:
        fname = file.filename or "archivo"
        # Security: Basic filename sanitization
        fname = "".join(c for c in fname if c.isalnum() or c in "._-").strip()
        if not fname: fname = "file_" + uuid.uuid4().hex[:8]

        ext   = os.path.splitext(fname)[1].lower()
        data  = await file.read()
        
        file_size = len(data)
        total_received += file_size
        
        if file_size > MAX_FILE_SIZE or total_received > MAX_TOTAL_SIZE:
             _log.warning("Upload bloqueado: archivo demasiado grande (%s, %d bytes)", fname, file_size)
             raise HTTPException(status_code=413, detail="El archivo o el total de carga excede el límite permitido.")

        dest = os.path.join(CONTEXT_DIR, fname)
        with open(dest, "wb") as out:
            out.write(data)
        saved.append(fname)

        if ext == ".pdf":
            if not _HAS_PYPDF2:
                sections.append(f"# {fname}\n[PyPDF2 no instalado — instala con: pip install PyPDF2]")
                continue
            try:
                reader = _pypdf2.PdfReader(_io.BytesIO(data))
                text = "".join(p.extract_text() or "" for p in reader.pages)
                sections.append(f"# {fname}\n{text.strip()}")
            except Exception as e:
                sections.append(f"# {fname}\n[Error extrayendo PDF: {e}]")
        elif ext in (".md", ".txt"):
            text = data.decode("utf-8", errors="replace")
            sections.append(f"# {fname}\n{text.strip()}")
        else:
            sections.append(f"# {fname}\n[Formato no soportado — sube PDF, .md o .txt]")

    combined = "\n\n---\n\n".join(sections)
    with open(profile_md, "w", encoding="utf-8") as f:
        f.write(combined)

    return {
        "ok":      True,
        "mensaje": f"{len(files)} archivo(s) procesado(s): {', '.join(saved)}",
        "archivos": saved,
        "chars":   len(combined),
        "ruta":    profile_md,
    }


@app.get("/perfil")
def get_perfil():
    profile_md = os.path.join(CONTEXT_DIR, "mi_perfil.md")
    if not os.path.exists(profile_md):
        raise HTTPException(status_code=404, detail="Perfil no encontrado. Sube tu CV en POST /perfil/upload.")
    with open(profile_md, "r", encoding="utf-8") as f:
        content = f.read()
    return {"ok": True, "contenido": content, "ruta": profile_md}


@app.get("/api/search-terms")
def get_search_terms(current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    terms = generar_terminos_busqueda(uid)
    return {"terminos": terms, "user_id": uid}


@app.get("/api/perfil")
def get_perfil_maestro(current_user: dict = Depends(get_current_user)):
    uid        = current_user["user_id"]
    user_path  = get_user_profile_path(uid)
    if os.path.exists(user_path):
        with open(user_path, encoding="utf-8") as f:
            return json.load(f)
    # Legacy fallback only for default_user
    if uid == 'default_user' and os.path.exists(PERFIL_MAESTRO_PATH):
        with open(PERFIL_MAESTRO_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}  # New user — no profile yet, frontend handles empty state


@app.post("/api/perfil")
async def save_perfil_maestro(request: Request, current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    try:
        data = await request.json()
    except Exception:
        _log.error("POST /api/perfil → JSON inválido")
        raise HTTPException(status_code=400, detail="JSON inválido.")
    
    _log.info("POST /api/perfil → Guardando perfil para user_id=%s", uid)
    
    required = {"nombre", "apellidos", "email"}
    missing = required - set(data.keys())
    if missing:
        raise HTTPException(status_code=400, detail=f"Campos requeridos: {sorted(missing)}")
    dest = get_user_profile_path(uid)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # Always sync perfil_maestro.json so bot/scraper/LLM are never stale
    with open(PERFIL_MAESTRO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    clear_compat_cache(uid)
    try:
        regenerate_mi_perfil(uid)
    except Exception as _regen_err:
        _log.warning("POST /api/perfil → regenerate_mi_perfil falló (perfil JSON ya guardado): %s", _regen_err)
    return {"ok": True, "mensaje": "Perfil guardado correctamente."}


# ── Template endpoints ────────────────────────────────────────────────────────

@app.get("/template/activa")
def template_activa():
    custom = os.path.join(TEMPLATES_DIR, 'mi_estilo.tex')
    default = os.path.join(TEMPLATES_DIR, 'default_template.tex')
    if os.path.exists(custom):
        stat = os.stat(custom)
        return {"activa": "mi_estilo.tex", "personalizada": True,
                "size_kb": round(stat.st_size / 1024, 1), "modified": stat.st_mtime}
    stat = os.stat(default) if os.path.exists(default) else None
    return {"activa": "default_template.tex", "personalizada": False,
            "size_kb": round(stat.st_size / 1024, 1) if stat else None,
            "modified": stat.st_mtime if stat else None}


@app.delete("/template/custom")
def delete_custom_template():
    custom = os.path.join(TEMPLATES_DIR, 'mi_estilo.tex')
    if not os.path.exists(custom):
        raise HTTPException(status_code=404, detail="No hay plantilla personalizada activa.")
    os.remove(custom)
    return {"ok": True, "mensaje": "Plantilla personalizada eliminada. Usando plantilla base."}


@app.get("/template/download")
def download_template():
    custom = os.path.join(TEMPLATES_DIR, 'mi_estilo.tex')
    default = os.path.join(TEMPLATES_DIR, 'default_template.tex')
    path = custom if os.path.exists(custom) else default
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Plantilla no encontrada.")
    return FileResponse(path, filename=os.path.basename(path), media_type='text/plain')


# ── Métricas endpoint ─────────────────────────────────────────────────────────

_TECH_KEYWORDS = [
    "Python", "JavaScript", "TypeScript", "React", "Next.js", "Node.js", "Go", "Rust",
    "FastAPI", "Flask", "Django", "Docker", "Kubernetes", "AWS", "Azure", "GCP",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Git", "CI/CD", "REST", "GraphQL",
    "Machine Learning", "AI", "NLP", "PyTorch", "TensorFlow", "Pandas", "NumPy",
    "IoT", "ESP32", "MQTT", "SolidWorks", "MATLAB", "Arduino", "STM32", "PLC",
    "Linux", "Embedded", "RTOS", "Unit Testing", "Microservices", "Terraform",
]


@app.get("/metricas")
def get_metricas(current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    conn = _db()
    cur = conn.cursor()

    # 1. Básicos
    cur.execute("SELECT COUNT(*) FROM vacantes WHERE user_id=%s AND status != 'No_Creado'", (uid,))
    total_aplicadas = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM vacantes WHERE user_id=%s AND status='Entrevista'", (uid,))
    total_entrevistas = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM vacantes WHERE user_id=%s AND status='Listo_Manual'", (uid,))
    total_enviados = cur.fetchone()[0] or 0

    # 2. Correlación Compatibilidad -> Éxito
    cur.execute(
        "SELECT compatibilidad, COUNT(*) FROM vacantes "
        "WHERE user_id=%s AND status='Entrevista' GROUP BY compatibilidad", (uid,)
    )
    success_by_compat = dict(cur.fetchall())

    # 3. Distribución de compatibilidad general
    cur.execute(
        "SELECT compatibilidad, COUNT(*) FROM vacantes WHERE user_id=%s GROUP BY compatibilidad", (uid,)
    )
    compat_dist = dict(cur.fetchall())

    # 4. Top Skills en Entrevistas vs Aplicadas (Fuerza de conversión)
    cur.execute(
        "SELECT requerimientos, status FROM vacantes "
        "WHERE user_id=%s AND status IN ('Entrevista', 'Listo_Manual') AND requerimientos IS NOT NULL", (uid,)
    )
    req_rows = cur.fetchall()
    cur.close()
    conn.close()

    tasa_conversion = round((total_entrevistas / total_aplicadas) * 100, 1) if total_aplicadas > 0 else 0.0

    kw_counts: dict[str, int] = {}
    for text, status in req_rows:
        text_lower = text.lower()
        weight = 3 if status == 'Entrevista' else 1
        for kw in _TECH_KEYWORDS:
            if kw.lower() in text_lower:
                kw_counts[kw] = kw_counts.get(kw, 0) + weight

    top_skills = sorted(kw_counts.items(), key=lambda x: -x[1])[:8]

    return {
        "total_aplicadas": total_aplicadas,
        "total_entrevistas": total_entrevistas,
        "total_enviados": total_enviados,
        "tasa_conversion": tasa_conversion,
        "top_skills_entrevistas": [{"skill": k, "count": v} for k, v in top_skills],
        "compat_distribution": compat_dist,
        "success_rate_by_compatibility": {
            k: round((success_by_compat.get(k, 0) / v) * 100, 1) if v > 0 else 0
            for k, v in compat_dist.items()
        }
    }


# ── Admin endpoints ───────────────────────────────────────────────────────────

@app.get("/admin/users")
def admin_list_users(current_user: dict = Depends(require_admin)):
    conn = _db()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, email, tier, role, created_at, is_verified, verification_code "
        "FROM usuarios ORDER BY created_at"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    cols = ["user_id", "email", "tier", "role", "fecha_creacion", "is_verified", "verification_code"]
    return JSONResponse(content=[_row_dict(cols, r) for r in rows], headers={"Cache-Control": "no-store"})


@app.patch("/admin/users/{target_id}/verify")
def admin_force_verify(target_id: str, current_user: dict = Depends(require_admin)):
    conn = _db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM usuarios WHERE user_id=%s", (target_id,))
    if not cur.fetchone():
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    cur.execute(
        "UPDATE usuarios SET is_verified=TRUE, verification_code=NULL WHERE user_id=%s",
        (target_id,)
    )
    conn.commit()
    cur.close(); conn.close()
    return {"ok": True, "msg": f"Usuario {target_id} verificado."}


@app.patch("/admin/users/{user_id}/tier")
def admin_update_tier(user_id: str, body: TierUpdate, current_user: dict = Depends(require_admin)):
    tiers = {
        "free": {"v": 5, "l": 3},
        "pro": {"v": 20, "l": 12},
        "ultimate": {"v": 50, "l": 35}
    }
    if body.tier not in tiers:
        raise HTTPException(status_code=400, detail="tier debe ser 'free', 'pro' o 'ultimate'")
    
    limits = tiers[body.tier]
    conn = _db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE usuarios SET tier=%s, vacantes_limite=%s, latex_limite=%s WHERE user_id=%s",
        (body.tier, limits["v"], limits["l"], user_id)
    )
    conn.commit()
    changes = cur.rowcount
    cur.close()
    conn.close()
    if not changes:
        raise HTTPException(status_code=404, detail=f"Usuario {user_id} no encontrado.")
    return {"ok": True, "user_id": user_id, "tier": body.tier}


# ── Background tasks ──────────────────────────────────────────────────────────

def _scrape_task(cantidad: int, terminos: list[str] | None = None, filtros: dict | None = None, user_id: str = 'default_user', min_compat: str = 'Media'):
    agent_path = os.path.join(os.path.dirname(__file__), 'browser_agent.py')
    cmd = [sys.executable, agent_path, '--limit', str(cantidad), '--user-id', user_id, '--min-compat', min_compat]
    if terminos:
        cmd += ['--terms'] + terminos
    if filtros:
        cmd += ['--filtros', json.dumps(filtros, ensure_ascii=False)]
    try:
        result = subprocess.run(
            cmd,
            timeout=600,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
        )
        if result.stdout:
            for line in result.stdout.strip().splitlines():
                _log.info("[scraper] %s", line)
        if result.stderr:
            for line in result.stderr.strip().splitlines():
                _log.warning("[scraper-err] %s", line)
        _scrape_status["last"] = f"OK – exit={result.returncode} – {cantidad} vacantes solicitadas"
        if result.returncode != 0:
            _scrape_status["last"] = f"ERROR – exit={result.returncode} – {result.stderr[:200]}"
    except subprocess.TimeoutExpired:
        _scrape_status["last"] = "TIMEOUT – el scraping superó 10 minutos."
    except Exception as e:
        _scrape_status["last"] = f"ERROR – {e}"
    finally:
        _scrape_status["running"] = False


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
