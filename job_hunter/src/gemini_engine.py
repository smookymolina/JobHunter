import os
import re
import subprocess
import threading
import time
import pg8000.dbapi as _pg8000
from urllib.parse import urlparse as _urlparse

import logging as _logging
from logging.handlers import RotatingFileHandler as _RotatingFileHandler

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

import google.generativeai as _genai
from google.api_core.exceptions import ResourceExhausted as _ResourceExhausted

_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mcp_debug.log')
_log = _logging.getLogger("gemini_engine")
if not _log.handlers:
    _fh = _RotatingFileHandler(os.path.abspath(_LOG_PATH), maxBytes=5_000_000, backupCount=3, encoding='utf-8')
    _fh.setFormatter(_logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    _log.addHandler(_fh)
    _log.setLevel(_logging.DEBUG)

# ── Config ────────────────────────────────────────────────────────────────────

GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_FAST = "gemini-1.5-flash"   # compat checks, inspector
GEMINI_MODEL_PRO  = "gemini-1.5-pro"     # CV / CL generation

BASE_DIR      = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
DB_PATH       = os.path.join(BASE_DIR, 'db', 'vacantes.db')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'latex_templates')
OUTPUTS_DIR   = os.path.join(BASE_DIR, 'outputs')           # root outputs dir (kept for compat)

_PROFILE_CANDIDATE = os.getenv("PROFILE_BASE_DIR", "")
CONTEXT_DIR = (_PROFILE_CANDIDATE if _PROFILE_CANDIDATE and os.path.isdir(_PROFILE_CANDIDATE)
               else os.path.join(BASE_DIR, 'context'))

TEMPLATE_CUSTOM  = os.path.join(TEMPLATES_DIR, 'mi_estilo.tex')
TEMPLATE_DEFAULT = os.path.join(TEMPLATES_DIR, 'default_template.tex')
TEMPLATE_CL      = os.path.join(TEMPLATES_DIR, 'carta_presentacion.tex')

DEFAULT_TEMPLATE_CONTENT = """% ============================================================
%  JOB HUNTER - Plantilla Base de CV
% ============================================================
\\documentclass[11pt, a4paper]{article}

\\usepackage[T1]{fontenc}
\\usepackage[utf8]{inputenc}
\\usepackage[spanish]{babel}
\\usepackage[margin=2cm, top=1.8cm, bottom=1.8cm]{geometry}
\\setlength{\\footskip}{4.5pt}
\\usepackage{bookmark}
\\usepackage{enumitem}
\\usepackage{titlesec}
\\usepackage{hyperref}
\\usepackage{xcolor}
\\usepackage{parskip}

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


def _select_cl_template():
    _ensure_runtime_paths()
    if os.path.exists(TEMPLATE_CL):
        _log.debug("[template] usando carta_presentacion.tex")
        return _read(TEMPLATE_CL)
    return ""  # Fallback si no existe


def _extract_latex(text):
    text = re.sub(r'```(?:latex|tex)?\s*', '', text)
    text = re.sub(r'```', '', text)
    match = re.search(r'(\\documentclass.*?\\end\{document\})', text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def _extract_headline(raw: str) -> str | None:
    """Extract the dynamically generated headline from the LLM's % HEADLINE: marker."""
    m = re.search(r'^%\s*HEADLINE:\s*(.+)$', raw, re.MULTILINE)
    return m.group(1).strip() if m else None


_EN_MARKERS = re.compile(
    r'\b(experience|education|summary|skills|profile|objective|engineer|manager|willing)\b',
    re.IGNORECASE,
)
_ES_MARKERS = re.compile(
    r'\b(experiencia|educaci[oó]n|resumen|habilidades|perfil|objetivo|ingeniero|disponibilidad)\b',
    re.IGNORECASE,
)


def _detect_lang(text: str) -> str:
    """Return 'en' if the text has more English section keywords than Spanish, else 'es'."""
    return 'en' if len(_EN_MARKERS.findall(text)) > len(_ES_MARKERS.findall(text)) else 'es'


