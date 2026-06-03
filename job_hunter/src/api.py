import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import sqlite3
import os
import shutil
import subprocess
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from gemini_engine import TEMPLATES_DIR, DB_PATH, OUTPUTS_DIR, CONTEXT_DIR, compilar_pdf, evaluar_compatibilidad_rapida, generar_terminos_busqueda

try:
    import PyPDF2 as _pypdf2
    _HAS_PYPDF2 = True
except ImportError:
    _HAS_PYPDF2 = False

PERFIL_MAESTRO_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'data', 'perfil_maestro.json')
)

# ── Estado en memoria ─────────────────────────────────────────────────────────
_scrape_status: dict = {"running": False, "last": None}

# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    yield

app = FastAPI(title="Job Hunter API", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Perfil Maestro helpers ────────────────────────────────────────────────────

def _regenerate_mi_perfil(data: dict) -> None:
    """Escribe mi_perfil.md desde perfil_maestro.json para que gemini_engine lo lea."""
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


# ── Helpers DB ────────────────────────────────────────────────────────────────

def _db():
    return sqlite3.connect(DB_PATH)

def _set_status(vid: int, status: str):
    conn = _db()
    conn.execute("UPDATE vacantes SET status=? WHERE id=?", (status, vid))
    conn.commit()
    conn.close()


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


class ScrapeRequest(BaseModel):
    cantidad: int = Field(ge=1, le=200, description="Vacantes a extraer (máximo global)")
    terminos: list[str] | None = Field(default=None, description="Términos de búsqueda (None = usar perfil_maestro.json)")

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/vacantes")
def listar_vacantes(limit: int = 50, status: str | None = None):
    """Devuelve lista de vacantes. Filtra por status si se provee."""
    conn = _db()
    if status:
        rows = conn.execute(
            "SELECT id, titulo, empresa, enlace, requerimientos, compatibilidad, status, fecha_registro "
            "FROM vacantes WHERE status=? ORDER BY id DESC LIMIT ?",
            (status, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, titulo, empresa, enlace, requerimientos, compatibilidad, status, fecha_registro "
            "FROM vacantes ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    cols = ["id", "titulo", "empresa", "enlace", "requerimientos", "compatibilidad", "status", "fecha_registro"]
    return [dict(zip(cols, r)) for r in rows]


@app.get("/vacantes/{vid}")
def detalle_vacante(vid: int):
    """Devuelve todos los campos de una vacante."""
    conn = _db()
    row = conn.execute(
        "SELECT id, titulo, empresa, enlace, requerimientos, compatibilidad, status, fecha_registro "
        "FROM vacantes WHERE id=?", (vid,)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail=f"Vacante #{vid} no encontrada.")
    cols = ["id", "titulo", "empresa", "enlace", "requerimientos", "compatibilidad", "status", "fecha_registro"]
    return dict(zip(cols, row))


@app.patch("/vacantes/{vid}/status")
def cambiar_status(vid: int, body: dict):
    """Actualiza el status de una vacante. Body: {"status": "Listo_Manual"}"""
    VALIDOS = {"No_Creado", "En_Proceso", "Revisado_IA", "Listo_Manual", "Requiere_Correccion"}
    nuevo = body.get("status", "")
    if nuevo not in VALIDOS:
        raise HTTPException(status_code=400, detail=f"Status inválido. Usa: {VALIDOS}")
    conn = _db()
    conn.execute("UPDATE vacantes SET status=? WHERE id=?", (nuevo, vid))
    conn.commit()
    changes = conn.execute("SELECT changes()").fetchone()[0]
    conn.close()
    if not changes:
        raise HTTPException(status_code=404, detail=f"Vacante #{vid} no encontrada.")
    return {"ok": True, "id": vid, "status": nuevo}


@app.patch("/vacantes/{vid}/compatibilidad")
def cambiar_compatibilidad(vid: int, body: dict):
    """Actualiza el nivel de compatibilidad de una vacante."""
    VALIDOS = {"Alta", "Media", "Baja", "Nula"}
    nuevo = body.get("compatibilidad", "")
    if nuevo not in VALIDOS:
        raise HTTPException(status_code=400, detail=f"Compatibilidad inválida. Usa: {VALIDOS}")
    conn = _db()
    conn.execute("UPDATE vacantes SET compatibilidad=? WHERE id=?", (nuevo, vid))
    conn.commit()
    changes = conn.execute("SELECT changes()").fetchone()[0]
    conn.close()
    if not changes:
        raise HTTPException(status_code=404, detail=f"Vacante #{vid} no encontrada.")
    return {"ok": True, "id": vid, "compatibilidad": nuevo}


@app.get("/latex/{vid}", response_class=PlainTextResponse)
def get_latex(vid: int):
    """Devuelve el contenido del .tex generado para una vacante."""
    tex_path = os.path.abspath(os.path.join(OUTPUTS_DIR, f"cv_vacante_{vid}.tex"))
    if not os.path.exists(tex_path):
        raise HTTPException(status_code=404, detail=f"LaTeX no encontrado para vacante #{vid}.")
    with open(tex_path, "r", encoding="utf-8") as f:
        return f.read()


@app.post("/latex/{vid}")
async def save_latex(vid: int, request: Request):
    """Recibe texto LaTeX crudo, sobrescribe el .tex y recompila el PDF."""
    tex_content = (await request.body()).decode("utf-8")
    if not tex_content.strip():
        raise HTTPException(status_code=400, detail="El cuerpo LaTeX está vacío.")
    tex_path = os.path.abspath(os.path.join(OUTPUTS_DIR, f"cv_vacante_{vid}.tex"))
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(tex_content)
    pdf_path = None
    error: str | None = None
    try:
        pdf_path = compilar_pdf(tex_path)
    except Exception as e:
        error = str(e)
    if pdf_path and os.path.exists(pdf_path):
        _set_status(vid, "Revisado_IA")
        return {"ok": True, "pdf": True, "tex_path": tex_path, "pdf_path": pdf_path}
    return {"ok": True, "pdf": False, "error": error or "pdflatex no generó el archivo."}


@app.post("/upload_template")
async def upload_template(file: UploadFile = File(...)):
    """Recibe un .tex y lo guarda como latex_templates/mi_estilo.tex."""
    if not file.filename.lower().endswith('.tex'):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .tex")
    dest = os.path.join(TEMPLATES_DIR, 'mi_estilo.tex')
    with open(dest, 'wb') as out:
        shutil.copyfileobj(file.file, out)
    return {"ok": True, "mensaje": "Plantilla visual actualizada con éxito.", "ruta": dest}


# POST /generar_cv/{vid} eliminado — la generación de CVs es ahora Human-in-the-loop
# vía Claude Desktop + MCP. Ver docs/PIPELINE_IA.md.


@app.post("/vacantes")
def crear_vacante(body: VacanteCreate):
    """Crea una vacante manual en SQLite con status No_Creado y evalúa compatibilidad."""
    reqs = body.requerimientos.strip()[:5000]
    compat = body.compatibilidad if body.compatibilidad in {"Alta", "Media", "Baja", "Nula"} else "Nula"
    if compat == "Nula" and reqs:
        compat = evaluar_compatibilidad_rapida(reqs)
    conn = _db()
    conn.execute(
        "INSERT OR IGNORE INTO vacantes (titulo, empresa, enlace, requerimientos, compatibilidad, status) "
        "VALUES (?,?,?,?,?,'No_Creado')",
        (
            body.titulo.strip()[:200],
            body.empresa.strip()[:100] or "Desconocida",
            body.enlace.strip(),
            reqs,
            compat,
        )
    )
    conn.commit()
    changes = conn.execute("SELECT changes()").fetchone()[0]
    row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    if not changes:
        raise HTTPException(status_code=409, detail="Vacante duplicada o no insertada.")
    return {"ok": True, "id": row_id, "compatibilidad": compat}


@app.post("/vacantes/bulk")
def crear_vacantes_bulk(items: list[VacanteBulkItem]):
    """Inserta vacantes en lote desde un JSON parseado."""
    if not items:
        raise HTTPException(status_code=400, detail="El arreglo JSON esta vacio.")

    conn = _db()
    insertados = 0
    duplicados = 0
    ids: list[int] = []
    try:
        for item in items:
            reqs_b = item.requerimientos.strip()[:5000]
            compat_b = evaluar_compatibilidad_rapida(reqs_b) if reqs_b else "Nula"
            conn.execute(
                "INSERT OR IGNORE INTO vacantes (titulo, empresa, enlace, requerimientos, compatibilidad, status) "
                "VALUES (?,?,?,?,?,'No_Creado')",
                (
                    item.titulo.strip()[:200],
                    item.empresa.strip()[:100] or "Desconocida",
                    item.enlace.strip(),
                    reqs_b,
                    compat_b,
                )
            )
            conn.commit()
            changes = conn.execute("SELECT changes()").fetchone()[0]
            row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            if changes:
                insertados += 1
                ids.append(row_id)
            else:
                duplicados += 1
    finally:
        conn.close()

    return {
        "ok": True,
        "insertadas": insertados,
        "duplicadas": duplicados,
        "ids": ids,
        "status": "No_Creado",
    }


@app.get("/pdf/{vid}")
def descargar_pdf(vid: int, download: bool = False):
    """Sirve el PDF inline para el visor del navegador. ?download=true fuerza descarga."""
    pdf_path = os.path.abspath(os.path.join(OUTPUTS_DIR, f"cv_vacante_{vid}.pdf"))
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


@app.post("/scrape")
async def iniciar_scrape(body: ScrapeRequest, background_tasks: BackgroundTasks):
    """Lanza el browser_agent en background con un límite de vacantes."""
    if _scrape_status["running"]:
        raise HTTPException(status_code=409, detail="Ya hay un scraping en curso. Espera a que termine.")
    terms = body.terminos or generar_terminos_busqueda()
    _scrape_status["running"] = True
    _scrape_status["last"] = None
    _scrape_status["terminos"] = terms
    background_tasks.add_task(_scrape_task, body.cantidad, terms)
    return {"ok": True, "mensaje": f"Scraping de {body.cantidad} vacantes iniciado con {len(terms)} términos.", "terminos": terms}


@app.get("/scrape/status")
def scrape_status():
    """Informa si hay un scraping activo y el resultado del último."""
    return _scrape_status


@app.delete("/vacantes/{vid}")
def borrar_vacante(vid: int):
    """Elimina una vacante por ID."""
    conn = _db()
    conn.execute("DELETE FROM vacantes WHERE id=?", (vid,))
    conn.commit()
    changes = conn.execute("SELECT changes()").fetchone()[0]
    conn.close()
    if not changes:
        raise HTTPException(status_code=404, detail=f"Vacante #{vid} no encontrada.")
    return {"ok": True, "id": vid}


@app.post("/perfil/upload")
async def upload_perfil(files: list[UploadFile] = File(...)):
    """Recibe uno o varios PDF/.md/.txt; combina todo el texto en mi_perfil.md."""
    import io as _io
    os.makedirs(CONTEXT_DIR, exist_ok=True)
    profile_md = os.path.join(CONTEXT_DIR, "mi_perfil.md")
    sections: list[str] = []
    saved: list[str] = []

    for file in files:
        fname = file.filename or "archivo"
        ext   = os.path.splitext(fname)[1].lower()
        data  = await file.read()          # lee bytes UNA sola vez

        # guarda copia física
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
    """Devuelve el contenido de mi_perfil.md."""
    profile_md = os.path.join(CONTEXT_DIR, "mi_perfil.md")
    if not os.path.exists(profile_md):
        raise HTTPException(status_code=404, detail="Perfil no encontrado. Sube tu CV en POST /perfil/upload.")
    with open(profile_md, "r", encoding="utf-8") as f:
        content = f.read()
    return {"ok": True, "contenido": content, "ruta": profile_md}


@app.get("/api/search-terms")
def get_search_terms():
    """Retorna los términos de búsqueda derivados de perfil_maestro.json."""
    terms = generar_terminos_busqueda()
    return {"terminos": terms, "fuente": "perfil_maestro.json" if os.path.exists(PERFIL_MAESTRO_PATH) else "fallback"}


@app.get("/api/perfil")
def get_perfil_maestro():
    """Retorna perfil_maestro.json como fuente de verdad."""
    if not os.path.exists(PERFIL_MAESTRO_PATH):
        raise HTTPException(status_code=404, detail="perfil_maestro.json no encontrado.")
    with open(PERFIL_MAESTRO_PATH, encoding="utf-8") as f:
        return json.load(f)


@app.post("/api/perfil")
async def save_perfil_maestro(request: Request):
    """Valida y sobrescribe perfil_maestro.json; regenera mi_perfil.md."""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido.")
    required = {"nombre", "apellidos", "email"}
    missing = required - set(data.keys())
    if missing:
        raise HTTPException(status_code=400, detail=f"Campos requeridos: {sorted(missing)}")
    os.makedirs(os.path.dirname(PERFIL_MAESTRO_PATH), exist_ok=True)
    with open(PERFIL_MAESTRO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    _regenerate_mi_perfil(data)
    return {"ok": True, "mensaje": "Perfil maestro guardado y mi_perfil.md actualizado."}


@app.get("/template/activa")
def template_activa():
    """Informa qué plantilla está activa."""
    custom = os.path.join(TEMPLATES_DIR, 'mi_estilo.tex')
    if os.path.exists(custom):
        return {"activa": "mi_estilo.tex", "personalizada": True}
    return {"activa": "default_template.tex", "personalizada": False}


# ── Tareas background ─────────────────────────────────────────────────────────

def _scrape_task(cantidad: int, terminos: list[str] | None = None):
    """Ejecuta browser_agent.py con límite y términos derivados del perfil."""
    agent_path = os.path.join(os.path.dirname(__file__), 'browser_agent.py')
    cmd = [sys.executable, agent_path, '--limit', str(cantidad)]
    if terminos:
        cmd += ['--terms'] + terminos
    try:
        result = subprocess.run(
            cmd,
            timeout=600,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
        )
        _scrape_status["last"] = (
            f"OK – exit={result.returncode} – {cantidad} vacantes solicitadas"
        )
    except subprocess.TimeoutExpired:
        _scrape_status["last"] = "TIMEOUT – el scraping superó 10 minutos."
    except Exception as e:
        _scrape_status["last"] = f"ERROR – {e}"
    finally:
        _scrape_status["running"] = False


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
