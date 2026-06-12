import asyncio
import json
import logging
import os
import re
import urllib.request
import urllib.error

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from gemini_engine import compilar_pdf, get_user_outputs_dir, _inject_fixed_header, _detect_lang, _build_header

# ── Config ────────────────────────────────────────────────────────────────────

API_BASE   = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
_MCP_EMAIL = os.getenv("MCP_API_EMAIL", "test@jobhunter.com")
_MCP_PASS  = os.getenv("MCP_API_PASSWORD", "jobhunter123")
_TOKEN     = ""          # populated by _login() at startup

# Debug logger — escribe en job_hunter/mcp_debug.log
_LOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'mcp_debug.log')
logging.basicConfig(
    filename=os.path.abspath(_LOG_PATH),
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    encoding='utf-8',
)
_log = logging.getLogger("mcp_server")
_log.info("=== MCP server arrancando (PID %s) ===", os.getpid())

server = Server("job-hunter")

# ── HTTP helpers (evitan sqlite3 bloqueado por sandbox) ──────────────────────

_STOP_API_DOWN = (
    f"🔴 STOP — La API de Job Hunter NO está corriendo en {API_BASE}.\n"
    "PROHIBIDO usar bash/sqlite/archivos como alternativa.\n"
    "Solución: abre PowerShell y ejecuta:\n"
    "  cd C:\\Users\\GIRTEC\\Desktop\\CODEMAGA\\JobHunter\n"
    "  docker compose up -d\n"
    "Espera 5 segundos y vuelve a intentar el mismo paso."
)

