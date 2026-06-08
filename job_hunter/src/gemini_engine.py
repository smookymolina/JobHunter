import os
import re
import subprocess
import pg8000.dbapi as _pg8000
from urllib.parse import urlparse as _urlparse

import logging as _logging
from logging.handlers import RotatingFileHandler as _RotatingFileHandler

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from openai import OpenAI

_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mcp_debug.log')
_log = _logging.getLogger("gemini_engine")
if not _log.handlers:
    _fh = _RotatingFileHandler(os.path.abspath(_LOG_PATH), maxBytes=5_000_000, backupCount=3, encoding='utf-8')
    _fh.setFormatter(_logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    _log.addHandler(_fh)
    _log.setLevel(_logging.DEBUG)

# ── Config ────────────────────────────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.3-70b-versatile"

BASE_DIR      = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
DB_PATH       = os.path.join(BASE_DIR, 'db', 'vacantes.db')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'latex_templates')
OUTPUTS_DIR   = os.path.join(BASE_DIR, 'outputs')           # root outputs dir (kept for compat)

_PROFILE_CANDIDATE = os.getenv("PROFILE_BASE_DIR", "")
CONTEXT_DIR = (_PROFILE_CANDIDATE if _PROFILE_CANDIDATE and os.path.isdir(_PROFILE_CANDIDATE)
               else os.path.join(BASE_DIR, 'context'))

TEMPLATE_CUSTOM  = os.path.join(TEMPLATES_DIR, 'mi_estilo.tex')
TEMPLATE_DEFAULT = os.path.join(TEMPLATES_DIR, 'default_template.tex')

DEFAULT_TEMPLATE_CONTENT = """% ============================================================
%  JOB HUNTER - Plantilla Base de CV
% ============================================================
\\documentclass[11pt, a4paper]{article}

\\usepackage[T1]{fontenc}
\\usepackage[utf8]{inputenc}
\\usepackage[spanish]{babel}
\\usepackage[margin=2cm, top=1.8cm, bottom=1.8cm]{geometry}
\\usepackage{enumitem}
\\usepackage{titlesec}
\\usepackage{hyperref}
\\usepackage{xcolor}
\\usepackage{parskip}
\\usepackage{fontawesome5}

\\definecolor{accentcolor}{RGB}{30, 80, 160}

\\titleformat{\\section}
  {\\large\\bfseries\\color{accentcolor}}
  {}{0em}{}[\\titlerule]
\\titlespacing{\\section}{0pt}{10pt}{4pt}

\\pagestyle{empty}

\\begin{document}

{\\LARGE\\bfseries {{NOMBRE_COMPLETO}}}\\\\[2pt]
{\\large {{TITULO_PROFESIONAL_ADAPTADO}}}\\\\[4pt]
\\small
\\faEnvelope\\ {{EMAIL}} \\quad
\\faPhone\\ {{TELEFONO}} \\quad
\\faLinkedin\\ {{LINKEDIN}} \\quad
\\faGithub\\ {{GITHUB}} \\quad
\\faMapMarker*\\ {{UBICACION}}

\\vspace{6pt}\\hrule\\vspace{6pt}

\\section{Perfil Profesional}
{{RESUMEN_EJECUTIVO}}

\\section{Habilidades Tecnicas}
\\begin{itemize}[leftmargin=*, itemsep=1pt]
    \\item \\textbf{{{CATEGORIA_SKILL_1}}:} {{LISTA_SKILLS_1}}
    \\item \\textbf{{{CATEGORIA_SKILL_2}}:} {{LISTA_SKILLS_2}}
    \\item \\textbf{{{CATEGORIA_SKILL_3}}:} {{LISTA_SKILLS_3}}
    \\item \\textbf{Idiomas:} {{IDIOMAS}}
\\end{itemize}

\\section{Experiencia Profesional}
\\textbf{{{PUESTO_1}}} \\hfill \\textit{{{FECHA_INICIO_1}} -- {{FECHA_FIN_1}}}\\\\
\\textit{{{EMPRESA_1}}} \\hfill {{UBICACION_1}}
\\begin{itemize}[leftmargin=*, itemsep=1pt]
    \\item {{LOGRO_1_1}}
    \\item {{LOGRO_1_2}}
    \\item {{LOGRO_1_3}}
\\end{itemize}

\\section{Proyectos Destacados}
\\begin{itemize}[leftmargin=*, itemsep=2pt]
    \\item \\textbf{{{PROYECTO_1}}:} {{DESCRIPCION_PROYECTO_1}}
    \\item \\textbf{{{PROYECTO_2}}:} {{DESCRIPCION_PROYECTO_2}}
\\end{itemize}

\\section{Educacion}
\\textbf{{{TITULO_ACADEMICO}}} \\hfill \\textit{{{ANIO_EGRESO}}}\\\\
{{INSTITUCION}} \\hfill {{CIUDAD_INSTITUCION}}

\\end{document}
"""


