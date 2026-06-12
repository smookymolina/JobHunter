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
TEMPLATE_CL      = os.path.join(TEMPLATES_DIR, 'carta_presentacion.tex')

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


def _build_header(lang: str) -> str:
    """Return the hardcoded personal header block in the requested language."""
    if lang == 'en':
        subtitulo = "{\\Large \\textit{Mechanical Engineer | Master in Advanced Technologies}}"
        disponib  = "Willing to travel: Yes"
        ciudad    = "Mexico City, Mexico"
    else:
        subtitulo = "{\\Large \\textit{Ingeniero Mecánico | Maestro en Tecnologías Avanzadas}}"
        disponib  = "Disponibilidad para viajar: Sí"
        ciudad    = "Ciudad de México, México"
    return (
        "\\begin{center}\n"
        + "{\\Huge \\textbf{Jair Molina Arce}} \\\\ \\vspace{2mm}\n"
        + subtitulo + " \\\\ \\vspace{1mm}\n"
        + "\\small 5652646108 | ingjairmolina@gmail.com | " + ciudad + " | " + disponib + "\n"
        + "\\end{center}\n"
        + "\\vspace{2mm}"
    )


def _inject_fixed_header(latex: str, header: str) -> str:
    """Inject the fixed header immediately after \\begin{document}.
    The LLM is instructed to emit nothing before the first \\section, so a plain
    string replacement on the first occurrence is sufficient and unambiguous."""
    if r'\begin{document}' in latex:
        return latex.replace(r'\begin{document}', r'\begin{document}' + '\n' + header, 1)
    return latex


def _groq_client():
    return OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")


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
    md_path = os.path.join(CONTEXT_DIR, 'mi_perfil.md')
    if os.path.exists(md_path):
        return _read(md_path)
    return ""


_POSGRADO_KW = ('maestría', 'maestro', 'máster', 'master', 'doctorado', 'phd', 'especialidad')
_LICENCIA_KW = ('ingeniería', 'licenciatura')


def _extract_titulo_academico(titulo: str) -> str:
    """Strip parenthetical annotations and convert degree name to professional title."""
    clean = re.sub(r'\s*\([^)]*\)\s*', '', titulo).strip()
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


# ── generar_terminos_busqueda ──────────────────────────────────────────────────

def generar_terminos_busqueda(user_id: str = 'default_user') -> list[str]:
    maestro_path = get_user_profile_path(user_id)
    if not os.path.exists(maestro_path):
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
    if 'SolidWorks' in mec or 'ANSYS' in mec: terms_mec.append('Ingeniero CAD CAE')
    if 'MATLAB' in mec or 'Control PID' in mec: terms_mec.append('Ingeniero Control Automático')

    all_terms: list[str] = winning_terms[:4]
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

_COMPAT_PROFILE_CACHE: str | None = None


def _get_profile_for_compat(user_id: str = 'default_user') -> str:
    """Compact profile (title + skills) for fast compatibility evaluation — cached per process."""
    global _COMPAT_PROFILE_CACHE
    if _COMPAT_PROFILE_CACHE is not None:
        return _COMPAT_PROFILE_CACHE
    p = _load_profile_json(user_id)
    if not p:
        return ""
    habs = p.get('habilidades', {})
    skills = [s for v in habs.values() for s in v][:30]
    _COMPAT_PROFILE_CACHE = (
        f"Título: {p.get('titulo_profesional', '')}\n"
        f"Skills: {', '.join(skills)}"
    )
    return _COMPAT_PROFILE_CACHE