def _build_header(lang: str, user_id: str = 'default_user', headline: str | None = None) -> str:
    """
    Build the personal header block dynamically from the user's profile JSON.
    headline overrides titulo_profesional when the LLM generates a job-tailored headline.
    Includes LinkedIn and GitHub as \\href links when present in the profile.
    Fallback to empty strings if a field is absent — never hardcodes personal data.
    """
    p = _load_profile_json(user_id) or {}

    nombre   = f"{p.get('nombre','')} {p.get('apellidos','')}".strip() or "Nombre Apellido"
    titulo   = headline or p.get('titulo_profesional', '')
    email    = p.get('email', '')
    telefono = p.get('telefono', '')
    linkedin = p.get('linkedin', '').strip()
    github   = p.get('github', '').strip()
    ciudad   = p.get('ubicacion', '')
    disp_raw = p.get('disponibilidad_viajar', 'Sí')

    if lang == 'en':
        titulo_hdr = titulo or 'Professional'
        disponib   = f"Willing to travel: {disp_raw}"
        ciudad_hdr = ciudad or 'Mexico City, Mexico'
    else:
        titulo_hdr = titulo or 'Profesional'
        disponib   = f"Disponibilidad para viajar: {disp_raw}"
        ciudad_hdr = ciudad or 'Ciudad de México, México'

    # ── Línea 1: teléfono | email | ciudad ───────────────────────────────────
    contact_parts: list[str] = []
    if telefono:
        contact_parts.append(telefono)
    if email:
        contact_parts.append(f"\\href{{mailto:{email}}}{{{email}}}")
    if ciudad_hdr:
        contact_parts.append(ciudad_hdr)
    contact_line = r" \quad|\quad ".join(contact_parts)

    # ── Línea 2: linkedin | github ────────────────────────────────────────────
    links_parts: list[str] = []
    if linkedin:
        ln_display = re.sub(r'^https?://(www\.)?', '', linkedin).rstrip('/')
        links_parts.append(f"\\href{{{linkedin}}}{{{ln_display}}}")
    if github:
        gh_display = re.sub(r'^https?://(www\.)?', '', github).rstrip('/')
        links_parts.append(f"\\href{{{github}}}{{{gh_display}}}")
    links_line = r" \quad|\quad ".join(links_parts)

    # ── Línea 3: disponibilidad ───────────────────────────────────────────────
    lines: list[str] = []
    if contact_line:
        lines.append(f"\\small {contact_line} \\\\ \\vspace{{1mm}}")
    if links_line:
        lines.append(f"{links_line} \\\\ \\vspace{{1mm}}")
    if disponib:
        lines.append(disponib)

    body = "\n".join(lines)

    return (
        "\\begin{center}\n"
        f"{{\\Huge \\textbf{{{nombre}}}}} \\\\ \\vspace{{2mm}}\n"
        f"{{\\large \\textit{{{titulo_hdr}}}}} \\\\ \\vspace{{2mm}}\n"
        f"{body}\n"
        "\\end{center}\n"
        "\\vspace{2mm}"
    )


def _inject_fixed_header(latex: str, header: str) -> str:
    """
    Predator injector — destroys EVERYTHING between \\begin{document} and the
    first \\section (or \\section*), then injects the canonical fixed header.

    Regex logic:
      \\begin{document}  — anchor
      .*?                — consume greedily-minimal (any LLM-generated header garbage)
      (?=\\section)      — lookahead: stop just before the first section command
    flags=DOTALL so '.' matches newlines; IGNORECASE for \\Section variants.
    Uses a lambda replacement to prevent Python from interpreting backslashes
    in the header string as regex backreferences.
    """
    if r'\begin{document}' not in latex:
        return latex
    return re.sub(
        r'\\begin\{document\}.*?(?=\\section[\s{*])',
        lambda _: r'\begin{document}' + '\n' + header + '\n',
        latex,
        count=1,
        flags=re.DOTALL | re.IGNORECASE,
    )


_GEMINI_SEM = threading.Semaphore(2)  # max 2 concurrent Gemini calls