def _ensure_runtime_paths():
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    if not os.path.exists(TEMPLATE_DEFAULT):
        with open(TEMPLATE_DEFAULT, 'w', encoding='utf-8') as f:
            f.write(DEFAULT_TEMPLATE_CONTENT)


_ensure_runtime_paths()


# ── Multi-tenant path helpers ─────────────────────────────────────────────────

def get_user_outputs_dir(user_id: str) -> str:
    """Returns outputs/{user_id}/ and creates it if necessary."""
    path = os.path.join(OUTPUTS_DIR, user_id)
    os.makedirs(path, exist_ok=True)
    return path


def get_user_profile_path(user_id: str) -> str:
    """Returns data/{user_id}_perfil.json (may not exist yet)."""
    return os.path.join(BASE_DIR, 'data', f'{user_id}_perfil.json')


# ── Internal helpers ──────────────────────────────────────────────────────────

def _read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def _db():
    _u = _urlparse(os.getenv('DATABASE_URL'))
    return _pg8000.connect(host=_u.hostname, port=_u.port or 5432,
                           user=_u.username, password=_u.password,
                           database=_u.path.lstrip('/'))


def _get_vacante(vid, user_id='default_user'):
    conn = _db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, titulo, empresa, enlace, requerimientos FROM vacantes WHERE id=%s AND user_id=%s",
        (vid, user_id)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def _set_status(vid, status, user_id='default_user'):
    conn = _db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE vacantes SET status=%s WHERE id=%s AND user_id=%s",
        (status, vid, user_id)
    )
    conn.commit()
    cur.close()
    conn.close()


def _select_template():
    _ensure_runtime_paths()
    if os.path.exists(TEMPLATE_CUSTOM):
        _log.debug("[template] usando mi_estilo.tex")
        return _read(TEMPLATE_CUSTOM)
    _log.debug("[template] usando default_template.tex")
    return _read(TEMPLATE_DEFAULT)