def _login() -> None:
    global _TOKEN
    payload = json.dumps({"email": _MCP_EMAIL, "password": _MCP_PASS}).encode()
    req = urllib.request.Request(
        f"{API_BASE}/auth/login", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            _TOKEN = json.loads(r.read()).get("access_token", "")
        _log.info("MCP login OK — token obtenido")
    except Exception as e:
        _log.warning("MCP login falló: %s — llamadas autenticadas fallarán", e)


def _auth_headers(extra: dict | None = None) -> dict:
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if _TOKEN:
        h["Authorization"] = f"Bearer {_TOKEN}"
    if extra:
        h.update(extra)
    return h


def _api_health() -> bool:
    try:
        with urllib.request.urlopen(f"{API_BASE}/scrape/status", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def _http_post(path: str) -> None:
    req = urllib.request.Request(
        f"{API_BASE}{path}", data=b"{}", method="POST",
        headers=_auth_headers(),
    )
    try:
        with urllib.request.urlopen(req, timeout=5):
            pass
    except Exception as e:
        _log.debug("POST %s falló: %s", path, e)


async def _heartbeat_loop():
    while True:
        await asyncio.to_thread(_http_post, "/mcp/heartbeat")
        await asyncio.sleep(30)


def _http_get(path: str) -> dict | list:
    req = urllib.request.Request(f"{API_BASE}{path}", headers=_auth_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode(errors='replace')}")
    except Exception as e:
        raise RuntimeError(str(e))


def _http_patch(path: str, data: dict) -> dict:
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}{path}", data=payload, method="PATCH",
        headers=_auth_headers(),
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            _log.info("PATCH %s -> HTTP %s", path, resp.status)
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode(errors="replace")
        _log.warning("PATCH %s -> HTTP %s | %s", path, e.code, error_body)
        raise RuntimeError(f"HTTP {e.code}: {error_body}")
    except Exception as e:
        raise RuntimeError(str(e))

# ── Tools ─────────────────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_vacancy_by_id",
            description=(
                "[REQUIERE api.py corriendo en 127.0.0.1:8000] "
                "Devuelve título, empresa, enlace y requerimientos de una vacante "
                "por su ID. Úsala como PRIMER paso. "
                "Si falla, ejecuta start_api.ps1 y reintenta — NO uses bash/sqlite."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "vacante_id": {"type": "integer", "description": "ID de la vacante"}
                },
                "required": ["vacante_id"],
            },
        ),
        Tool(
            name="get_pending_vacancies",
            description=(
                "Lista las vacantes en estado No_Creado o Requiere_Correccion. "
                "Úsala para ver qué CVs pendientes necesitan generarse."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="update_compatibility",
            description=(
                "Guarda el nivel de compatibilidad de una vacante con el perfil del candidato. "
                "Llámala después de evaluar el match. Niveles válidos: Alta, Media, Baja, Nula."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "vacante_id": {"type": "integer", "description": "ID de la vacante"},
                    "nivel": {
                        "type": "string",
                        "enum": ["Alta", "Media", "Baja", "Nula"],
                        "description": "Nivel de compatibilidad"
                    },
                },
                "required": ["vacante_id", "nivel"],
            },
        ),
        Tool(
            name="reset_vacancy",
            description=(
                "[REQUIERE api.py corriendo en 127.0.0.1:8000] "
                "Resetea el status de una vacante a No_Creado y elimina sus archivos CV (.tex y .pdf). "
                "Úsala cuando un CV generado NO corresponde a los requerimientos de la vacante, "
                "para limpiar y permitir una regeneración correcta. "
                "También puede usarse para marcar vacantes como Nula compatibilidad (ej. Brasil-only, "
                "puesto de redacción, etc.). "
                "Si la API no responde: DETENTE y levanta docker compose."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "vacante_id": {"type": "integer", "description": "ID de la vacante a resetear"},
                },
                "required": ["vacante_id"],
            },
        ),
        Tool(
            name="save_latex_cv",
            description=(
                "[REQUIERE api.py corriendo en 127.0.0.1:8000] "
                "Guarda el código LaTeX, lo compila con pdflatex y actualiza el status "
                "a Revisado_IA vía PATCH HTTP. "
                "SOLO código LaTeX puro (sin bloques markdown). "
                "REGLAS DE GENERACIÓN ATS: "
                "(1) Single-column — PROHIBIDO multicol/minipage lado a lado; "
                "(2) PROHIBIDO \\usepackage{fontawesome5}; "
                "(3) Keywords EXACTAS de la vacante (mirror literal); "
                "(4) Título profesional = título exacto del puesto; "
                "(5) Macros Jake's Resume: \\resumeSubheading{Puesto}{Periodo}{Empresa}{Ciudad} + \\resumeItem{}; "
                "(6) 1 página junior/mid, máx 2 senior; "
                "(7) Caracteres especiales con \\' para compatibilidad pdflatex. "
                "Si la API no responde: DETENTE y levanta docker compose — NUNCA uses bash/sqlite."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "vacante_id": {"type": "integer", "description": "ID de la vacante"},
                    "tex_content": {
                        "type": "string",
                        "description": "Código LaTeX completo (debe empezar con \\documentclass)"
                    },
                },
                "required": ["vacante_id", "tex_content"],
            },
        ),
        Tool(
            name="save_latex_cl",
            description=(
                "[REQUIERE api.py corriendo en 127.0.0.1:8000] "
                "Guarda el código LaTeX de una Carta de Presentación (Cover Letter), "
                "lo compila con pdflatex. "
                "SOLO código LaTeX puro (sin bloques markdown). "
                "La carta debe estar personalizada para la vacante y la empresa."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "vacante_id": {"type": "integer", "description": "ID de la vacante"},
                    "tex_content": {
                        "type": "string",
                        "description": "Código LaTeX completo (debe empezar con \\documentclass)"
                    },
                },
                "required": ["vacante_id", "tex_content"],
            },
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    _log.info("TOOL CALL: %s  args=%s", name, arguments)
    if name == "get_vacancy_by_id":
        return await _get_vacancy_by_id(int(arguments["vacante_id"]))
    if name == "get_pending_vacancies":
        return await _get_pending_vacancies()
    if name == "update_compatibility":
        return await _update_compatibility(int(arguments["vacante_id"]), str(arguments["nivel"]))
    if name == "reset_vacancy":
        return await _reset_vacancy(int(arguments["vacante_id"]))
    if name == "save_latex_cv":
        return await _save_latex_cv(int(arguments["vacante_id"]), str(arguments["tex_content"]))
    if name == "save_latex_cl":
        return await _save_latex_cl(int(arguments["vacante_id"]), str(arguments["tex_content"]))
    return [TextContent(type="text", text=f"Tool desconocida: {name}")]

# ── Implementaciones ──────────────────────────────────────────────────────────

