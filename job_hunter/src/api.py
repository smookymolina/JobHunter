import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import logging
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

from auth import get_current_user, get_optional_user, hash_password, verify_password, create_token
from gemini_engine import (
    TEMPLATES_DIR, DB_PATH, OUTPUTS_DIR, CONTEXT_DIR,
    get_user_outputs_dir, get_user_profile_path,
    compilar_pdf, evaluar_compatibilidad_rapida, generar_terminos_busqueda,
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
        _cur.execute("""
            CREATE TABLE IF NOT EXISTS vacantes (
                id                SERIAL PRIMARY KEY,
                user_id           VARCHAR(50) NOT NULL DEFAULT 'default_user',
                titulo            TEXT NOT NULL,
                empresa           TEXT,
                enlace            TEXT UNIQUE,
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
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'vacantes'
        """)
        existing_cols = {r[0] for r in _cur.fetchall()}
        if 'fecha_postulacion' not in existing_cols:
            _cur.execute("ALTER TABLE vacantes ADD COLUMN fecha_postulacion TIMESTAMP")
        if 'favorito' not in existing_cols:
            _cur.execute("ALTER TABLE vacantes ADD COLUMN favorito INTEGER DEFAULT 0")
        if 'user_id' not in existing_cols:
            _cur.execute("ALTER TABLE vacantes ADD COLUMN user_id VARCHAR(50) NOT NULL DEFAULT 'default_user'")
        # usuarios table
        _cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id              SERIAL PRIMARY KEY,
                user_id         VARCHAR(50) UNIQUE NOT NULL,
                email           VARCHAR(255) UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                created_at      TIMESTAMP DEFAULT NOW()
            )
        """)
        # Seed default_user — keeps link to the 33 migrated vacantes
        _cur.execute("SELECT id FROM usuarios WHERE user_id='default_user'")
        if not _cur.fetchone():
            _cur.execute(
                "INSERT INTO usuarios (user_id, email, hashed_password) VALUES ('default_user', %s, %s)",
                ('test@jobhunter.com', hash_password('jobhunter123'))
            )
        _mc.commit()
        _cur.close()
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
async def register(request: Request):
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
    cur.execute("SELECT id FROM usuarios WHERE email=%s", (email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")
    user_id = uuid.uuid4().hex
    cur.execute(
        "INSERT INTO usuarios (user_id, email, hashed_password) VALUES (%s, %s, %s)",
        (user_id, email, hash_password(password))
    )
    conn.commit()
    cur.close()
    conn.close()
    os.makedirs(_DATA_DIR, exist_ok=True)
    profile_path = get_user_profile_path(user_id)
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump({"nombre": "", "titulo": "", "skills": []}, f)
    return JSONResponse(status_code=201, content={"ok": True, "user_id": user_id})


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


# ── Models ────────────────────────────────────────────────────────────────────

class VacanteCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    empresa: str = Field(default="Desconocida", max_length=100)
    enlace: str = Field(default="", max_length=500)
    requerimientos: str = Field(default="", max_length=5000)
    compatibilidad: str = Field(default="Nula")


class VacanteBulkItem(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    empresa: str = Field(default="Desconocida", max_length=100)
    enlace: str = Field(default="", max_length=500)
    requerimientos: str = Field(default="", max_length=5000)


class FiltrosBusqueda(BaseModel):
    ubicacion: str  = Field(default="", description="Ciudad o estado — vacío = cualquiera")
    modalidad: str  = Field(default="any", description="any | remoto | hibrido | presencial")
    pais:      str  = Field(default="Mexico", description="Mexico | España | Argentina | Colombia | Internacional")


class ScrapeRequest(BaseModel):
    cantidad: int = Field(ge=1, le=200, description="Vacantes a extraer (máximo global)")
    terminos: list[str] | None = Field(default=None, description="Términos de búsqueda (None = usar perfil_maestro.json)")
    filtros:  FiltrosBusqueda  = Field(default_factory=FiltrosBusqueda)


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
    VALIDOS = {"No_Creado", "En_Proceso", "Revisado_IA", "Listo_Manual", "Requiere_Correccion"}
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


@app.post("/debug/sync-health")
def debug_sync_health_apply():
    snapshot = deep_health_check(dry_run=False)
    watcher = getattr(app.state, "health_watcher", None)
    if watcher:
        watcher._last_snapshot = snapshot
    snapshot["watcher"] = (
        watcher.snapshot() if watcher
        else {"running": False, "interval_seconds": None, "last_error": None, "last_snapshot": snapshot}
    )
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

    auditoria = await loop.run_in_executor(None, evaluar_cv, vid, tex_path)
    tiene_pdf = bool(pdf_path and os.path.exists(pdf_path))

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
def crear_vacante(body: VacanteCreate, current_user: dict = Depends(get_optional_user)):
    uid = current_user["user_id"]
    enlace = body.enlace.strip()
    conn = _db()
    if _is_blacklisted(conn, enlace, uid):
        conn.close()
        return JSONResponse(status_code=409, content={"ok": False, "detail": "Vacante eliminada previamente", "blacklisted": True})
    cur = conn.cursor()
    cur.execute("SELECT id FROM vacantes WHERE enlace=%s AND user_id=%s", (enlace, uid))
    existing = cur.fetchone()
    if existing:
        cur.close()
        conn.close()
        return JSONResponse(status_code=409, content={"ok": False, "detail": "Vacante duplicada", "id": existing[0]})

    reqs   = body.requerimientos.strip()[:5000]
    compat = body.compatibilidad if body.compatibilidad in {"Alta", "Media", "Baja"} else None
    if compat is None and reqs:
        compat = evaluar_compatibilidad_rapida(reqs)
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
def crear_vacantes_bulk(items: list[VacanteBulkItem], current_user: dict = Depends(get_optional_user)):
    if not items:
        raise HTTPException(status_code=400, detail="El arreglo JSON esta vacio.")

    uid = current_user["user_id"]
    conn = _db()
    cur = conn.cursor()
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
            compat_b = evaluar_compatibilidad_rapida(reqs_b) if reqs_b else "Nula"
            cur.execute(
                "INSERT INTO vacantes (user_id, titulo, empresa, enlace, requerimientos, compatibilidad, status) "
                "VALUES (%s,%s,%s,%s,%s,%s,'No_Creado') ON CONFLICT (enlace) DO NOTHING RETURNING id",
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
async def iniciar_scrape(body: ScrapeRequest, background_tasks: BackgroundTasks):
    if _scrape_status["running"]:
        raise HTTPException(status_code=409, detail="Ya hay un scraping en curso. Espera a que termine.")
    terms = body.terminos or generar_terminos_busqueda()
    filtros = body.filtros.model_dump()
    _scrape_status["running"] = True
    _scrape_status["last"] = None
    _scrape_status["terminos"] = terms
    _scrape_status["filtros"] = filtros
    background_tasks.add_task(_scrape_task, body.cantidad, terms, filtros)
    return {
        "ok": True,
        "mensaje": f"Scraping de {body.cantidad} vacantes iniciado con {len(terms)} términos.",
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
    os.makedirs(CONTEXT_DIR, exist_ok=True)
    profile_md = os.path.join(CONTEXT_DIR, "mi_perfil.md")
    sections: list[str] = []
    saved: list[str] = []

    for file in files:
        fname = file.filename or "archivo"
        ext   = os.path.splitext(fname)[1].lower()
        data  = await file.read()

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
def get_search_terms():
    terms = generar_terminos_busqueda()
    return {"terminos": terms, "fuente": "perfil_maestro.json" if os.path.exists(PERFIL_MAESTRO_PATH) else "fallback"}


@app.get("/api/perfil")
def get_perfil_maestro(current_user: dict = Depends(get_current_user)):
    uid        = current_user["user_id"]
    user_path  = get_user_profile_path(uid)
    # Fallback: legacy perfil_maestro.json for default_user
    path = user_path if os.path.exists(user_path) else (PERFIL_MAESTRO_PATH if uid == 'default_user' else None)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Perfil no encontrado.")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.post("/api/perfil")
async def save_perfil_maestro(request: Request, current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido.")
    required = {"nombre", "apellidos", "email"}
    missing = required - set(data.keys())
    if missing:
        raise HTTPException(status_code=400, detail=f"Campos requeridos: {sorted(missing)}")
    os.makedirs(_DATA_DIR, exist_ok=True)
    dest = get_user_profile_path(uid)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # Also write legacy path for default_user (watcher/scraper compatibility)
    if uid == 'default_user':
        with open(PERFIL_MAESTRO_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    _regenerate_mi_perfil(data)
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


# ── Background tasks ──────────────────────────────────────────────────────────

def _scrape_task(cantidad: int, terminos: list[str] | None = None, filtros: dict | None = None):
    agent_path = os.path.join(os.path.dirname(__file__), 'browser_agent.py')
    cmd = [sys.executable, agent_path, '--limit', str(cantidad)]
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
