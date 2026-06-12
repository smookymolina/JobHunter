"""
Browser Agent — scraping con Playwright (headless, anti-bot evasion).
Cada vacante se envía vía POST al API REST.

Uso:
    python browser_agent.py --limit 5
    python browser_agent.py --limit 5 --terms "IoT Developer" "Backend Python"
    python browser_agent.py --limit 10 --filtros '{"ubicacion":"Ciudad de México","modalidad":"remoto","pais":"Mexico","min_salary":16000}'
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import argparse
import json
import os
import time
import random
import unicodedata
import urllib.request
import urllib.error
import urllib.parse
import re as _re
import xml.etree.ElementTree as _ET
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser as _HTMLParser

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from playwright.sync_api import sync_playwright, Page
from gemini_engine import generar_terminos_busqueda, evaluar_compatibilidad_rapida

# ── Config ────────────────────────────────────────────────────────────────────

API_BASE       = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
MAX_PER_TERM   = 8
HEADLESS       = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() != "false"
MAX_WORKERS    = int(os.getenv("SCRAPER_WORKERS", "3"))

# Thread-safe counter and user identity/config (set in main before spawning workers)
_counter_lock       = threading.Lock()
_SCRAPER_USER_ID    = "default_user"
_SCRAPER_MIN_COMPAT = "Baja"
_COMPAT_ORDER       = {"Alta": 3, "Media": 2, "Baja": 1, "Nula": 0}
_SCRAPER_LIMITE: int | None = None   # set in main; used by _incr to fire stop event
_stop_event         = threading.Event()  # set when limit reached → all workers halt ASAP

# FIX: usar mx.computrabajo.com (www.computrabajo.com.mx redirige a .com internacional)
_CT_DOMINIOS: dict[str, str] = {
    "Mexico":        "https://mx.computrabajo.com",
    "España":        "https://www.computrabajo.es",
    "Argentina":     "https://www.computrabajo.com.ar",
    "Colombia":      "https://www.computrabajo.com.co",
    "Chile":         "https://www.computrabajo.cl",
    "Internacional": "https://mx.computrabajo.com",
}

_ALL_PLATFORMS = {"computrabajo", "occ", "bumeran", "getonbrd", "remotive", "linkedin"}

_FILTROS_DEFAULT: dict = {
    "ubicacion": "", "modalidad": "any", "pais": "Mexico",
    "min_salary": None, "platforms": list(_ALL_PLATFORMS),
}

# Rotación de User-Agents (Chrome 124–126, Windows/Mac)
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
]

# ── Text normalization ─────────────────────────────────────────────────────────

_PUNCT_RE = _re.compile(r"[.,;:!?/\\()\[\]{}\"\'\-–—_]+")


def _normalize_text(text: str) -> str:
    """Lowercase + strip accents + replace punctuation with spaces + collapse whitespace."""
    nfd     = unicodedata.normalize("NFD", text.lower())
    no_acc  = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    no_pct  = _PUNCT_RE.sub(" ", no_acc)
    return " ".join(no_pct.split())


def _word_match(term: str, text: str) -> bool:
    """True if `term` appears as whole words in `text` (both already normalized)."""
    return bool(_re.search(r"(?<!\w)" + _re.escape(term) + r"(?!\w)", text))


# ── Geographic profiles ────────────────────────────────────────────────────────
# Each profile: {"url_names": [...], "aliases": [...positive], "exclusions": [...hard-reject]}
# All terms stored pre-normalized (no accents, lowercase, no punctuation).

_P_CDMX: dict = {
    "url_names": ["Ciudad de México", "CDMX"],
    "aliases": [
        "cdmx", "ciudad de mexico", "ciudad de mx", "distrito federal", "d f",
        # Alcaldías
        "miguel hidalgo", "cuauhtemoc", "benito juarez", "coyoacan",
        "iztapalapa", "tlalpan", "azcapotzalco", "alvaro obregon",
        "iztacalco", "xochimilco", "gustavo a madero", "venustiano carranza",
        "tlahuac", "milpa alta", "magdalena contreras",
        # Colonias / zonas de referencia
        "polanco", "santa fe", "condesa", "roma norte", "roma sur",
        "del valle", "narvarte", "pedregal", "lomas chapultepec",
        "tlatelolco", "anzures", "doctores", "centro historico",
        # Acrónimos metropolitanos
        "zmcm", "zmvm", "zona metropolitana ciudad de mexico",
    ],
    "exclusions": [
        # Estado de México — el falso positivo más común
        "estado de mexico", "edomex", "edo mex",
        "ecatepec", "naucalpan", "tlalnepantla", "nezahualcoyotl", "neza",
        "texcoco", "cuautitlan", "tultitlan", "atizapan", "coacalco",
        "chimalhuacan", "chalco", "ixtapaluca",
        # Toluca capital del Edomex
        "toluca",
        # Resto del país
        "monterrey", "nuevo leon",
        "guadalajara", "jalisco",
        "puebla",
        "queretaro",
        "veracruz",
        "chihuahua",
        "tijuana", "baja california",
        "mexicali",
        "hermosillo", "sonora",
        "merida", "yucatan",
        "cancun", "quintana roo",
        "saltillo", "coahuila",
        "san luis potosi",
        "aguascalientes",
        "morelia", "michoacan",
        "leon gto", "guanajuato",
        "oaxaca",
        "acapulco", "guerrero",
        "cuernavaca", "morelos",
        "tampico", "tamaulipas",
        "culiacan", "sinaloa",
        "durango",
        "zacatecas",
        "tuxtla gutierrez", "chiapas",
    ],
}

_P_MTY: dict = {
    "url_names": ["Monterrey"],
    "aliases": [
        "monterrey", "mty", "nuevo leon", "guadalupe nl",
        "san pedro garza garcia", "santa catarina nl",
        "apodaca", "escobedo", "san nicolas de los garza",
        "garcia nl",
    ],
    "exclusions": [
        "cdmx", "ciudad de mexico", "guadalajara", "puebla",
        "queretaro", "veracruz", "tijuana",
    ],
}

_P_GDL: dict = {
    "url_names": ["Guadalajara"],
    "aliases": [
        "guadalajara", "gdl", "jalisco", "zapopan", "tlaquepaque",
        "tonala", "tlajomulco", "zona metropolitana guadalajara",
    ],
    "exclusions": [
        "cdmx", "ciudad de mexico", "monterrey", "puebla", "queretaro",
    ],
}

_P_EDOMEX: dict = {
    "url_names": ["Estado de México", "Toluca"],
    "aliases": [
        "estado de mexico", "edomex", "toluca",
        "ecatepec", "naucalpan", "tlalnepantla", "nezahualcoyotl",
        "texcoco", "cuautitlan", "tultitlan", "atizapan", "coacalco",
        "chimalhuacan", "chalco", "ixtapaluca",
    ],
    "exclusions": [
        "cdmx", "ciudad de mexico", "monterrey", "guadalajara",
    ],
}

_P_PUE: dict = {
    "url_names": ["Puebla"],
    "aliases": ["puebla", "pue", "san andres cholula", "cuautlancingo"],
    "exclusions": ["cdmx", "ciudad de mexico", "monterrey", "guadalajara"],
}

_P_QRO: dict = {
    "url_names": ["Querétaro"],
    "aliases": ["queretaro", "qro", "el marques", "corregidora"],
    "exclusions": ["cdmx", "ciudad de mexico", "monterrey"],
}

# Map all user-input variants → their profile
_GEO_PROFILES: dict[str, dict] = {
    "cdmx":              _P_CDMX,
    "ciudad de mexico":  _P_CDMX,
    "ciudad de mx":      _P_CDMX,
    "df":                _P_CDMX,
    "distrito federal":  _P_CDMX,
    "monterrey":         _P_MTY,
    "mty":               _P_MTY,
    "nuevo leon":        _P_MTY,
    "nl":                _P_MTY,
    "guadalajara":       _P_GDL,
    "gdl":               _P_GDL,
    "jalisco":           _P_GDL,
    "jal":               _P_GDL,
    "edomex":            _P_EDOMEX,
    "estado de mexico":  _P_EDOMEX,
    "toluca":            _P_EDOMEX,
    "puebla":            _P_PUE,
    "pue":               _P_PUE,
    "queretaro":         _P_QRO,
    "qro":               _P_QRO,
}

# Keep _GEO_ALIASES for URL builder (_expand_ubicacion) — maps input → display names
_GEO_ALIASES: dict[str, list[str]] = {
    k: v["url_names"] for k, v in _GEO_PROFILES.items()
}
_GEO_ALIASES.update({
    "slp":    ["San Luis Potosí"],
    "merida": ["Mérida"],
    "yuc":    ["Mérida", "Yucatán"],
    "leon":   ["León"],
    "gto":    ["León", "Guanajuato"],
    "bajio":  ["León", "Guanajuato"],
})


def _expand_ubicacion(ubicacion: str) -> list[str]:
    """Expand a (possibly comma-separated) location string to URL-ready display names."""
    parts = [p.strip() for p in ubicacion.split(',') if p.strip()]
    urls: list[str] = []
    for part in parts:
        key = _normalize_text(part)
        urls.extend(_GEO_ALIASES.get(key, [part])[:2])
    return list(dict.fromkeys(urls))[:4]


# ── Salary filter ──────────────────────────────────────────────────────────────

_SALARY_RE = _re.compile(r'(?:\$\s*|MXN\s*|USD\s*)?(\d[\d,\.]{1,9})', _re.I)
_SALARY_MIL_RE = _re.compile(r'(\d+(?:\.\d+)?)\s*mil\b', _re.I)


def _passes_salary_filter(reqs: str, min_salary: int | None) -> bool:
    """False solo cuando salario mencionado y TODOS los valores encontrados son < mínimo."""
    if not min_salary:
        return True
    found_any = False

    for raw in _SALARY_MIL_RE.findall(reqs):
        try:
            val = int(float(raw) * 1000)
            if 3_000 <= val <= 300_000:
                found_any = True
                if val >= min_salary:
                    return True
        except ValueError:
            pass

    for raw in _SALARY_RE.findall(reqs):
        try:
            val = int(raw.replace(',', '').split('.')[0])
            if 3_000 <= val <= 300_000:
                found_any = True
                if val >= min_salary:
                    return True
        except ValueError:
            pass

    return not found_any


_REMOTE_KEYWORDS = {"remoto", "home office", "teletrabajo", "remote", "trabajo remoto", "desde casa"}
_ONSITE_KEYWORDS = {"presencial", "en sitio", "on-site", "oficina"}

# ── URL builders ──────────────────────────────────────────────────────────────

def _slug(text: str) -> str:
    nfd = unicodedata.normalize('NFD', text.lower().strip())
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn').replace(' ', '-')


def _computrabajo_urls(term: str, filtros: dict) -> list[str]:
    modalidad = filtros.get("modalidad", "any")
    ubicacion = filtros.get("ubicacion", "").strip()
    pais      = filtros.get("pais", "Mexico")

    if pais == "Internacional":
        bases = list(dict.fromkeys(_CT_DOMINIOS.values()))[:3]
    else:
        bases = [_CT_DOMINIOS.get(pais, _CT_DOMINIOS["Mexico"])]

    ubicaciones = _expand_ubicacion(ubicacion) if ubicacion else [""]
    urls: list[str] = []
    for base in bases:
        t = _slug(term)
        if modalidad == "remoto":
            urls.append(f"{base}/trabajo-de-{t}-trabajo-remoto")
            urls.append(f"{base}/trabajo-de-{t}-home-office")
        elif modalidad == "hibrido":
            urls.append(f"{base}/trabajo-de-{t}-hibrido")
        else:
            for ub in ubicaciones:
                if ub:
                    urls.append(f"{base}/trabajo-de-{t}-en-{_slug(ub)}")
                else:
                    urls.append(f"{base}/trabajo-de-{t}")
    return list(dict.fromkeys(urls))


def _occ_urls(term: str, filtros: dict) -> list[str]:
    if filtros.get("pais", "Mexico") not in ("Mexico", "Internacional"):
        return []
    modalidad = filtros.get("modalidad", "any")
    ubicacion = filtros.get("ubicacion", "").strip()
    t = _slug(term)
    if modalidad == "remoto":
        return [f"https://www.occ.com.mx/empleos/de-{t}/en-home-office/"]
    if ubicacion and modalidad != "hibrido":
        variants = _expand_ubicacion(ubicacion)
        return [f"https://www.occ.com.mx/empleos/de-{t}/en-{_slug(ub)}/" for ub in variants]
    return [f"https://www.occ.com.mx/empleos/de-{t}/"]


# ── Text / geo filters ─────────────────────────────────────────────────────────

def _passes_text_filter(titulo: str, reqs: str, filtros: dict) -> bool:
    modalidad = filtros.get("modalidad", "any")
    if modalidad == "any":
        return True
    text = f"{titulo} {reqs}".lower()
    is_remote = any(kw in text for kw in _REMOTE_KEYWORDS)
    if modalidad == "presencial" and is_remote:
        return False
    if modalidad == "remoto" and any(kw in text for kw in _ONSITE_KEYWORDS) and not is_remote:
        return False
    return True


def _passes_geo_filter(titulo: str, reqs: str, filtros: dict, jld_location: str = "") -> bool:
    """
    True  → vacante pasa el filtro geográfico.
    Soporta ubicaciones múltiples separadas por coma (ej. "CDMX, Estado de México").
    Con múltiples zonas: acepta si la vacante coincide con CUALQUIERA de ellas.
    """
    ubicacion = filtros.get("ubicacion", "").strip()
    if not ubicacion:
        return True
    if filtros.get("modalidad", "any") == "remoto":
        return True

    # Texto a analizar: JSON-LD location (más preciso) o título + inicio de reqs
    if jld_location:
        search_text = _normalize_text(jld_location)
    else:
        search_text = _normalize_text(f"{titulo} {reqs[:600]}")

    # Soporte para ubicaciones múltiples separadas por coma
    parts = [p.strip() for p in ubicacion.split(',') if p.strip()]

    for part in parts:
        key     = _normalize_text(part)
        profile = _GEO_PROFILES.get(key)

        if profile:
            # Exclusiones solo aplican si ninguna otra parte del filtro las acepta
            excluded = any(_word_match(excl, search_text) for excl in profile["exclusions"])
            if excluded:
                # Antes de rechazar, verificar si otro perfil hermano acepta esta vacante
                sibling_accepts = False
                for other_part in parts:
                    if other_part == part:
                        continue
                    other_profile = _GEO_PROFILES.get(_normalize_text(other_part))
                    if other_profile and any(_word_match(a, search_text) for a in other_profile["aliases"]):
                        sibling_accepts = True
                        break
                if sibling_accepts:
                    return True
                # Exclusión definitiva solo si todas las partes la rechazan
                continue
            # Alias positivo o sin señal (benefit of doubt)
            if any(_word_match(a, search_text) for a in profile["aliases"]):
                return True
            # Sin señal: sigue revisando otras partes, pero marca como posible aceptación
        else:
            # Perfil desconocido: coincidencia literal
            if _word_match(key, search_text):
                return True

    # Sin alias positivo en ninguna parte → benefit of doubt si hubo perfiles reconocidos
    if any(_GEO_PROFILES.get(_normalize_text(p)) for p in parts):
        return True
    return False


# ── API helper ────────────────────────────────────────────────────────────────

def _post_vacante(titulo: str, empresa: str, enlace: str, reqs: str, compat: str = "Nula") -> tuple[bool, str]:
    """POST vacancy to API. `compat` pre-set → API skips Groq re-evaluation (token-free)."""
    payload = json.dumps({
        "titulo":          titulo[:200],
        "empresa":         (empresa or "Desconocida")[:100],
        "enlace":          enlace,
        "requerimientos":  (reqs or "")[:5000],
        "compatibilidad":  compat,
        "user_id":         _SCRAPER_USER_ID,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/vacantes",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('BOT_MASTER_TOKEN', 'BOT_MASTER_TOKEN_2026')}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read().decode())
            return True, result.get("compatibilidad", compat)
    except urllib.error.HTTPError as e:
        if e.code == 409:
            return False, ""
        print(f"  [API] HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:200]}")
        return False, ""
    except Exception as ex:
        print(f"  [API] Error: {ex}")
        return False, ""


def _eval_and_post(titulo: str, empresa: str, enlace: str, reqs: str) -> tuple[bool, str]:
    """Evaluate compatibility locally, filter by min threshold, post if it passes.
    Pre-sets compat in payload → API never calls Groq (zero double-evaluation tokens).
    """
    compat = evaluar_compatibilidad_rapida(reqs, _SCRAPER_USER_ID) if reqs.strip() else "Nula"
    if _COMPAT_ORDER.get(compat, 0) < _COMPAT_ORDER.get(_SCRAPER_MIN_COMPAT, 0):
        print(f"  [Skip] Compat {compat} < {_SCRAPER_MIN_COMPAT}: {titulo[:42]}")
        return False, compat
    return _post_vacante(titulo, empresa, enlace, reqs, compat)


# ── HTTP helper (sin Playwright) ──────────────────────────────────────────────

_HTTP_HEADERS = {
    "User-Agent": _USER_AGENTS[0],
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
}


def _http_get(url: str, as_json=False, timeout=15):
    req = urllib.request.Request(url, headers=_HTTP_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", errors="replace")
    return json.loads(raw) if as_json else raw


def _strip_html(html: str) -> str:
    class _S(_HTMLParser):
        def __init__(self): super().__init__(); self.parts = []
        def handle_data(self, d): self.parts.append(d)
    p = _S(); p.feed(html); return " ".join(p.parts)


# ── Anti-bot helpers ──────────────────────────────────────────────────────────

def _sleep(a=1.0, b=2.5):
    time.sleep(random.uniform(a, b))


def _incr(counter: list) -> int:
    """Thread-safe counter increment; returns new value."""
    with _counter_lock:
        counter[0] += 1
        return counter[0]


def _scroll(page: Page, steps=4):
    for _ in range(steps):
        page.evaluate("window.scrollBy(0, window.innerHeight * 0.7)")
        _sleep(0.4, 0.8)


def _is_blocked(page: Page) -> bool:
    """Detecta páginas de CAPTCHA / bloqueo / login wall."""
    try:
        signals = page.title().lower() + " " + page.url.lower()
        blockers = [
            "captcha", "are you a robot", "access denied", "403",
            "cloudflare", "security check", "robot check",
            "verify you are human", "unusual traffic", "iniciar sesión",
            "sign in to continue", "authwall",
        ]
        return any(b in signals for b in blockers)
    except Exception:
        return False


def _jsonld_job_from_page(page: Page) -> tuple[str, str, str, str]:
    """
    Extrae (titulo, empresa, reqs, location) de JSON-LD JobPosting.
    `location` es el string de addressLocality + addressRegion del schema JobPosting.
    """
    try:
        scripts = page.query_selector_all('script[type="application/ld+json"]')
        for s in scripts:
            try:
                data = json.loads(s.inner_text() or "{}")
            except json.JSONDecodeError:
                continue
            items = data if isinstance(data, list) else data.get("@graph", [data])
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("@type") not in ("JobPosting", "jobPosting"):
                    continue

                titulo  = str(item.get("title", "")).strip()
                org     = item.get("hiringOrganization") or {}
                empresa = str(org.get("name", "") if isinstance(org, dict) else "").strip()
                desc    = str(item.get("description", "")).strip()
                reqs    = _strip_html(desc)[:3000]

                # Extraer ubicación desde jobLocation → address
                location = ""
                job_loc = item.get("jobLocation") or {}
                if isinstance(job_loc, list):
                    job_loc = job_loc[0] if job_loc else {}
                if isinstance(job_loc, dict):
                    address = job_loc.get("address") or {}
                    if isinstance(address, str):
                        location = address
                    elif isinstance(address, dict):
                        parts = [
                            str(address.get("addressLocality", "") or ""),
                            str(address.get("addressRegion", "")   or ""),
                            str(address.get("addressCountry", "")  or ""),
                        ]
                        location = ", ".join(p for p in parts if p.strip())
                    # También revisar el nombre directo del lugar
                    if not location:
                        location = str(job_loc.get("name", "") or "")

                if titulo:
                    return titulo, empresa, reqs, location
    except Exception:
        pass
    return "", "", "", ""


def _resolve_href(href: str, base_domain: str) -> str:
    if not href:
        return ""
    if href.startswith("http"):
        return href.split("?")[0].split("#")[0]
    if href.startswith("/"):
        return base_domain + href.split("?")[0].split("#")[0]
    return href


# ── Scrapers ──────────────────────────────────────────────────────────────────

def scrape_computrabajo(page: Page, term: str, counter: list, limite: int | None, filtros: dict) -> int:
    count = 0
    urls  = _computrabajo_urls(term, filtros)
    min_salary = filtros.get("min_salary")
    CT_BASE = _CT_DOMINIOS.get(filtros.get("pais", "Mexico"), _CT_DOMINIOS["Mexico"])

    for url in urls:
        if limite is not None and counter[0] >= limite:
            break
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=22000)
            _sleep(1.5, 2.5)

            if _is_blocked(page):
                print(f"  [CT] Bloqueado en {url[:60]}")
                continue

            _scroll(page)

            cards = page.query_selector_all("article.box_offer")[:MAX_PER_TERM]
            if not cards:
                print(f"  [CT] Sin tarjetas en {url[:60]}")
                continue

            for card in cards:
                if limite is not None and counter[0] >= limite:
                    break
                try:
                    titulo_el = card.query_selector("h2 a, h3 a, a.js-o-link")
                    if not titulo_el:
                        continue
                    titulo = titulo_el.inner_text().strip()
                    href   = titulo_el.get_attribute("href") or ""
                    enlace = _resolve_href(href, CT_BASE)
                    if not enlace:
                        continue

                    emp_el  = card.query_selector("p.dcolor, a.dcolor, span[class*='company']")
                    empresa = emp_el.inner_text().strip() if emp_el else ""

                    reqs = ""
                    jld_location = ""
                    if enlace:
                        detail = None
                        try:
                            detail = page.context.new_page()
                            detail.goto(enlace, wait_until="domcontentloaded", timeout=15000)
                            _sleep(0.8, 1.5)

                            t2, e2, r2, loc2 = _jsonld_job_from_page(detail)
                            jld_location = loc2
                            if r2:
                                reqs = r2
                                if not empresa and e2:
                                    empresa = e2
                            else:
                                req_el = detail.query_selector(
                                    "div.description_offer, div[class*='description_offer'], "
                                    "section[class*='description'], div[id*='description']"
                                )
                                if req_el:
                                    reqs = req_el.inner_text()[:3000]
                        except Exception as ex:
                            print(f"    [detail] {ex}")
                        finally:
                            if detail:
                                try: detail.close()
                                except Exception: pass
                            _sleep(0.5, 1.0)

                    if len(reqs.strip()) < 50:
                        print(f"  [Skip] Sin reqs: {titulo[:45]}")
                        continue
                    if not _passes_text_filter(titulo, reqs, filtros):
                        continue
                    if not _passes_salary_filter(reqs, min_salary):
                        print(f"  [Filtro] Salario: {titulo[:45]}")
                        continue
                    if not _passes_geo_filter(titulo, reqs, filtros, jld_location):
                        print(f"  [Filtro] Geo: {titulo[:45]}")
                        continue

                    insertada, compat = _eval_and_post(titulo, empresa, enlace, reqs)
                    if insertada:
                        n = _incr(counter)
                        count += 1
                        print(f"  + [{n}] {titulo[:50]} | {(empresa or 'Desconocida')[:22]} | {compat}  [CT]")
                except Exception as ex:
                    print(f"  [CT-card] {ex}")
            _sleep(2, 4)
        except Exception as ex:
            print(f"  [computrabajo] {term} @ {url[:60]}: {ex}")
    return count


def scrape_occ(page: Page, term: str, counter: list, limite: int | None, filtros: dict) -> int:
    count = 0
    urls  = _occ_urls(term, filtros)
    if not urls:
        return 0
    min_salary = filtros.get("min_salary")

    for url in urls:
        if limite is not None and counter[0] >= limite:
            break
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=22000)
            # OCC usa React SSR — esperar hidratación de tarjetas
            try:
                page.wait_for_selector(
                    "a[data-testid='job-card-title-link'], div.card-job-offer",
                    timeout=8000,
                )
            except Exception:
                pass
            _sleep(1.0, 2.0)

            if _is_blocked(page):
                print(f"  [OCC] Bloqueado en {url[:60]}")
                continue

            _scroll(page)

            links = page.query_selector_all(
                "a[data-testid='job-card-title-link'], div.card-job-offer a[href*='/vacante/']"
            )[:MAX_PER_TERM]

            for link in links:
                if limite is not None and counter[0] >= limite:
                    break
                try:
                    titulo = link.inner_text().strip()
                    if not titulo or len(titulo) < 4:
                        continue
                    href   = link.get_attribute("href") or ""
                    enlace = ("https://www.occ.com.mx" + href) if href.startswith("/") else href

                    empresa = ""
                    try:
                        parent    = link.evaluate_handle("el => el.closest('article, div[class*=card]')")
                        parent_el = parent.as_element()
                        if parent_el:
                            emp_el = parent_el.query_selector(
                                "[data-testid='company-name'], p.company, span[class*='company']"
                            )
                            if emp_el:
                                empresa = emp_el.inner_text().strip()
                    except Exception:
                        pass

                    reqs = ""
                    jld_location = ""
                    if enlace:
                        detail = None
                        try:
                            detail = page.context.new_page()
                            detail.goto(enlace, wait_until="domcontentloaded", timeout=15000)
                            _sleep(0.8, 1.5)
                            _, e2, r2, loc2 = _jsonld_job_from_page(detail)
                            jld_location = loc2
                            if r2:
                                reqs = r2
                                if not empresa and e2:
                                    empresa = e2
                            else:
                                req_el = detail.query_selector(
                                    "div.job-description, section[class*='description'], "
                                    "div[data-cy='jobDescription'], div[class*='description']"
                                )
                                if req_el:
                                    reqs = req_el.inner_text()[:3000]
                        except Exception:
                            pass
                        finally:
                            if detail:
                                try: detail.close()
                                except Exception: pass

                    if len(reqs.strip()) < 50:
                        print(f"  [Skip] Sin reqs: {titulo[:45]}")
                        continue
                    if not _passes_text_filter(titulo, reqs, filtros):
                        continue
                    if not _passes_salary_filter(reqs, min_salary):
                        print(f"  [Filtro] Salario: {titulo[:45]}")
                        continue
                    if not _passes_geo_filter(titulo, reqs, filtros, jld_location):
                        print(f"  [Filtro] Geo: {titulo[:45]}")
                        continue

                    insertada, compat = _eval_and_post(titulo, empresa, enlace, reqs)
                    if insertada:
                        n = _incr(counter)
                        count += 1
                        print(f"  + [{n}] {titulo[:50]} | {(empresa or 'Desconocida')[:22]} | {compat}  [OCC]")
                except Exception as ex:
                    print(f"  [OCC-card] {ex}")
            _sleep(2, 3)
        except Exception as ex:
            print(f"  [OCC] {term} @ {url[:60]}: {ex}")
    return count


def scrape_bumeran(page: Page, term: str, counter: list, limite: int | None, filtros: dict) -> int:
    """Scrape Bumeran MX vía Playwright (JS-rendered)."""
    pais = filtros.get("pais", "Mexico")
    if pais not in ("Mexico", "Internacional"):
        return 0
    if limite is not None and counter[0] >= limite:
        return 0

    modalidad = filtros.get("modalidad", "any")
    ubicacion = filtros.get("ubicacion", "").strip()
    t         = _slug(term)

    if modalidad == "remoto":
        url = f"https://www.bumeran.com.mx/empleos-trabajo-desde-casa-{t}.html"
    elif ubicacion:
        url = f"https://www.bumeran.com.mx/empleos-{t}-en-{_slug(ubicacion)}.html"
    else:
        url = f"https://www.bumeran.com.mx/empleos-{t}.html"

    count = 0
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=22000)
        # Esperar a que React renderice las tarjetas
        try:
            page.wait_for_selector("a[href*='/empleo/']", timeout=8000)
        except Exception:
            pass
        _sleep(1.5, 2.5)

        if _is_blocked(page):
            print(f"  [Bumeran] Bloqueado")
            return 0

        _scroll(page)

        links = page.query_selector_all("a[href*='/empleo/']")[:MAX_PER_TERM * 3]
        seen  = set()
        processed = 0
        for link in links:
            if limite is not None and counter[0] >= limite:
                break
            if processed >= MAX_PER_TERM:
                break
            try:
                href   = link.get_attribute("href") or ""
                enlace = ("https://www.bumeran.com.mx" + href) if href.startswith("/") else href
                if enlace in seen or not enlace:
                    continue

                titulo = link.inner_text().strip()[:200]
                if not titulo or len(titulo) < 6:
                    continue
                # Excluir links de navegación genérica
                skip_words = ["ver más", "ver todos", "inicio", "búsqueda", "empresa", "candidatos"]
                if any(sw in titulo.lower() for sw in skip_words):
                    continue

                seen.add(enlace)
                processed += 1

                empresa = "Desconocida"
                reqs = ""
                jld_location = ""
                detail = None
                try:
                    detail = page.context.new_page()
                    detail.goto(enlace, wait_until="domcontentloaded", timeout=15000)
                    _sleep(0.8, 1.5)
                    _, e2, r2, loc2 = _jsonld_job_from_page(detail)
                    jld_location = loc2
                    if r2:
                        reqs = r2
                        if e2:
                            empresa = e2
                    else:
                        req_el = detail.query_selector(
                            "div[class*='description'], section[class*='detail'], div[id*='description']"
                        )
                        if req_el:
                            reqs = req_el.inner_text()[:3000]
                        emp_el = detail.query_selector("a[href*='/empresa/'], span[class*='company']")
                        if emp_el:
                            empresa = emp_el.inner_text().strip()
                except Exception:
                    pass
                finally:
                    if detail:
                        try: detail.close()
                        except Exception: pass
                    _sleep(0.5, 1.0)

                if len(reqs.strip()) < 50:
                    continue
                if not _passes_text_filter(titulo, reqs, filtros):
                    continue
                if not _passes_salary_filter(reqs, filtros.get("min_salary")):
                    print(f"  [Filtro] Salario: {titulo[:45]}")
                    continue
                if not _passes_geo_filter(titulo, reqs, filtros, jld_location):
                    print(f"  [Filtro] Geo: {titulo[:45]}")
                    continue

                insertada, compat = _eval_and_post(titulo, empresa, enlace, reqs)
                if insertada:
                    n = _incr(counter)
                    count += 1
                    print(f"  + [{n}] {titulo[:50]} | {empresa[:22]} | {compat}  [Bumeran]")
            except Exception as ex:
                print(f"  [Bumeran-card] {ex}")
        _sleep(2, 3)
    except Exception as ex:
        print(f"  [Bumeran] {term}: {ex}")
    return count


# ── Indeed RSS — DEPRECADO (404 desde 2024) ────────────────────────────────────

def scrape_indeed_rss(term: str, counter: list, limite: int | None, filtros: dict) -> int:
    """Indeed RSS endpoint retorna 404 desde 2024 — desactivado."""
    print(f"  [Indeed] Omitido (RSS deprecado)")
    return 0


# ── Remotive (API JSON — solo remoto / tech global) ────────────────────────────

def scrape_remotive(term: str, counter: list, limite: int | None, filtros: dict) -> int:
    if filtros.get("modalidad", "any") not in ("remoto", "any"):
        return 0
    if limite is not None and counter[0] >= limite:
        return 0
    count = 0
    try:
        q   = urllib.parse.quote_plus(term)
        url = f"https://remotive.com/api/remote-jobs?search={q}&limit=10"
        data = _http_get(url, as_json=True)
        jobs = data.get("jobs", [])[:MAX_PER_TERM]
        for job in jobs:
            if limite is not None and counter[0] >= limite:
                break
            titulo  = (job.get("title") or "").strip()
            empresa = (job.get("company_name") or "Desconocida").strip()
            enlace  = (job.get("url") or "").strip()
            reqs    = _strip_html(job.get("description") or "")[:3000]
            if not titulo or len(reqs.strip()) < 50:
                continue
            if not _passes_salary_filter(reqs, filtros.get("min_salary")):
                continue
            insertada, compat = _eval_and_post(titulo, empresa, enlace, reqs)
            if insertada:
                n = _incr(counter); count += 1
                print(f"  + [{n}] {titulo[:50]} | {empresa[:22]} | {compat}  [Remotive]")
        _sleep(1.0, 2.0)
    except Exception as ex:
        print(f"  [Remotive] {term}: {ex}")
    return count


# ── GetOnBrd (API JSON — tech Latam) ──────────────────────────────────────────

def scrape_getonbrd(term: str, counter: list, limite: int | None, filtros: dict) -> int:
    if limite is not None and counter[0] >= limite:
        return 0
    count = 0
    try:
        q   = urllib.parse.quote_plus(term)
        url = f"https://www.getonbrd.com/api/v0/search/jobs?query={q}&per_page=10"
        data = _http_get(url, as_json=True)
        jobs = (data.get("data") or [])[:MAX_PER_TERM]
        for job in jobs:
            if limite is not None and counter[0] >= limite:
                break
            try:
                attr    = job.get("attributes", {})
                titulo  = (attr.get("title") or "").strip()
                empresa = (attr.get("company", {}) or {}).get("name", "Desconocida")
                enlace  = (attr.get("application_link") or
                           f"https://www.getonbrd.com/jobs/{job.get('id','')}").strip()
                reqs    = _strip_html(attr.get("description") or "")[:3000]
                if not titulo or len(reqs.strip()) < 50:
                    continue
                if not _passes_text_filter(titulo, reqs, filtros):
                    continue
                if not _passes_salary_filter(reqs, filtros.get("min_salary")):
                    continue
                if not _passes_geo_filter(titulo, reqs, filtros):
                    continue
                insertada, compat = _eval_and_post(titulo, empresa, enlace, reqs)
                if insertada:
                    n = _incr(counter); count += 1
                    print(f"  + [{n}] {titulo[:50]} | {empresa[:22]} | {compat}  [GetOnBrd]")
            except Exception as ex:
                print(f"  [GetOnBrd-item] {ex}")
        _sleep(1.0, 2.0)
    except Exception as ex:
        print(f"  [GetOnBrd] {term}: {ex}")
    return count


# ── LinkedIn (Playwright — bloqueo frecuente en headless) ─────────────────────

def _linkedin_url(term: str, filtros: dict) -> str:
    q   = urllib.parse.quote_plus(term)
    ub  = filtros.get("ubicacion", "").strip()
    if ub:
        loc = urllib.parse.quote_plus(_expand_ubicacion(ub)[0] if _expand_ubicacion(ub) else ub)
    else:
        loc = urllib.parse.quote_plus({"Mexico": "Mexico", "España": "Spain",
                                       "Argentina": "Argentina", "Colombia": "Colombia",
                                       "Chile": "Chile"}.get(filtros.get("pais","Mexico"), "Mexico"))
    return f"https://www.linkedin.com/jobs/search/?keywords={q}&location={loc}&f_TP=1&sortBy=DD"


def scrape_linkedin(page: Page, term: str, counter: list, limite: int | None, filtros: dict) -> int:
    if limite is not None and counter[0] >= limite:
        return 0

    url        = _linkedin_url(term, filtros)
    min_salary = filtros.get("min_salary")
    count      = 0
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        _sleep(2.5, 4.0)

        if _is_blocked(page):
            print(f"  [LinkedIn] Bloqueado / requiere login — saltando")
            return 0

        _scroll(page, steps=3)

        cards = page.query_selector_all(
            "div.base-card, div.job-search-card, li.jobs-search-results__list-item"
        )[:MAX_PER_TERM]

        for card in cards:
            if limite is not None and counter[0] >= limite:
                break
            try:
                title_el = card.query_selector(
                    "h3.base-search-card__title, h3.job-card-list__title, "
                    "span[class*='title'], a[class*='title']"
                )
                if not title_el:
                    continue
                titulo = title_el.inner_text().strip()

                company_el = card.query_selector(
                    "h4.base-search-card__subtitle, span.job-card-container__company-name, "
                    "a[class*='company']"
                )
                empresa = company_el.inner_text().strip() if company_el else "Desconocida"

                link_el = card.query_selector("a.base-card__full-link, a[data-tracking-control-name]")
                href    = link_el.get_attribute("href") if link_el else ""
                enlace  = href.split("?")[0] if href else ""

                reqs = ""
                jld_location = ""
                if enlace:
                    detail = None
                    try:
                        detail = page.context.new_page()
                        detail.goto(enlace, wait_until="domcontentloaded", timeout=20000)
                        _sleep(1.5, 3.0)
                        if _is_blocked(detail):
                            detail.close()
                            continue
                        # LinkedIn expone JSON-LD en algunas páginas de job
                        _, _, r_jld, loc_jld = _jsonld_job_from_page(detail)
                        jld_location = loc_jld
                        if r_jld:
                            reqs = r_jld
                        else:
                            req_el = detail.query_selector(
                                "div.description__text, div.show-more-less-html__markup, "
                                "div[class*='description-content'], section.description"
                            )
                            if req_el:
                                reqs = req_el.inner_text()[:3000]
                    except Exception:
                        pass
                    finally:
                        if detail:
                            try: detail.close()
                            except Exception: pass
                        _sleep(1.0, 2.0)

                if len(reqs.strip()) < 50:
                    continue
                if not _passes_text_filter(titulo, reqs, filtros):
                    continue
                if not _passes_salary_filter(reqs, min_salary):
                    continue
                if not _passes_geo_filter(titulo, reqs, filtros, jld_location):
                    print(f"  [Filtro] Geo: {titulo[:45]}")
                    continue

                insertada, compat = _eval_and_post(titulo, empresa, enlace, reqs)
                if insertada:
                    n = _incr(counter); count += 1
                    print(f"  + [{n}] {titulo[:50]} | {empresa[:22]} | {compat}  [LinkedIn]")
            except Exception as ex:
                print(f"  [LinkedIn-card] {ex}")
        _sleep(3, 5)
    except Exception as ex:
        print(f"  [LinkedIn] {term}: {ex}")
    return count


# ── Browser helpers ───────────────────────────────────────────────────────────

_BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-web-security",
    "--disable-gpu",
    "--no-first-run",
    "--disable-notifications",
    "--disable-features=VizDisplayCompositor",
    "--single-process",
]

_STEALTH_SCRIPT = """
    Object.defineProperty(navigator,'webdriver',{get:()=>undefined});
    Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});
    Object.defineProperty(navigator,'languages',{get:()=>['es-MX','es','en']});
    window.chrome = {runtime:{},loadTimes:()=>{},csi:()=>{}};