async def _get_vacancy_by_id(vacante_id: int):
    if not _api_health():
        return [TextContent(type="text", text=_STOP_API_DOWN)]
    try:
        data = _http_get(f"/vacantes/{vacante_id}")
    except RuntimeError as e:
        return [TextContent(type="text", text=f"ERROR: {e}")]
    return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]


async def _get_pending_vacancies():
    try:
        all_v = _http_get("/vacantes?limit=100")
    except RuntimeError as e:
        return [TextContent(type="text", text=f"ERROR: {e}")]

    compat_rank = {"Alta": 3, "Media": 2, "Baja": 1, "Nula": 0}
    pendientes = [v for v in all_v if v.get("status") in ("No_Creado", "Requiere_Correccion")]
    pendientes.sort(key=lambda v: (-compat_rank.get(v.get("compatibilidad", ""), 0), -v["id"]))
    pendientes = pendientes[:20]

    if not pendientes:
        return [TextContent(type="text", text="No hay vacantes pendientes.")]
    return [TextContent(
        type="text",
        text=f"Vacantes pendientes ({len(pendientes)}):\n{json.dumps(pendientes, ensure_ascii=False, indent=2)}"
    )]


async def _update_compatibility(vacante_id: int, nivel: str):
    VALIDOS = {"Alta", "Media", "Baja", "Nula"}
    if nivel not in VALIDOS:
        return [TextContent(type="text", text=f"ERROR: nivel inválido '{nivel}'. Usa: {sorted(VALIDOS)}")]
    try:
        _http_patch(f"/vacantes/{vacante_id}/compatibilidad", {"compatibilidad": nivel})
    except RuntimeError as e:
        return [TextContent(type="text", text=f"ERROR actualizando compatibilidad: {e}")]
    return [TextContent(type="text", text=f"✓ Compatibilidad vacante #{vacante_id} → {nivel}")]


async def _reset_vacancy(vacante_id: int):
    """Resetea status a No_Creado y borra los archivos CV del disco."""
    if not _api_health():
        return [TextContent(type="text", text=_STOP_API_DOWN)]

    # Verificar que la vacante existe
    try:
        vacante = _http_get(f"/vacantes/{vacante_id}")
        titulo = vacante.get("titulo", f"#{vacante_id}")
    except RuntimeError as e:
        return [TextContent(type="text", text=f"ERROR verificando vacante: {e}")]

    # Resetear status → No_Creado
    try:
        _http_patch(f"/vacantes/{vacante_id}/status", {"status": "No_Creado"})
    except RuntimeError as e:
        return [TextContent(type="text", text=f"ERROR reseteando status: {e}")]

    # Borrar archivos CV del disco
    out_dir = get_user_outputs_dir("default_user")
    deleted = []
    for ext in ("tex", "pdf"):
        path = os.path.join(out_dir, f"cv_vacante_{vacante_id}.{ext}")
        if os.path.exists(path):
            try:
                os.remove(path)
                deleted.append(ext)
            except OSError:
                pass  # Si no se puede borrar, no es crítico

    deleted_str = ", ".join(f".{e}" for e in deleted) if deleted else "ninguno (ya no existían)"
    return [TextContent(
        type="text",
        text=(
            f"✓ Vacante #{vacante_id} — {titulo}\n"
            f"  Status   → No_Creado\n"
            f"  Archivos eliminados: {deleted_str}"
        )
    )]


