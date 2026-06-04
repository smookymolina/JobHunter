"""
Browser Agent — scraping con Playwright (headed, anti-bot evasion).
Cada vacante encontrada se envía vía POST al API REST (localhost:8000/vacantes).
El agente NO escribe directamente a SQLite.

Uso:
    python browser_agent.py
    python browser_agent.py --limit 5
    python browser_agent.py --limit 5 --terms "IoT Developer" "Backend Python"
    python browser_agent.py --limit 10 --filtros '{"ubicacion":"Ciudad de México","modalidad":"remoto","pais":"Mexico"}'
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import argparse
import json
import os
import time
import random
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as _ET
from html.parser import HTMLParser as _HTMLParser

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from playwright.sync_api import sync_playwright, Page
from gemini_engine import generar_terminos_busqueda

# ── Config ────────────────────────────────────────────────────────────────────

API_BASE     = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
SEARCH_TERMS: list[str] = generar_terminos_busqueda()
MAX_PER_TERM = 8
HEADLESS     = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() != "false"

# Dominios Computrabajo por país
_CT_DOMINIOS: dict[str, str] = {
    "Mexico":        "https://www.computrabajo.com.mx",
    "España":        "https://www.computrabajo.es",
    "Argentina":     "https://www.computrabajo.com.ar",
    "Colombia":      "https://www.computrabajo.com.co",
    "Chile":         "https://www.computrabajo.cl",
    "Internacional": "https://www.computrabajo.com.mx",  # base; se itera multi-país
}

_FILTROS_DEFAULT: dict = {"ubicacion": "", "modalidad": "any", "pais": "Mexico"}

# Palabras clave que indican trabajo remoto en texto de vacante
_REMOTE_KEYWORDS = {"remoto", "home office", "teletrabajo", "remote", "trabajo remoto", "desde casa"}
# Palabras clave que indican trabajo presencial
_ONSITE_KEYWORDS = {"presencial", "en sitio", "on-site", "oficina"}

# ── URL builders ──────────────────────────────────────────────────────────────

def _slug(text: str) -> str:
    return text.lower().strip().replace(' ', '-')


def _computrabajo_urls(term: str, filtros: dict) -> list[str]:
    """Genera lista de URLs de Computrabajo según filtros."""
    modalidad = filtros.get("modalidad", "any")
    ubicacion = filtros.get("ubicacion", "").strip()
    pais      = filtros.get("pais", "Mexico")

    if pais == "Internacional":
        bases = list(dict.fromkeys(_CT_DOMINIOS.values()))[:3]  # MX+ES+AR, cap para no saturar
    else:
        bases = [_CT_DOMINIOS.get(pais, _CT_DOMINIOS["Mexico"])]

    urls = []
    for base in bases:
        t = _slug(term)
        if modalidad == "remoto":
            urls.append(f"{base}/trabajo-de-{t}-trabajo-remoto")
            urls.append(f"{base}/trabajo-de-{t}-home-office")
        elif modalidad == "hibrido":
            urls.append(f"{base}/trabajo-de-{t}-hibrido")
        elif ubicacion:
            urls.append(f"{base}/trabajo-de-{t}-en-{_slug(ubicacion)}")
        else:
            urls.append(f"{base}/trabajo-de-{t}")
    return urls


def _occ_url(term: str, filtros: dict) -> str | None:
    """Genera URL de OCC según filtros. OCC es solo México."""
    if filtros.get("pais", "Mexico") not in ("Mexico", "Internacional"):
        return None

    modalidad = filtros.get("modalidad", "any")
    ubicacion = filtros.get("ubicacion", "").strip()
    t = _slug(term)

    if modalidad == "remoto":
        return f"https://www.occ.com.mx/empleos/de-{t}/en-home-office/"
    # OCC no tiene ruta /en-hibrido/ — usar búsqueda base con filtro de texto
    if ubicacion and modalidad != "hibrido":
        return f"https://www.occ.com.mx/empleos/de-{t}/en-{_slug(ubicacion)}/"
    return f"https://www.occ.com.mx/empleos/de-{t}/"


# ── Text filter ───────────────────────────────────────────────────────────────

def _passes_text_filter(titulo: str, reqs: str, filtros: dict) -> bool:
    """Filtro secundario sobre el texto de la vacante para coherencia con modalidad."""
    modalidad = filtros.get("modalidad", "any")
    if modalidad == "any":
        return True

    text = f"{titulo} {reqs}".lower()
    is_remote = any(kw in text for kw in _REMOTE_KEYWORDS)

    if modalidad == "presencial" and is_remote:
        return False   # quiere presencial pero es remoto
    if modalidad == "remoto" and any(kw in text for kw in _ONSITE_KEYWORDS) and not is_remote:
        return False   # quiere remoto pero dice presencial
    return True


# ── API helper ────────────────────────────────────────────────────────────────

def _post_vacante(titulo: str, empresa: str, enlace: str, reqs: str) -> tuple[bool, str]:
    payload = json.dumps({
        "titulo":         titulo[:200],
        "empresa":        (empresa or "Desconocida")[:100],
        "enlace":         enlace,
        "requerimientos": (reqs or "")[:5000],
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/vacantes",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read().decode())
            return True, result.get("compatibilidad", "Nula")
    except urllib.error.HTTPError as e:
        if e.code == 409:
            return False, ""
        print(f"  [API] HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:200]}")
        return False, ""
    except Exception as ex:
        print(f"  [API] Error: {ex}")
        return False, ""


# ── HTTP helper (sin Playwright) ─────────────────────────────────────────────

_HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
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

def _scroll(page: Page, steps=4):
    for _ in range(steps):
        page.evaluate("window.scrollBy(0, window.innerHeight * 0.7)")
        _sleep(0.4, 0.8)


# ── Scrapers ──────────────────────────────────────────────────────────────────

def scrape_computrabajo(page: Page, term: str, counter: list, limite: int | None, filtros: dict) -> int:
    count = 0
    urls = _computrabajo_urls(term, filtros)

    for url in urls:
        if limite is not None and counter[0] >= limite:
            break
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            _sleep(1.5, 2.5)
            _scroll(page)

            cards = page.query_selector_all("article.box_offer")[:MAX_PER_TERM]
            for card in cards:
                if limite is not None and counter[0] >= limite:
                    break
                try:
                    titulo_el = card.query_selector("h2 a, h3 a")
                    if not titulo_el:
                        continue
                    titulo = titulo_el.inner_text().strip()
                    href   = titulo_el.get_attribute("href") or ""
                    enlace = ("https://www.computrabajo.com.mx" + href) if href.startswith("/") else href

                    emp_el  = card.query_selector("p.fs16, p.dcolor, a.dcolor")
                    empresa = emp_el.inner_text().strip() if emp_el else ""

                    reqs = ""
                    if enlace:
                        try:
                            detail = page.context.new_page()
                            detail.goto(enlace, wait_until="domcontentloaded", timeout=15000)
                            _sleep(0.8, 1.5)

                            if not empresa:
                                jld_raw = detail.evaluate("""
                                    () => {
                                        const s = document.querySelector('script[type="application/ld+json"]');
                                        return s ? s.textContent : '';
                                    }
                                """)
                                if jld_raw:
                                    try:
                                        jld = json.loads(jld_raw)
                                        items = jld if isinstance(jld, list) else [jld]
                                        for item in items:
                                            if item.get("@type") == "JobPosting":
                                                h = item.get("hiringOrganization", {})
                                                empresa = h.get("name") if isinstance(h, dict) else ""
                                    except Exception:
                                        pass

                            req_el = detail.query_selector(
                                "div[div-link='oferta'], section.description, div.job-description"
                            )
                            if req_el:
                                reqs = req_el.inner_text()[:3000]
                            detail.close()
                            _sleep(0.5, 1.0)
                        except Exception as ex:
                            print(f"    [detail] {ex}")

                    if len(reqs.strip()) < 50:
                        print(f"  [Skip] Sin reqs: {titulo[:45]}")
                        continue

                    if not _passes_text_filter(titulo, reqs, filtros):
                        print(f"  [Filtro] Excluido por modalidad: {titulo[:45]}")
                        continue

                    insertada, compat = _post_vacante(titulo, empresa, enlace, reqs)
                    if insertada:
                        counter[0] += 1
                        count += 1
                        print(f"  + [{counter[0]}] {titulo[:50]} | {(empresa or 'Desconocida')[:22]} | {compat}")
                except Exception as ex:
                    print(f"  [card] {ex}")
            _sleep(2, 4)
        except Exception as ex:
            print(f"  [computrabajo] {term} @ {url[:60]}: {ex}")
    return count


def scrape_occ(page: Page, term: str, counter: list, limite: int | None, filtros: dict) -> int:
    count = 0
    url = _occ_url(term, filtros)
    if url is None:
        return 0

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        _sleep(1.5, 2.5)
        _scroll(page)

        links = page.query_selector_all("a[data-testid='job-card-title-link']")[:MAX_PER_TERM]
        for link in links:
            if limite is not None and counter[0] >= limite:
                break
            try:
                titulo = link.inner_text().strip()
                href   = link.get_attribute("href") or ""
                enlace = ("https://www.occ.com.mx" + href) if href.startswith("/") else href

                empresa = ""
                parent  = link.evaluate_handle("el => el.closest('article, div[data-testid]')")
                emp_el  = parent.as_element() and parent.as_element().query_selector(
                    "[data-testid='company-name'], p.company"
                )
                if emp_el:
                    empresa = emp_el.inner_text().strip()

                reqs = ""
                if enlace:
                    try:
                        detail = page.context.new_page()
                        detail.goto(enlace, wait_until="domcontentloaded", timeout=15000)
                        _sleep(0.8, 1.5)
                        req_el = detail.query_selector(
                            "div.job-description, section[class*='description']"
                        )
                        if req_el:
                            reqs = req_el.inner_text()[:3000]
                        detail.close()
                    except Exception:
                        pass

                if len(reqs.strip()) < 50:
                    print(f"  [Skip] Sin reqs: {titulo[:45]}")
                    continue

                if not _passes_text_filter(titulo, reqs, filtros):
                    print(f"  [Filtro] Excluido por modalidad: {titulo[:45]}")
                    continue

                insertada, compat = _post_vacante(titulo, empresa, enlace, reqs)
                if insertada:
                    counter[0] += 1
                    count += 1
                    print(f"  + [{counter[0]}] {titulo[:50]} | {(empresa or 'Desconocida')[:22]} | {compat}")
            except Exception as ex:
                print(f"  [occ-card] {ex}")
    except Exception as ex:
        print(f"  [occ] {term}: {ex}")
    return count


# ── Indeed RSS ────────────────────────────────────────────────────────────────

_INDEED_DOMAINS = {
    "Mexico":        "mx.indeed.com",
    "España":        "es.indeed.com",
    "Argentina":     "ar.indeed.com",
    "Colombia":      "co.indeed.com",
    "Chile":         "cl.indeed.com",
    "Internacional": "www.indeed.com",
}

def scrape_indeed_rss(term: str, counter: list, limite: int | None, filtros: dict) -> int:
    """Scrape Indeed via RSS — sin Playwright, rápido y estable."""
    if limite is not None and counter[0] >= limite:
        return 0

    pais      = filtros.get("pais", "Mexico")
    modalidad = filtros.get("modalidad", "any")
    ubicacion = filtros.get("ubicacion", "").strip()
    domain    = _INDEED_DOMAINS.get(pais, "mx.indeed.com")

    q = urllib.parse.quote_plus(term)
    if modalidad == "remoto":
        q = urllib.parse.quote_plus(f"{term} remoto")
    l_param = ""
    if ubicacion and modalidad != "remoto":
        l_param = f"&l={urllib.parse.quote_plus(ubicacion)}"

    url   = f"https://{domain}/rss?q={q}&sort=date{l_param}"
    count = 0
    try:
        raw  = _http_get(url)
        root = _ET.fromstring(raw)
        ns   = {"": ""}
        items = root.findall("./channel/item")[:MAX_PER_TERM]
        for item in items:
            if limite is not None and counter[0] >= limite:
                break
            titulo  = (item.findtext("title") or "").strip()
            enlace  = (item.findtext("link")  or "").strip()
            empresa = (item.findtext("source") or "Desconocida").strip()
            desc_raw = item.findtext("description") or ""
            reqs    = _strip_html(desc_raw)[:3000]

            if not titulo or len(reqs.strip()) < 50:
                continue
            if not _passes_text_filter(titulo, reqs, filtros):
                continue

            insertada, compat = _post_vacante(titulo, empresa, enlace, reqs)
            if insertada:
                counter[0] += 1; count += 1
                print(f"  + [{counter[0]}] {titulo[:50]} | {empresa[:22]} | {compat}  [Indeed]")
        _sleep(0.8, 1.5)
    except Exception as ex:
        print(f"  [Indeed RSS] {term}: {ex}")
    return count


# ── Bumeran ────────────────────────────────────────────────────────────────────

def scrape_bumeran(page: Page, term: str, counter: list, limite: int | None, filtros: dict) -> int:
    """Scrape Bumeran (MX/Latam) via Playwright."""
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
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        _sleep(1.5, 2.5)
        _scroll(page)

        # Bumeran usa <a> con href que contiene /empleo/
        links = page.query_selector_all("a[href*='/empleo/']")[:MAX_PER_TERM]
        seen  = set()
        for link in links:
            if limite is not None and counter[0] >= limite:
                break
            try:
                href   = link.get_attribute("href") or ""
                enlace = ("https://www.bumeran.com.mx" + href) if href.startswith("/") else href
                if enlace in seen:
                    continue
                seen.add(enlace)

                titulo  = link.inner_text().strip()[:200]
                if not titulo or len(titulo) < 5:
                    continue

                reqs = ""
                try:
                    detail = page.context.new_page()
                    detail.goto(enlace, wait_until="domcontentloaded", timeout=15000)
                    _sleep(0.8, 1.5)
                    req_el = detail.query_selector(
                        "div[class*='description'], section[class*='detail'], div[id*='description']"
                    )
                    if req_el:
                        reqs = req_el.inner_text()[:3000]
                    empresa_el = detail.query_selector("a[href*='/empresa/'], span[class*='company']")
                    empresa = empresa_el.inner_text().strip() if empresa_el else "Desconocida"
                    detail.close()
                    _sleep(0.5, 1.0)
                except Exception:
                    empresa = "Desconocida"

                if len(reqs.strip()) < 50:
                    continue
                if not _passes_text_filter(titulo, reqs, filtros):
                    continue

                insertada, compat = _post_vacante(titulo, empresa, enlace, reqs)
                if insertada:
                    counter[0] += 1; count += 1
                    print(f"  + [{counter[0]}] {titulo[:50]} | {empresa[:22]} | {compat}  [Bumeran]")
            except Exception as ex:
                print(f"  [bumeran-card] {ex}")
        _sleep(2, 3)
    except Exception as ex:
        print(f"  [Bumeran] {term}: {ex}")
    return count


# ── Remotive (API JSON — solo remoto / tech global) ────────────────────────────

def scrape_remotive(term: str, counter: list, limite: int | None, filtros: dict) -> int:
    """Scrape Remotive API — trabajos remotos tech a nivel global."""
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

            insertada, compat = _post_vacante(titulo, empresa, enlace, reqs)
            if insertada:
                counter[0] += 1; count += 1
                print(f"  + [{counter[0]}] {titulo[:50]} | {empresa[:22]} | {compat}  [Remotive]")
        _sleep(1.0, 2.0)
    except Exception as ex:
        print(f"  [Remotive] {term}: {ex}")
    return count


# ── GetOnBrd (API JSON — tech Latam) ──────────────────────────────────────────

def scrape_getonbrd(term: str, counter: list, limite: int | None, filtros: dict) -> int:
    """Scrape GetOnBrd API — tech Latam (remoto + presencial)."""
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

                insertada, compat = _post_vacante(titulo, empresa, enlace, reqs)
                if insertada:
                    counter[0] += 1; count += 1
                    print(f"  + [{counter[0]}] {titulo[:50]} | {empresa[:22]} | {compat}  [GetOnBrd]")
            except Exception as ex:
                print(f"  [getonbrd-item] {ex}")
        _sleep(1.0, 2.0)
    except Exception as ex:
        print(f"  [GetOnBrd] {term}: {ex}")
    return count


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Browser Agent — scraping de vacantes vía API")
    parser.add_argument('--limit',   type=int,  default=None,   help="Máximo de vacantes a insertar (global)")
    parser.add_argument('--terms',   nargs='*', dest='named_terms', help="Términos de búsqueda")
    parser.add_argument('--filtros', type=str,  default='{}',   help='JSON de filtros: {"ubicacion":"...","modalidad":"...","pais":"..."}')
    parser.add_argument('positional_terms', nargs='*', help="Términos posicionales (legado)")
    args = parser.parse_args()

    limite = args.limit
    terms  = args.named_terms or args.positional_terms or SEARCH_TERMS

    try:
        filtros = {**_FILTROS_DEFAULT, **json.loads(args.filtros)}
    except json.JSONDecodeError:
        print(f"[WARN] --filtros JSON inválido, usando defaults: {args.filtros}")
        filtros = dict(_FILTROS_DEFAULT)

    print(f"[config] API: {API_BASE}")
    print(f"[config] Términos: {terms}")
    print(f"[config] Filtros: ubicacion={filtros['ubicacion']!r}  modalidad={filtros['modalidad']}  pais={filtros['pais']}")
    if limite:
        print(f"[config] Límite: {limite}")

    counter = [0]
    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=HEADLESS,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-web-security",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process",
                ]
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 900},
                locale="es-MX",
            )
            context.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
            )
            page = context.new_page()

            for term in terms:
                if limite is not None and counter[0] >= limite:
                    print(f"\n[límite] Alcanzado {limite}. Deteniendo.")
                    break

                print(f"\n[Computrabajo] '{term}'")
                scrape_computrabajo(page, term, counter, limite, filtros)

                if limite is not None and counter[0] >= limite: break

                print(f"\n[OCC] '{term}'")
                scrape_occ(page, term, counter, limite, filtros)

                if limite is not None and counter[0] >= limite: break

                print(f"\n[Indeed] '{term}'")
                scrape_indeed_rss(term, counter, limite, filtros)

                if limite is not None and counter[0] >= limite: break

                print(f"\n[Bumeran] '{term}'")
                scrape_bumeran(page, term, counter, limite, filtros)

                if limite is not None and counter[0] >= limite: break

                print(f"\n[GetOnBrd] '{term}'")
                scrape_getonbrd(term, counter, limite, filtros)

                if limite is not None and counter[0] >= limite: break

                print(f"\n[Remotive] '{term}'")
                scrape_remotive(term, counter, limite, filtros)

                _sleep(2, 4)

            browser.close()
            browser = None
    except Exception as e:
        print(f"\n[ERROR] {e}")
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass

    print(f"\n{'='*50}")
    print(f"Total enviadas a la API: {counter[0]} vacantes nuevas")


if __name__ == "__main__":
    main()
