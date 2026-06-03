"""
Browser Agent — scraping con Playwright (headed, anti-bot evasion).
Reemplaza scraper.py para sitios con lazy-load y protecciones JS.

Uso:
    python browser_agent.py                       # todos los términos, sin límite
    python browser_agent.py "IoT Developer"       # término específico
    python browser_agent.py --limit 5             # máximo 5 vacantes globales
    python browser_agent.py --limit 5 "IoT Dev"  # límite + término
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import argparse
import re
import sqlite3
import os
import time
import random

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout
from gemini_engine import DB_PATH, evaluar_compatibilidad_rapida, generar_terminos_busqueda

# ── Config ────────────────────────────────────────────────────────────────────

# Términos derivados del perfil maestro en tiempo de ejecución
SEARCH_TERMS: list[str] = generar_terminos_busqueda()

MAX_PER_TERM = 8   # vacantes a revisar por término (paginación interna)
HEADLESS     = False  # True = sin ventana (puede fallar anti-bot)

# ── DB ────────────────────────────────────────────────────────────────────────

def _update_compat(conn, enlace: str, compat: str):
    try:
        conn.execute("UPDATE vacantes SET compatibilidad=? WHERE enlace=?", (compat, enlace))
        conn.commit()
    except Exception as e:
        print(f"  [compat-update] {e}")


def _insert(conn, titulo, empresa, enlace, reqs):
    try:
        conn.execute(
            "INSERT OR IGNORE INTO vacantes (titulo, empresa, enlace, requerimientos) "
            "VALUES (?,?,?,?)",
            (titulo[:200], (empresa or "Desconocida")[:100], enlace, (reqs or "")[:3000])
        )
        conn.commit()
        return conn.execute("SELECT changes()").fetchone()[0] == 1
    except Exception as e:
        print(f"  [DB] {e}")
        return False

# ── Anti-bot helpers ──────────────────────────────────────────────────────────

def _sleep(a=1.0, b=2.5):
    time.sleep(random.uniform(a, b))

def _scroll(page: Page, steps=4):
    for _ in range(steps):
        page.evaluate("window.scrollBy(0, window.innerHeight * 0.7)")
        _sleep(0.4, 0.8)

def _human_type(page: Page, selector: str, text: str):
    page.click(selector)
    for ch in text:
        page.keyboard.type(ch)
        time.sleep(random.uniform(0.04, 0.12))

# ── Scrapers por sitio ────────────────────────────────────────────────────────

def scrape_computrabajo(page: Page, conn, term: str, counter: list, limite: int | None) -> int:
    """counter[0] es el total global insertado; limite corta cuando se alcanza."""
    count = 0
    url = f"https://www.computrabajo.com.mx/trabajo-de-{term.lower().replace(' ', '-')}"
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
                empresa = emp_el.inner_text().strip() if emp_el else None

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
                                import json
                                try:
                                    jld = json.loads(jld_raw)
                                    items = jld if isinstance(jld, list) else [jld]
                                    for item in items:
                                        if item.get("@type") == "JobPosting":
                                            h = item.get("hiringOrganization", {})
                                            empresa = h.get("name") if isinstance(h, dict) else None
                                except Exception:
                                    pass

                        req_el = detail.query_selector("div[div-link='oferta'], section.description, div.job-description")
                        if req_el:
                            reqs = req_el.inner_text()[:3000]
                        detail.close()
                        _sleep(0.5, 1.0)
                    except Exception as ex:
                        print(f"    [detail] {ex}")

                if len(reqs.strip()) < 50:
                    print(f"  [Skipped] Sin requerimientos suficientes: {titulo[:45]}")
                    continue
                if _insert(conn, titulo, empresa, enlace, reqs):
                    counter[0] += 1
                    count += 1
                    compat = evaluar_compatibilidad_rapida(reqs)
                    _update_compat(conn, enlace, compat)
                    print(f"  + [{counter[0]}] {titulo[:50]} | {(empresa or 'Desconocida')[:22]} | {compat}")
            except Exception as ex:
                print(f"  [card] {ex}")
    except Exception as ex:
        print(f"  [computrabajo] {term}: {ex}")
    return count


def scrape_occ(page: Page, conn, term: str, counter: list, limite: int | None) -> int:
    count = 0
    url = f"https://www.occ.com.mx/empleos/de-{term.lower().replace(' ', '-')}/"
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
                emp_el  = parent.as_element() and parent.as_element().query_selector("[data-testid='company-name'], p.company")
                if emp_el:
                    empresa = emp_el.inner_text().strip()

                reqs = ""
                if enlace:
                    try:
                        detail = page.context.new_page()
                        detail.goto(enlace, wait_until="domcontentloaded", timeout=15000)
                        _sleep(0.8, 1.5)
                        req_el = detail.query_selector("div.job-description, section[class*='description']")
                        if req_el:
                            reqs = req_el.inner_text()[:3000]
                        detail.close()
                    except Exception:
                        pass

                if len(reqs.strip()) < 50:
                    print(f"  [Skipped] Sin requerimientos suficientes: {titulo[:45]}")
                    continue
                if _insert(conn, titulo, empresa, enlace, reqs):
                    counter[0] += 1
                    count += 1
                    compat = evaluar_compatibilidad_rapida(reqs)
                    _update_compat(conn, enlace, compat)
                    print(f"  + [{counter[0]}] {titulo[:50]} | {(empresa or 'Desconocida')[:22]} | {compat}")
            except Exception as ex:
                print(f"  [occ-card] {ex}")
    except Exception as ex:
        print(f"  [occ] {term}: {ex}")
    return count

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Browser Agent — scraping de vacantes")
    parser.add_argument('--limit', type=int, default=None,
                        help="Número máximo de vacantes a insertar (global, todos los términos)")
    parser.add_argument('--terms', nargs='*', dest='named_terms',
                        help="Términos de búsqueda (sobrescribe perfil_maestro)")
    parser.add_argument('positional_terms', nargs='*',
                        help="Términos de búsqueda posicionales (legado)")
    args = parser.parse_args()

    limite = args.limit
    terms  = args.named_terms or args.positional_terms or SEARCH_TERMS

    if limite is not None:
        print(f"[config] Límite global: {limite} vacantes")

    conn    = sqlite3.connect(DB_PATH)
    counter = [0]   # contador global mutable compartido entre scrapers

    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=HEADLESS,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-web-security",
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
            context.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

            page = context.new_page()

            for term in terms:
                if limite is not None and counter[0] >= limite:
                    print(f"\n[limite] Alcanzado {limite} vacantes. Deteniendo.")
                    break

                print(f"\n[Computrabajo] '{term}'")
                scrape_computrabajo(page, conn, term, counter, limite)
                _sleep(2, 4)

                if limite is not None and counter[0] >= limite:
                    print(f"\n[limite] Alcanzado {limite} vacantes. Deteniendo.")
                    break

                print(f"\n[OCC] '{term}'")
                scrape_occ(page, conn, term, counter, limite)
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
        conn.close()

    total = counter[0]
    print(f"\n{'='*50}")
    print(f"Total insertadas: {total} vacantes nuevas")

    conn2 = sqlite3.connect(DB_PATH)
    rows = conn2.execute(
        "SELECT id, titulo, empresa, status FROM vacantes ORDER BY id DESC LIMIT 10"
    ).fetchall()
    conn2.close()
    print(f"\n--- Últimas {len(rows)} en DB ---")
    for r in rows:
        print(f"  [{r[0]:>3}] {r[1][:48]:<48} | {r[2][:22]:<22} | {r[3]}")

if __name__ == "__main__":
    main()