async def _save_latex_cv(vacante_id: int, tex_content: str):
    # Health-check: abortar si la API no responde
    if not _api_health():
        return [TextContent(type="text", text=_STOP_API_DOWN)]

    # Verificar vacante vía API (sin tocar sqlite)
    try:
        vacante = _http_get(f"/vacantes/{vacante_id}")
        titulo = vacante.get("titulo", f"#{vacante_id}")
    except RuntimeError as e:
        return [TextContent(type="text", text=f"ERROR verificando vacante: {e}")]

    # Señalizar En_Proceso antes de compilar
    try:
        _http_patch(f"/vacantes/{vacante_id}/status", {"status": "En_Proceso"})
    except RuntimeError as e:
        _log.warning("No se pudo marcar En_Proceso: %s", e)

    # ── Helper interno para no repetir el try/except de PATCH ──────────────────
    def _set_status(new_status: str):
        try:
            _http_patch(f"/vacantes/{vacante_id}/status", {"status": new_status})
            _log.info("Status vacante #%s → %s", vacante_id, new_status)
        except RuntimeError as exc:
            _log.warning("No se pudo actualizar status a %s: %s", new_status, exc)

    # Candado de encabezado: detectar idioma e inyectar antes de escribir el .tex
    _lang = _detect_lang(titulo + " " + tex_content)
    _log.info("[MCP] Idioma detectado para vacante #%s: %s", vacante_id, _lang)
    tex_content = _inject_fixed_header(tex_content, _build_header(_lang))

    # Escribir .tex en el directorio del usuario correcto
    out_dir = get_user_outputs_dir("default_user")
    os.makedirs(out_dir, exist_ok=True)
    tex_path = os.path.join(out_dir, f"cv_vacante_{vacante_id}.tex")
    try:
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex_content)
    except OSError as e:
        _set_status("Requiere_Correccion")
        return [TextContent(type="text", text=f"ERROR escribiendo .tex: {e}\n  Status → Requiere_Correccion")]

    # Compilar PDF
    pdf_path = None
    compile_error = None
    try:
        pdf_path = compilar_pdf(tex_path)
    except Exception as e:
        compile_error = str(e)

    if pdf_path and os.path.exists(pdf_path):
        _set_status("Revisado_IA")
        return [TextContent(
            type="text",
            text=(
                f"✓ CV guardado y compilado correctamente.\n"
                f"  Vacante : #{vacante_id} — {titulo}\n"
                f"  .tex    : {tex_path}\n"
                f"  PDF     : {pdf_path}\n"
                f"  Status  → Revisado_IA"
            )
        )]
    else:
        _set_status("Requiere_Correccion")
        error_detail = compile_error or "pdflatex no generó el archivo."
        return [TextContent(
            type="text",
            text=(
                f"⚠ .tex guardado pero PDF no compiló.\n"
                f"  Vacante : #{vacante_id} — {titulo}\n"
                f"  .tex    : {tex_path}\n"
                f"  Error   : {error_detail}\n"
                f"  Status  → Requiere_Correccion\n"
                f"  Revisa la sintaxis LaTeX e intenta de nuevo."
            )
        )]


async def _save_latex_cl(vacante_id: int, tex_content: str):
    """Guarda y compila la Carta de Presentación."""
    if not _api_health():
        return [TextContent(type="text", text=_STOP_API_DOWN)]

    try:
        vacante = _http_get(f"/vacantes/{vacante_id}")
        titulo = vacante.get("titulo", f"#{vacante_id}")
    except RuntimeError as e:
        return [TextContent(type="text", text=f"ERROR verificando vacante: {e}")]

    # Inyección de encabezado
    _lang = _detect_lang(titulo + " " + tex_content)
    tex_content = _inject_fixed_header(tex_content, _build_header(_lang))

    out_dir = get_user_outputs_dir("default_user")
    tex_path = os.path.join(out_dir, f"cl_vacante_{vacante_id}.tex")
    try:
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex_content)
    except OSError as e:
        return [TextContent(type="text", text=f"ERROR escribiendo .tex: {e}")]

    # Compilar PDF
    pdf_path = None
    try:
        pdf_path = compilar_pdf(tex_path)
    except Exception as e:
        error_detail = str(e)
        return [TextContent(type="text", text=f"⚠ .tex guardado pero PDF no compiló: {error_detail}")]

    if pdf_path and os.path.exists(pdf_path):
        return [TextContent(
            type="text",
            text=(
                f"✓ Carta de Presentación guardada y compilada.\n"
                f"  Vacante : #{vacante_id} — {titulo}\n"
                f"  .tex    : {tex_path}\n"
                f"  PDF     : {pdf_path}"
            )
        )]
    return [TextContent(type="text", text="ERROR: pdflatex no generó el archivo.")]


# ── Entrypoint ────────────────────────────────────────────────────────────────

async def main():
    _login()
    _log.info("stdio_server iniciando — esperando mensajes JSON-RPC de Claude Desktop")
    heartbeat_task = asyncio.create_task(_heartbeat_loop())
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        heartbeat_task.cancel()
    _log.info("stdio_server cerrado")

if __name__ == "__main__":
    asyncio.run(main())