def evaluar_compatibilidad_rapida(requerimientos: str) -> str:
    if not GROQ_API_KEY or not requerimientos.strip():
        return "Nula"
    perfil = _get_profile_for_compat()
    if not perfil:
        return "Nula"
    try:
        client = _groq_client()
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Responde ÚNICAMENTE con una de estas palabras: Alta, Media, Baja, Nula."},
                {"role": "user",   "content": f"Vacante:\n{requerimientos[:1200]}\n\nCandidato:\n{perfil}\n\n¿Compatibilidad?"},
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

    # ── System prompt maestro — 100% dinámico ────────────────────────────────
    system_msg = (
        "Eres redactor ejecutivo de CVs técnicos. Devuelves ÚNICAMENTE código LaTeX compilable. "
        "Sin bloques markdown, sin explicaciones. Empieza con \\documentclass.\n\n"

        "=== MÉTRICAS DE CONVERSIÓN ===\n"
        f"Skills alta conversión (prioriza si aplican): {winning_skills}\n\n"

        "=== PERFIL DEL CANDIDATO ===\n"
        f"Resumen: {user_summary}\n"
        f"Skills: {user_skills}\n"
        f"Experiencia: {user_exp}\n\n"

        "=== REGLA CRÍTICA DE INICIO ===\n"
        "TIENES ESTRICTAMENTE PROHIBIDO generar cualquier tipo de encabezado, nombre, "
        "título profesional, correo, teléfono o datos de contacto al inicio del documento. "
        "Debes comenzar el contenido del CV DIRECTAMENTE con el primer comando de sección. "
        "Ejemplo correcto: \\section{PROFESSIONAL PROFILE} o \\section{PERFIL PROFESIONAL}. "
        "CERO texto, CERO \\begin{center}, CERO datos personales antes de la primera sección.\n\n"

        "=== EXACT MATCH — REQUISITOS INDISPENSABLES ===\n"
        "Identifica los requisitos marcados como INDISPENSABLE, EXCLUYENTE o REQUISITO. "
        "Escribe ESAS PALABRAS EXACTAS en Perfil Profesional o Habilidades. "
        "Ejemplos: si pide 'auto estándar y camionetas Pick Up' → escribe exactamente eso, "
        "no 'manejo de vehículo'. Si pide 'disponibilidad de rolar turnos' → escribe exactamente eso.\n\n"

        "=== REGLAS FIJAS ===\n"
        "1. INGLÉS: Siempre 'Inglés: Dominio Profesional Fluido (C1/C2)'. PROHIBIDO 'intermedio'.\n"
        "2. TONO DIRECTO: PROHIBIDO iniciar el Perfil con frases genéricas ('Profesional con X años...', "
        "'Apasionado por...', 'Orientado a...'). Ve directo a la propuesta de valor técnica "
        "específica a los problemas operativos de ESTA empresa.\n"
        "3. ANTI-ALUCINACIÓN: No inventes habilidades, certs ni experiencias ausentes del perfil.\n"
        "4. PAR: Logros en formato Problema→Acción→Resultado. Cuantifica cuando sea posible.\n\n"

        "=== PROTECCIÓN LATEX ===\n"
        "- Preámbulo: incluye \\usepackage[utf8]{inputenc}, \\usepackage[spanish]{babel}.\n"
        "- Listas: usa \\begin{itemize}/\\item. NUNCA llaves sueltas como viñetas.\n"
        "- Escapa: \\%, \\&, \\#, \\_. No uses $ para texto regular.\n"
        "- Sin Markdown dentro del LaTeX."
    )

    entrevista_ctx = _get_entrevista_context(user_id)
    if entrevista_ctx:
        system_msg += (
            "\n\n=== CONTEXTO DE ÉXITO (ENTREVISTAS PREVIAS) ===\n"
            f"{entrevista_ctx}\n"
            "Prioriza resaltar habilidades y enfoques similares para maximizar la conversión."
        )

    user_msg = f"""Genera un CV completo en LaTeX para esta vacante.

VACANTE:
- Título: {titulo}
- Empresa: {empresa}
- Enlace: {enlace}
- Requerimientos:
{requerimientos or 'No especificados'}

PERFIL COMPLETO DEL CANDIDATO:
{perfil_full or '[Sin perfil configurado]'}

INSTRUCCIONES ADICIONALES:
{instrucciones}

PLANTILLA BASE:
{template_code}

REGLAS DE FORMATO:
1. Código LaTeX puro, empezando con \\documentclass.
2. Usa vocabulario espejo al de la vacante (keywords de la descripción).
3. Logros cuantificables cuando sea posible.
4. Máximo 1 página para puestos junior/mid."""

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

    lang = _detect_lang(titulo + " " + latex_raw)
    fixed_header = _build_header(lang)
    _log.info("[IA] Idioma detectado: %s", lang)
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
        client = _groq_client()
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.5,
            max_tokens=2048,
        )
        latex_raw = resp.choices[0].message.content or ""
    except Exception as e:
        _log.error("[CL IA ERROR] %s", e)
        return None

    lang = _detect_lang(titulo + " " + latex_raw)
    fixed_header = _build_header(lang)
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


def generar_cl_y_compilar(vacante_id: int, user_id: str = 'default_user') -> tuple[str | None, str | None]:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY no configurada.")
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