def _extract_latex(text):
    text = re.sub(r'```(?:latex|tex)?\s*', '', text)
    text = re.sub(r'```', '', text)
    match = re.search(r'(\\documentclass.*?\\end\{document\})', text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def _groq_client():
    return OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")


def _get_user_profile(user_id: str) -> str:
    """Read profile for CV generation. Fallback chain: user JSON → perfil_maestro → mi_perfil.md → empty."""
    import json as _json

    def _fmt(pdata: dict) -> str:
        habs   = pdata.get('habilidades', {})
        skills = [s for v in habs.values() for s in v]
        return (
            f"Nombre: {pdata.get('nombre','')} {pdata.get('apellidos','')}\n"
            f"Título: {pdata.get('titulo_profesional','')}\n"
            f"Resumen: {pdata.get('resumen','')[:400]}\n"
            f"Habilidades: {', '.join(skills[:40])}\n"
            f"Experiencia: {', '.join(str(e.get('puesto','')) for e in pdata.get('experiencia',[])[:3])}\n"
        )

    # 1. User-specific JSON profile
    user_json = get_user_profile_path(user_id)
    if os.path.exists(user_json):
        with open(user_json, encoding='utf-8') as f:
            return _fmt(_json.load(f))

    # 2. default_user → legacy perfil_maestro.json
    if user_id == 'default_user':
        maestro = os.path.join(BASE_DIR, 'data', 'perfil_maestro.json')
        if os.path.exists(maestro):
            with open(maestro, encoding='utf-8') as f:
                return _fmt(_json.load(f))

    # 3. Legacy mi_perfil.md (any user)
    md_path = os.path.join(CONTEXT_DIR, 'mi_perfil.md')
    if os.path.exists(md_path):
        return _read(md_path)

    return ""


# ── generar_terminos_busqueda ──────────────────────────────────────────────────

def generar_terminos_busqueda() -> list[str]:
    maestro_path = os.path.join(BASE_DIR, 'data', 'perfil_maestro.json')
    _FALLBACK = [
        "Desarrollador Full Stack", "Desarrollador Python",
        "Desarrollador React", "Desarrollador IoT",
        "Ingeniero Sistemas Embebidos", "Ingeniero Mecánico",
    ]
    if not os.path.exists(maestro_path):
        return _FALLBACK

    import json as _json
    with open(maestro_path, encoding='utf-8') as f:
        p = _json.load(f)

    titulo = p.get('titulo_profesional', '')
    habs   = p.get('habilidades', {})
    iot    = ' '.join(habs.get('iot_embebidos', []))
    sw     = ' '.join(habs.get('software_fullstack', []))
    mec    = ' '.join(habs.get('mecanica_manufactura', []))

    terms_sw: list[str] = []
    if 'Full-Stack' in titulo or 'Full Stack' in titulo or 'Flask' in sw or 'FastAPI' in sw:
        terms_sw += ['Desarrollador Full Stack', 'Full Stack Developer']
    if 'Python' in sw:    terms_sw.append('Desarrollador Python')
    if 'React' in sw or 'Next.js' in sw: terms_sw.append('Desarrollador React')
    if 'Docker' in sw or 'CI/CD' in sw:  terms_sw.append('DevOps Engineer')
    if 'FastAPI' in sw or 'Flask' in sw:  terms_sw.append('Backend Developer Python')
    if 'HTML/CSS/JS' in sw or 'React' in sw: terms_sw.append('Desarrollador Web')

    terms_iot: list[str] = []
    if 'IoT' in titulo or 'IoT' in iot:   terms_iot.append('Desarrollador IoT')
    if 'ESP32' in iot or 'STM32' in iot:  terms_iot.append('Ingeniero Sistemas Embebidos')
    if 'Domótica' in titulo or 'Domótica' in iot: terms_iot.append('Automatización Industrial')
    if 'MQTT' in iot or 'WiFi' in iot:    terms_iot.append('Desarrollador Firmware IoT')

    terms_mec: list[str] = []
    if 'Mecán' in titulo or 'Mecanic' in titulo:
        terms_mec += ['Ingeniero Mecánico', 'Ingeniero Mecatrónico']
    if 'SolidWorks' in mec or 'ANSYS' in mec: terms_mec.append('Ingeniero CAD CAE')
    if 'MATLAB' in mec or 'Control PID' in mec: terms_mec.append('Ingeniero Control Automático')

    all_terms: list[str] = []
    for bucket in (terms_sw, terms_iot, terms_mec):
        all_terms.extend(bucket[:4])

    seen: set[str] = set()
    unique: list[str] = []
    for t in all_terms:
        if t and t not in seen:
            seen.add(t)
            unique.append(t)
    return unique[:12] if unique else _FALLBACK


# ── Compatibilidad rápida ──────────────────────────────────────────────────────

def evaluar_compatibilidad_rapida(requerimientos: str) -> str:
    if not GROQ_API_KEY or not requerimientos.strip():
        return "Nula"
    perfil = _get_user_profile('default_user')
    if not perfil.strip():
        return "Nula"
    try:
        client = _groq_client()
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Responde ÚNICAMENTE con una de estas palabras: Alta, Media, Baja, Nula."},
                {"role": "user",   "content": f"Vacante:\n{requerimientos[:2000]}\n\nCandidato:\n{perfil[:1000]}\n\n¿Compatibilidad?"},
            ],
            temperature=0.1,
            max_tokens=10,
        )
        word = (resp.choices[0].message.content or "").strip().split()[0]
        return word if word in {"Alta", "Media", "Baja", "Nula"} else "Nula"
    except Exception as e:
        _log.warning("[compat] %s", e)
        return "Nula"


# ── Motor principal ───────────────────────────────────────────────────────────

def generar_latex_cv(vacante_id: int, user_id: str = 'default_user') -> str | None:
    row = _get_vacante(vacante_id, user_id)
    if not row:
        _log.error("Vacante #%s no encontrada para user %s.", vacante_id, user_id)
        return None
    vid, titulo, empresa, enlace, requerimientos = row

    perfil        = _get_user_profile(user_id)
    instruc_path  = os.path.join(CONTEXT_DIR, 'instrucciones_sistema.md')
    instrucciones = _read(instruc_path) if os.path.exists(instruc_path) else ""
    template_code = _select_template()

    system_msg = (
        "Eres un experto en redacción de CVs técnicos y código LaTeX. "
        "Devuelves ÚNICAMENTE código LaTeX puro. "
        "Sin bloques markdown, sin explicaciones. "
        "Empieza directamente con \\documentclass."
    )
    user_msg = f"""Genera un CV completo en LaTeX para esta vacante.

VACANTE:
- Título: {titulo}
- Empresa: {empresa}
- Enlace: {enlace}
- Requerimientos:
{requerimientos or 'No especificados'}

PERFIL DEL CANDIDATO:
{perfil or '[Sin perfil configurado — usa datos de ejemplo]'}

INSTRUCCIONES DEL SISTEMA:
{instrucciones}

PLANTILLA BASE:
{template_code}

REGLAS:
1. Código LaTeX puro, empezando con \\documentclass.
2. Adapta el título profesional al puesto exacto.
3. Usa vocabulario espejo al de la vacante.
4. Logros cuantificables cuando sea posible.
5. Máximo 1 página para puestos junior/mid."""

    _set_status(vid, "En_Proceso", user_id)
    _log.info("[IA] Generando CV vacante #%s user=%s: %s", vid, user_id, titulo[:50])

    try:
        client = _groq_client()
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=4096,
        )
        latex_raw = resp.choices[0].message.content or ""
    except Exception as e:
        _log.error("[IA ERROR] %s", e)
        _set_status(vid, "Requiere_Correccion", user_id)
        return None

    latex_clean = _extract_latex(latex_raw)
    if not latex_clean.startswith("\\documentclass"):
        _log.warning("[IA] Respuesta no parece LaTeX válido, guardando de todas formas...")

    out_dir  = get_user_outputs_dir(user_id)
    tex_path = os.path.join(out_dir, f"cv_vacante_{vid}.tex")
    with open(tex_path, 'w', encoding='utf-8') as f:
        f.write(latex_clean)
    _log.info("[tex] Guardado: %s", tex_path)
    return tex_path