"""


def _run_term(term: str, counter: list, limite: int | None, filtros: dict, platforms: set) -> int:
    """Scrape one search term across all platforms in its own Playwright instance (thread worker)."""
    inserted = 0
    browser  = None
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=HEADLESS, args=_BROWSER_ARGS)
            ua = random.choice(_USER_AGENTS)
            ctx = browser.new_context(
                user_agent=ua,
                viewport={"width": random.choice([1280, 1366, 1440]), "height": 900},
                locale="es-MX",
                timezone_id="America/Mexico_City",
                extra_http_headers={"Accept-Language": "es-MX,es;q=0.9,en;q=0.8"},
            )
            ctx.add_init_script(_STEALTH_SCRIPT)
            page = ctx.new_page()

            def _at_limit() -> bool:
                with _counter_lock:
                    return limite is not None and counter[0] >= limite

            if "computrabajo" in platforms and not _at_limit():
                print(f"\n[Computrabajo] '{term}'")
                inserted += scrape_computrabajo(page, term, counter, limite, filtros)

            if "occ" in platforms and not _at_limit():
                print(f"\n[OCC] '{term}'")
                inserted += scrape_occ(page, term, counter, limite, filtros)

            if "bumeran" in platforms and not _at_limit():
                print(f"\n[Bumeran] '{term}'")
                inserted += scrape_bumeran(page, term, counter, limite, filtros)

            if "getonbrd" in platforms and not _at_limit():
                print(f"\n[GetOnBrd] '{term}'")
                inserted += scrape_getonbrd(term, counter, limite, filtros)

            if "remotive" in platforms and not _at_limit():
                print(f"\n[Remotive] '{term}'")
                inserted += scrape_remotive(term, counter, limite, filtros)

            if "linkedin" in platforms and not _at_limit():
                print(f"\n[LinkedIn] '{term}'")
                inserted += scrape_linkedin(page, term, counter, limite, filtros)

    except Exception as e:
        print(f"\n[ERROR worker '{term}'] {e}")
    finally:
        if browser:
            try: browser.close()
            except Exception: pass
    return inserted


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global _SCRAPER_USER_ID, _SCRAPER_MIN_COMPAT

    parser = argparse.ArgumentParser()
    parser.add_argument('--limit',   type=int,  default=None)
    parser.add_argument('--terms',   nargs='*', dest='named_terms')
    parser.add_argument('--filtros', type=str,  default='{}')
    parser.add_argument('--user-id',    type=str, default='default_user', dest='user_id')
    parser.add_argument('--min-compat', type=str, default='Baja',         dest='min_compat',
                        choices=['Alta', 'Media', 'Baja', 'Nula'])
    parser.add_argument('positional_terms', nargs='*')
    args = parser.parse_args()

    _SCRAPER_USER_ID    = args.user_id
    _SCRAPER_MIN_COMPAT = args.min_compat
    limite = args.limit
    terms  = args.named_terms or args.positional_terms or generar_terminos_busqueda()

    try:
        filtros = {**_FILTROS_DEFAULT, **json.loads(args.filtros)}
    except json.JSONDecodeError:
        print(f"[WARN] --filtros JSON inválido, usando defaults")
        filtros = dict(_FILTROS_DEFAULT)

    platforms = set(filtros.get("platforms") or _ALL_PLATFORMS)
    workers   = min(len(terms), MAX_WORKERS)

    print(f"[config] API: {API_BASE}")
    print(f"[config] Usuario: {_SCRAPER_USER_ID}")
    print(f"[config] Compatibilidad mínima: {_SCRAPER_MIN_COMPAT}")
    print(f"[config] Términos ({len(terms)}): {terms}")
    print(f"[config] Plataformas: {', '.join(sorted(platforms))}")
    print(f"[config] Trabajadores paralelos: {workers}")
    if limite:
        print(f"[config] Límite: {limite}")
    if filtros.get("min_salary"):
        print(f"[config] Salario mínimo: ${filtros['min_salary']:,} MXN")
    print(f"[config] Filtros: ubicacion={filtros['ubicacion']!r}  modalidad={filtros['modalidad']}  pais={filtros['pais']}")

    counter = [0]

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures: dict = {}
        for term in terms:
            with _counter_lock:
                at_limit = limite is not None and counter[0] >= limite
            if at_limit:
                print(f"\n[límite] Alcanzado {limite}. No se lanzan más trabajadores.")
                break
            fut = executor.submit(_run_term, term, counter, limite, filtros, platforms)
            futures[fut] = term

        for fut in as_completed(futures):
            term = futures[fut]
            try:
                n = fut.result()
                print(f"\n[✓] '{term}' → {n} vacantes insertadas")
            except Exception as e:
                print(f"\n[✗] '{term}' → error: {e}")

    print(f"\n{'='*50}")
    print(f"Total enviadas a la API: {counter[0]} vacantes nuevas")


if __name__ == "__main__":
    main()