def _gemini_call(
    system_msg: str,
    user_msg: str,
    model: str,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    """Thread-safe Gemini call. Configures API key, builds model, returns response text."""
    _genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = _genai.GenerativeModel(
        model_name=model,
        system_instruction=system_msg or None,
    )
    with _GEMINI_SEM:
        resp = gemini_model.generate_content(
            user_msg,
            generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
        )
    return resp.text or ""


def _load_profile_json(user_id: str):
    """Return raw profile dict from DB-backed JSON. None if not found."""
    import json as _json
    user_json = get_user_profile_path(user_id)
    if os.path.exists(user_json):
        with open(user_json, encoding='utf-8') as f:
            return _json.load(f)
    if user_id == 'default_user':
        maestro = os.path.join(BASE_DIR, 'data', 'perfil_maestro.json')
        if os.path.exists(maestro):
            with open(maestro, encoding='utf-8') as f:
                return _json.load(f)
    return None


def _get_user_profile(user_id: str) -> str:
    """Formatted profile string for the user_msg body (full detail)."""
    p = _load_profile_json(user_id)
    if p:
        habs   = p.get('habilidades', {})
        skills = [s for v in habs.values() for s in v]
        exp    = p.get('experiencia', [])
        exp_lines = '\n'.join(
            f"  • {e.get('puesto','')} en {e.get('empresa','')} ({e.get('periodo','')}): "
            + '; '.join(e.get('logros', [])[:2])
            for e in exp[:4]
        )
        return (
            f"Nombre: {p.get('nombre','')} {p.get('apellidos','')}\n"
            f"Título actual: {p.get('titulo_profesional','')}\n"
            f"Resumen: {p.get('resumen','')[:500]}\n"
            f"Habilidades: {', '.join(skills[:50])}\n"
            f"Experiencia relevante:\n{exp_lines}\n"
        )
    # Per-user markdown; fall back to legacy global file only if present
    md_path = os.path.join(CONTEXT_DIR, f'{user_id}_mi_perfil.md')
    if not os.path.exists(md_path):
        md_path = os.path.join(CONTEXT_DIR, 'mi_perfil.md')
    if os.path.exists(md_path):
        return _read(md_path)
    return ""


_POSGRADO_KW = ('maestría', 'maestro', 'máster', 'master', 'doctorado', 'phd', 'especialidad')
_LICENCIA_KW = ('ingeniería', 'licenciatura')


_TITULO_LLM_CORRECTIONS = [
    # LLM invents "Mastería" / "Masteria" / "Masterìa" — force correct spelling
    (re.compile(r'\bmaster[ií]a\b', re.IGNORECASE), 'maestría'),
    (re.compile(r'\bmaestria\b',    re.IGNORECASE), 'maestría'),
    # Common STEM degree words written without accents by LLMs / OCR
    (re.compile(r'\bingenieria\b',  re.IGNORECASE), 'ingeniería'),
    (re.compile(r'\bmecanica\b',    re.IGNORECASE), 'mecánica'),
    (re.compile(r'\belectronica\b', re.IGNORECASE), 'electrónica'),
    (re.compile(r'\binformatica\b', re.IGNORECASE), 'informática'),
    (re.compile(r'\bmatematicas\b', re.IGNORECASE), 'matemáticas'),
    (re.compile(r'\bfisica\b',      re.IGNORECASE), 'física'),
    (re.compile(r'\bquimica\b',     re.IGNORECASE), 'química'),
]


def _extract_titulo_academico(titulo: str) -> str:
    """Strip parenthetical annotations, correct LLM spelling errors,
    and convert degree name to professional title."""
    clean = re.sub(r'\s*\([^)]*\)\s*', '', titulo).strip()
    # Correct common LLM spelling errors BEFORE applying transformation rules
    for pattern, replacement in _TITULO_LLM_CORRECTIONS:
        clean = pattern.sub(replacement, clean)
    rules = [
        (r'(?i)^maestría en (.+)$',     r'Maestro en \1'),
        (r'(?i)^maestría (.+)$',        r'Maestro en \1'),
        (r'(?i)^ingeniería mecánica$',  r'Ingeniero Mecánico'),
        (r'(?i)^ingeniería en (.+)$',   r'Ingeniero en \1'),
        (r'(?i)^ingeniería (.+)$',      r'Ingeniero \1'),
        (r'(?i)^licenciatura en (.+)$', r'Licenciado en \1'),
        (r'(?i)^doctorado en (.+)$',    r'Doctor en \1'),
    ]
    for pat, rep in rules:
        if re.match(pat, clean):
            return re.sub(pat, rep, clean)
    return clean


def _get_user_profile_structured(user_id: str) -> dict:
    """Return structured profile fields for dynamic system-prompt injection."""
    p = _load_profile_json(user_id)
    if not p:
        return {"nombre": "", "titulo_profesional": "", "titulo_universitario": "",
                "titulo_posgrado": "", "disponibilidad": "Sí",
                "email": "", "telefono": "", "ubicacion": "",
                "resumen": "", "skills": [], "experiencia_str": ""}
    habs   = p.get('habilidades', {})
    skills = [s for v in habs.values() for s in v]
    exp    = p.get('experiencia', [])
    exp_str = '; '.join(
        f"{e.get('puesto','')} en {e.get('empresa','')} ({e.get('periodo','')})"
        for e in exp[:4]
    )
    titulo_universitario, titulo_posgrado = '', ''
    for e in p.get('educacion', []):
        t    = e.get('titulo', '')
        tlow = t.lower()
        if any(k in tlow for k in _POSGRADO_KW) and not titulo_posgrado:
            titulo_posgrado = _extract_titulo_academico(t)
        elif any(k in tlow for k in _LICENCIA_KW) and not titulo_universitario:
            titulo_universitario = _extract_titulo_academico(t)
    return {
        "nombre":               f"{p.get('nombre','')} {p.get('apellidos','')}".strip(),
        "titulo_profesional":   p.get('titulo_profesional', ''),
        "titulo_universitario": titulo_universitario,
        "titulo_posgrado":      titulo_posgrado,
        "disponibilidad":       p.get('disponibilidad_viajar', 'Sí'),
        "email":                p.get('email', ''),
        "telefono":             p.get('telefono', ''),
        "ubicacion":            p.get('ubicacion', ''),
        "resumen":              p.get('resumen', '')[:600],
        "skills":               skills[:50],
        "experiencia_str":      exp_str,
    }


def regenerate_mi_perfil(user_id: str = 'default_user') -> str:
    """Regenerates mi_perfil.md from the JSON profile of the given user."""
    data = _load_profile_json(user_id)
    if not data:
        return ""
    
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
    md_path = os.path.join(CONTEXT_DIR, f"{user_id}_mi_perfil.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    return md_path


# ── generar_terminos_busqueda ──────────────────────────────────────────────────

def generar_terminos_busqueda(user_id: str = 'default_user') -> list[str]:
    maestro_path = get_user_profile_path(user_id)
    if not os.path.exists(maestro_path):
        maestro_path = os.path.join(BASE_DIR, 'data', 'perfil_maestro.json')
    
    _FALLBACK = [
        "Ingeniero", "Desarrollador", "Analista",
        "Técnico", "Especialista", "Coordinador",
    ]
    if not os.path.exists(maestro_path):
        return _FALLBACK

    import json as _json
    with open(maestro_path, encoding='utf-8') as f:
        p = _json.load(f)

    # Inyección de términos exitosos (Feedback Loop)
    winning = _get_winning_skills(user_id)
    winning_terms = []
    if winning:
        for s in winning.split(", "):
            skill = s.split(" (")[0]
            winning_terms.append(f"Desarrollador {skill}")
            winning_terms.append(f"Ingeniero {skill}")

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
    if 'SolidWorks' in mec or 'ANSYS' in mec:
        terms_mec += ['Diseñador Mecánico', 'Ingeniero CAD CAE']
    if 'MATLAB' in mec or 'Control PID' in mec:
        terms_mec.append('Ingeniero Control Automático')
    if 'Instrumentación' in mec or 'DAQ' in mec:
        terms_mec.append('Ingeniero de Manufactura')
    if 'Análisis térmico' in mec or 'Térmic' in titulo:
        terms_mec.append('Ingeniero Térmico')

    # Priority: winning → mec → IoT → software (mec first since profile is primarily mechanical)
    all_terms: list[str] = winning_terms[:4]
    for bucket in (terms_mec, terms_iot, terms_sw):
        all_terms.extend(bucket[:6])

    seen: set[str] = set()
    unique: list[str] = []
    for t in all_terms:
        if t and t not in seen:
            seen.add(t)
            unique.append(t)
    return unique[:20] if unique else _FALLBACK


# ── Compatibilidad rápida ──────────────────────────────────────────────────────

# Keyed by user_id — each user gets their own cached compact profile
_COMPAT_PROFILE_CACHE: dict[str, str] = {}


def clear_compat_cache(user_id: str | None = None) -> None:
    """Evict one user (or all) from the compat profile cache after a profile save."""
    if user_id is None:
        _COMPAT_PROFILE_CACHE.clear()
    else:
        _COMPAT_PROFILE_CACHE.pop(user_id, None)


def _get_profile_for_compat(user_id: str = 'default_user') -> str:
    """Compact profile (title + top-20 skills) cached per user per process."""
    if user_id in _COMPAT_PROFILE_CACHE:
        return _COMPAT_PROFILE_CACHE[user_id]
    p = _load_profile_json(user_id)
    if not p:
        return ""
    habs = p.get('habilidades', {})
    # Sample up to 5 skills per category so all areas are represented (not just the first category)
    skills: list[str] = []
    for v in habs.values():
        skills.extend(v[:5])
    entry = f"Título: {p.get('titulo_profesional', '')}\nSkills: {', '.join(skills[:20])}"
    _COMPAT_PROFILE_CACHE[user_id] = entry
    return entry


def evaluar_compatibilidad_rapida(requerimientos: str, user_id: str = 'default_user') -> str:
    if not GEMINI_API_KEY or not requerimientos.strip():
        return "Nula"
    perfil = _get_profile_for_compat(user_id)
    if not perfil:
        return "Nula"
    sys_msg = "Responde ÚNICAMENTE con una de estas palabras: Alta, Media, Baja o Nula."
    usr_msg = f"Vacante:\n{requerimientos[:800]}\n\nCandidato:\n{perfil}\n\n¿Compatibilidad?"
    for attempt in range(3):
        try:
            raw = _gemini_call(sys_msg, usr_msg, GEMINI_MODEL_FAST, temperature=0.0, max_tokens=10)
            word = raw.strip().split()[0] if raw.strip() else "Nula"
            return word if word in {"Alta", "Media", "Baja", "Nula"} else "Nula"
        except _ResourceExhausted:
            wait = 2 ** attempt * 3  # 3s, 6s, 12s
            _log.warning("[compat] rate-limit, retrying in %ss (attempt %d/3)", wait, attempt + 1)
            time.sleep(wait)
        except Exception as e:
            _log.warning("[compat] error: %s", e)
            return "Nula"
    _log.error("[compat] all retries exhausted for user=%s", user_id)
    return "Nula"


# ── Motor principal ───────────────────────────────────────────────────────────

def _get_entrevista_context(user_id: str) -> str:
    """Return a brief summary of vacantes that led to interviews for reinforcement."""
    try:
        conn = _db()
        cur  = conn.cursor()
        cur.execute(
            "SELECT titulo, empresa, requerimientos FROM vacantes "
            "WHERE user_id=%s AND status='Entrevista' AND requerimientos IS NOT NULL "
            "ORDER BY fecha_registro DESC LIMIT 3",
            (user_id,)
        )
        rows = cur.fetchall()
        cur.close(); conn.close()
        if not rows:
            return ""
        return '\n'.join(
            f"• Entrevista: {r[0]} en {r[1]} — req: {(r[2] or '')[:180]}"
            for r in rows
        )
    except Exception:
        return ""


def _get_winning_skills(user_id: str) -> str:
    """Return top 5 high-conversion skills based on previous successes."""
    try:
        conn = _db()
        cur = conn.cursor()
        cur.execute(
            "SELECT requerimientos FROM vacantes "
            "WHERE user_id=%s AND status IN ('Entrevista', 'Listo_Manual') AND requerimientos IS NOT NULL",
            (user_id,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if not rows: return ""
        
        counts = {}
        # Lista simplificada para el motor IA
        kws = ["Python", "JavaScript", "React", "Node.js", "Docker", "AWS", "FastAPI", "IoT", "Embedded"]
        for r in rows:
            text = r[0].lower()
            for kw in kws:
                if kw.lower() in text:
                    counts[kw] = counts.get(kw, 0) + 1
        top = sorted(counts.items(), key=lambda x: -x[1])[:5]
        return ", ".join([f"{k} (Alta Conversión)" for k, _ in top])
    except Exception:
        return ""


def generar_latex_cv(vacante_id: int, user_id: str = 'default_user') -> str | None:
    row = _get_vacante(vacante_id, user_id)
    if not row:
        _log.error("Vacante #%s no encontrada para user %s.", vacante_id, user_id)
        return None
    vid, titulo, empresa, enlace, requerimientos = row

    # ── Datos dinámicos del usuario (BD → JSON) ───────────────────────────────
    prof                 = _get_user_profile_structured(user_id)
    perfil_full          = _get_user_profile(user_id)
    nombre_usuario       = prof["nombre"]
    telefono_usuario     = prof["telefono"]
    correo_usuario       = prof["email"]
    ubicacion_usuario    = prof["ubicacion"]
    titulo_universitario = prof["titulo_universitario"]
    titulo_posgrado      = prof["titulo_posgrado"]
    disponibilidad       = prof["disponibilidad"]
    user_summary         = prof["resumen"] or "(perfil no configurado — rellena tu perfil en /perfil)"
    user_skills          = ', '.join(prof["skills"]) if prof["skills"] else "(sin habilidades registradas)"
    user_exp             = prof["experiencia_str"] or "(sin experiencia registrada)"

    winning_skills = _get_winning_skills(user_id)

    instruc_path  = os.path.join(CONTEXT_DIR, 'instrucciones_sistema.md')
    instrucciones = _read(instruc_path) if os.path.exists(instruc_path) else ""
    template_code = _select_template()

    # ── System prompt maestro v2 — 100% dinámico ─────────────────────────────
    system_msg = (
        "Eres redactor experto en CVs técnicos de ingeniería. "
        "Devuelves ÚNICAMENTE código LaTeX compilable. Sin bloques markdown, sin explicaciones.\n\n"

        "=== PASO 0 — DETECCIÓN DE IDIOMA ===\n"
        "Analiza el título y los requerimientos de la vacante. "
        "Si >60\\% de los requerimientos están en inglés → IDIOMA = EN. Si no → IDIOMA = ES. "
        "Mantén ese idioma en TODO el documento sin excepción. "
        "PROHIBIDO mezclar idiomas. Excepción: nombres propios de herramientas (SolidWorks, ANSYS, "
        "Python, MATLAB, ESP32, STM32, MQTT, CATIA, AutoCAD). "
        "Labels EN: Technical Skills | Professional Experience | Education | Key Projects. "
        "Labels ES: Habilidades Técnicas | Experiencia Profesional | Educación | Proyectos.\n\n"

        "=== PASO 1 — HEADLINE (OBLIGATORIO) ===\n"
        "Construye un headline personalizado para ESTA vacante con el formato: "
        "[Dominio principal] | [Especialidad 1] & [Especialidad 2]. "
        "Ejemplos: 'Mechanical Design Engineer | CAD/CAE & Systems Integration', "
        "'Automation & Embedded Systems Engineer | IoT & DAQ'. "
        "NUNCA uses el título exacto de la vacante. "
        "Escribe el headline en la PRIMERA LÍNEA del código generado como comentario LaTeX: "
        "% HEADLINE: <tu headline aquí>\n\n"

        "=== PASO 2 — TONO (LISTA NEGRA) ===\n"
        "PROHIBIDO USAR: 'Highly motivated', 'Strong background', 'Team player', "
        "'Results-driven', 'Orientado a resultados', 'Proactivo', "
        "'Profesional con X años de experiencia', 'Apasionado por'. "
        "ESTRUCTURA OBLIGATORIA para bullets: "
        "[Verbo de acción] + [tecnología/herramienta] + [resultado o contexto medible].\n\n"

        "=== PERFIL DEL CANDIDATO ===\n"
        f"Nombre: {nombre_usuario}\n"
        f"Resumen: {user_summary}\n"
        f"Skills: {user_skills}\n"
        f"Experiencia: {user_exp}\n\n"

        "=== MÉTRICAS DE CONVERSIÓN ===\n"
        f"Skills alta conversión (prioriza si aplican): {winning_skills}\n\n"

        "=== PASO 3 — CONTENIDO EXCLUSIVO ===\n"
        "Incluye ÚNICAMENTE tecnologías y experiencias del perfil del candidato. "
        "NUNCA inventes habilidades, certificaciones ni experiencias ausentes del perfil. "
        "Incluye la publicación IAC 2024 (DOI: 10.52202/078365-0120) si la vacante es técnica/académica.\n\n"

        "=== PASO 4 — ESTRUCTURA LATEX ESTRICTA ===\n"
        "REGLA CRÍTICA: TIENES ESTRICTAMENTE PROHIBIDO colocar bloques \\begin{center}, "
        "macros de cabecera, nombre, contacto o cualquier datos personales en el cuerpo del documento. "
        "El encabezado personal es INYECTADO AUTOMÁTICAMENTE por el sistema con esta distribución en 3 líneas:\n"
        "  \\begin{center}\n"
        "    {\\Huge \\textbf{ {nombre} }} \\\\ \\vspace{2mm}\n"
        "    {\\large \\textit{ {headline_generado} }} \\\\ \\vspace{2mm}\n"
        "    \\small {telefono} \\quad|\\quad {email} \\quad|\\quad {ciudad} \\\\ \\vspace{1mm}\n"
        "    linkedin.com/in/jair-molina-arce \\quad|\\quad github.com/smookymolina \\\\ \\vspace{1mm}\n"
        "    Willing to travel: Yes (o Disponibilidad para viajar: Sí)\n"
        "  \\end{center}\n"
        "  \\vspace{2mm}\n"
        "El documento DEBE ir directo a las secciones después de \\begin{document}.\n"
        "El orden de secciones es:\n"
        "  1. Professional Summary / Perfil Profesional (párrafo continuo, máx 4 líneas)\n"
        "  2. Technical Skills / Habilidades Técnicas — usa ESTAS categorías exactas:\n"
        "     \\textbf{CAD / CAE:} SolidWorks, CATIA, AutoCAD, ANSYS...\n"
        "     \\textbf{Mechanical Design:} 2D/3D modeling, GD\\&T, tolerance analysis...\n"
        "     \\textbf{Manufacturing \\& Process:} CNC machining, lean methods, metrology...\n"
        "     \\textbf{Automation \\& Control:} Embedded systems (ESP32, STM32), DAQ, MATLAB/Simulink...\n"
        "     \\textbf{Languages:} Spanish (native) | English: Professional Fluency C1/C2\n"
        "  3. Professional Experience / Experiencia Profesional — formato:\n"
        "     \\noindent \\textbf{Job Title} \\hfill \\textbf{Year -- Year} \\\\\n"
        "     \\textit{Company/Institution} \\hfill \\textit{Location} \\\\\n"
        "     \\vspace{-2mm}\n"
        "     \\begin{itemize} \\itemsep -2pt\n"
        "         \\item Bullet 1\n"
        "     \\end{itemize}\n"
        "  4. Education / Educación\n"
        "  5. Key Projects / Proyectos (si hay espacio)\n\n"

        "=== EXACT MATCH — REQUISITOS INDISPENSABLES ===\n"
        "Identifica los requisitos marcados como INDISPENSABLE, EXCLUYENTE o REQUISITO. "
        "Escribe ESAS PALABRAS EXACTAS en Perfil Profesional o Habilidades.\n\n"

        "=== PROTECCIÓN LATEX ===\n"
        "- Preámbulo: incluye \\usepackage[utf8]{inputenc}, \\usepackage[spanish]{babel} "
        "(o [english] si IDIOMA=EN), \\usepackage{bookmark}. "
        "Añade \\setlength{\\footskip}{4.5pt} tras \\usepackage{geometry}.\n"
        "- Listas: usa \\begin{itemize}/\\item. NUNCA llaves sueltas como viñetas.\n"
        "- TIENES ESTRICTAMENTE PROHIBIDO usar \\\\ dentro de \\item. "
        "Usa \\newline para saltos dentro de items.\n"
        "- Escapa: \\%, \\&, \\#, \\_. No uses $ para texto regular.\n"
        "- PROHIBIDO \\usepackage{fontawesome5} — causa conflictos en el sistema.\n"
        "- Sin Markdown dentro del LaTeX."
    )

    entrevista_ctx = _get_entrevista_context(user_id)
    if entrevista_ctx:
        system_msg += (
            "\n\n=== CONTEXTO DE ÉXITO (ENTREVISTAS PREVIAS) ===\n"
            f"{entrevista_ctx}\n"
            "Prioriza resaltar habilidades y enfoques similares para maximizar la conversión."
        )

    # Pre-detect language from vacante data (before LLM call) so it's authoritative
    lang = _detect_lang(titulo + " " + (requerimientos or "")[:1000])
    lang_label = "EN (English)" if lang == 'en' else "ES (Español)"

    user_msg = f"""Generate a complete LaTeX CV for the following job vacancy.

VACANCY:
- Title: {titulo}
- Company: {empresa}
- Link: {enlace}
- Requirements:
{requerimientos or 'Not specified'}

CANDIDATE FULL PROFILE:
{perfil_full or '[No profile configured]'}

ADDITIONAL INSTRUCTIONS:
{instrucciones}

BASE TEMPLATE:
{template_code}

MANDATORY FORMAT RULES:
1. LANGUAGE: {lang_label} — Write ALL section names, bullets and text in this language.
2. FIRST LINE of the code MUST be the headline comment: % HEADLINE: [Domain] | [Specialty 1] & [Specialty 2]
   Example: % HEADLINE: Mechanical Engineering Specialist | Automotive Systems & Design/Release
3. Second line must be \\documentclass. No other code before \\documentclass.
4. Use mirror vocabulary from the vacancy keywords.
5. Quantifiable achievements whenever possible.
6. Maximum 1 page for junior/mid positions."""

    _set_status(vid, "En_Proceso", user_id)
    _log.info("[IA] Generando CV vacante #%s user=%s lang=%s: %s", vid, user_id, lang, titulo[:50])

    try:
        latex_raw = _gemini_call(system_msg, user_msg, GEMINI_MODEL_PRO, temperature=0.3, max_tokens=4096)
    except Exception as e:
        _log.error("[IA ERROR] %s", e)
        _set_status(vid, "Requiere_Correccion", user_id)
        return None

    headline = _extract_headline(latex_raw)
    fixed_header = _build_header(lang, user_id, headline=headline)
    _log.info("[IA] Idioma: %s | Headline: %s", lang, headline or "(desde perfil)")
    latex_clean = _inject_fixed_header(_extract_latex(latex_raw), fixed_header)
    if not latex_clean.startswith("\\documentclass"):
        _log.warning("[IA] Respuesta no parece LaTeX válido, guardando de todas formas...")

    out_dir  = get_user_outputs_dir(user_id)
    tex_path = os.path.join(out_dir, f"cv_vacante_{vid}.tex")
    with open(tex_path, 'w', encoding='utf-8') as f:
        f.write(latex_clean)
    _log.info("[tex] Guardado: %s", tex_path)
    return tex_path


def generar_latex_cl(vacante_id: int, user_id: str = 'default_user') -> str | None:
    row = _get_vacante(vacante_id, user_id)
    if not row:
        _log.error("Vacante #%s no encontrada para user %s.", vacante_id, user_id)
        return None
    vid, titulo, empresa, enlace, requerimientos = row

    prof          = _get_user_profile_structured(user_id)
    perfil_full   = _get_user_profile(user_id)
    template_code = _select_cl_template()

    system_msg = (
        "Eres un experto redactor de cartas de presentación (Cover Letters) de alto impacto. "
        "Devuelves ÚNICAMENTE código LaTeX compilable. Sin markdown, sin explicaciones.\n\n"

        "=== REGLA CRÍTICA DE INICIO ===\n"
        "TIENES ESTRICTAMENTE PROHIBIDO generar el encabezado personal (nombre, contacto). "
        "Empieza directamente con la fecha o el destinatario. "
        "EL ENCABEZADO SERÁ INYECTADO POR EL SISTEMA.\n\n"

        "=== ESTRUCTURA DE LA CARTA ===\n"
        "1. GANCHO: Menciona el puesto específico y por qué te entusiasma.\n"
        "2. POR QUÉ YO: Conecta tus logros específicos (especialmente IoT, Full-Stack, Mecánica) con los dolores de la empresa.\n"
        "3. POR QUÉ USTEDES: Demuestra conocimiento de la empresa/industria.\n"
        "4. CALL TO ACTION: Pide una entrevista de forma profesional.\n\n"

        "=== TONO ===\n"
        "Profesional, seguro de sí mismo pero humilde, y extremadamente personalizado. "
        "USA VOCABULARIO ESPEJO de la vacante.\n\n"

        "=== PROTECCIÓN LATEX ===\n"
        "- Usa la plantilla proporcionada.\n"
        "- Escapa caracteres especiales (\\%, \\&).\n"
        "- NO uses paquetes externos no definidos en la plantilla."
    )

    user_msg = f"""Genera una Carta de Presentación en LaTeX para esta vacante.

VACANTE:
- Título: {titulo}
- Empresa: {empresa}
- Requerimientos: {requerimientos or 'No especificados'}

PERFIL COMPLETO:
{perfil_full}

PLANTILLA:
{template_code}

REGLAS:
1. Reemplaza los marcadores {{{{FECHA}}}}, {{{{EMPRESA}}}}, {{{{UBICACION_EMPRESA}}}}, {{{{SALUDO}}}}, {{{{CUERPO_CARTA}}}} con contenido real.
2. La fecha debe ser la de hoy (11 de junio de 2026).
3. Idioma: Detecta el idioma de la vacante y escribe la carta en ese mismo idioma (Inglés o Español).
"""

    try:
        latex_raw = _gemini_call(system_msg, user_msg, GEMINI_MODEL_PRO, temperature=0.5, max_tokens=2048)
    except Exception as e:
        _log.error("[CL IA ERROR] %s", e)
        return None

    lang = _detect_lang(titulo + " " + latex_raw)
    fixed_header = _build_header(lang, user_id)
    latex_clean = _inject_fixed_header(_extract_latex(latex_raw), fixed_header)

    out_dir  = get_user_outputs_dir(user_id)
    tex_path = os.path.join(out_dir, f"cl_vacante_{vid}.tex")
    with open(tex_path, 'w', encoding='utf-8') as f:
        f.write(latex_clean)
    _log.info("[cl tex] Guardado: %s", tex_path)
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
            ["pdflatex", "-interaction=nonstopmode", "-no-shell-escape",
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
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY no configurada.")
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


def generar_cl_y_compilar(vacante_id: int, user_id: str = 'default_user') -> tuple[str | None, str | None]:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY no configurada.")
    tex_path = generar_latex_cl(vacante_id, user_id)
    if not tex_path:
        return None, None
    try:
        pdf_path = compilar_pdf(tex_path)
    except Exception as e:
        _log.error("[generar_cl_y_compilar] Error compilando PDF: %s", e)
        return tex_path, None
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