def compilar_pdf(tex_path: str) -> str | None:
    if not os.path.exists(tex_path):
        _log.error("[pdflatex ERROR] No encontrado: %s", tex_path)
        raise RuntimeError(f"No existe el archivo .tex: {tex_path}")

    abs_tex     = os.path.abspath(tex_path)
    abs_out_dir = os.path.dirname(abs_tex)     # mismo directorio que el .tex
    pdf_path    = os.path.splitext(abs_tex)[0] + '.pdf'

    if os.path.exists(pdf_path):
        tex_mtime = os.path.getmtime(abs_tex)
        pdf_mtime = os.path.getmtime(pdf_path)
        if pdf_mtime >= tex_mtime - 2:
            _log.info("[pdf] Reutilizando PDF existente: %s", pdf_path)
            return pdf_path

    _log.info("[pdflatex] Compilando %s", os.path.basename(tex_path))
    try:
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode",
             f"-output-directory={abs_out_dir}", abs_tex],
            capture_output=True, text=True, timeout=60
        )
        _log.debug("[pdflatex stdout] %s", result.stdout or "(sin stdout)")
        _log.debug("[pdflatex stderr] %s", result.stderr or "(sin stderr)")
        if os.path.exists(pdf_path):
            _log.info("[pdf] Generado: %s", pdf_path)
            return pdf_path
        _log.error("[pdflatex ERROR] No se generó PDF. rc=%s", result.returncode)
        raise RuntimeError(
            f"Fallo la compilacion. rc={result.returncode}. "
            f"stdout={result.stdout[-1500:]}. stderr={result.stderr[-1500:]}"
        )
    except subprocess.TimeoutExpired:
        _log.error("[pdflatex ERROR] Timeout.")
        raise RuntimeError("pdflatex excedió el tiempo límite de 60s.")
    except FileNotFoundError:
        if os.path.exists(pdf_path):
            _log.warning("[pdflatex] No en PATH, reutilizando PDF previo.")
            return pdf_path
        _log.error("[pdflatex ERROR] pdflatex no encontrado y no hay PDF previo.")
        raise RuntimeError(
            "pdflatex no encontrado en PATH. Instala MiKTeX o TeX Live."
        )


def generar_y_compilar(vacante_id: int, user_id: str = 'default_user') -> tuple[str | None, str | None]:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY no configurada.")
    tex_path = generar_latex_cv(vacante_id, user_id)
    if not tex_path:
        return None, None
    try:
        pdf_path = compilar_pdf(tex_path)
    except Exception as e:
        _log.error("[generar_y_compilar] Error compilando PDF: %s", e)
        _set_status(vacante_id, "Requiere_Correccion", user_id)
        return tex_path, None
    if pdf_path and os.path.exists(pdf_path):
        _set_status(vacante_id, "Revisado_IA", user_id)
    else:
        _set_status(vacante_id, "Requiere_Correccion", user_id)
    return tex_path, pdf_path


if __name__ == '__main__':
    import sys as _sys
    if len(_sys.argv) < 2:
        print("Uso: python gemini_engine.py <vacante_id> [user_id]")
        _sys.exit(1)
    uid = _sys.argv[2] if len(_sys.argv) > 2 else 'default_user'
    tex, pdf = generar_y_compilar(int(_sys.argv[1]), uid)
    if pdf:   print(f"\n✓ PDF listo: {pdf}")
    elif tex: print(f"\n! .tex generado, PDF falló: {tex}")
    else:     print("\n✗ Generación fallida.")
