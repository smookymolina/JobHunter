import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import feedparser
import requests
from bs4 import BeautifulSoup
import os
import re
import json
import time

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'vacantes.db')

SEARCH_TERMS = ["Ingeniero Mecanico", "IoT Developer", "Full Stack"]

RSS_FEEDS = [
    "https://mx.indeed.com/rss?q=Ingeniero+Mecanico&l=Mexico&sort=date",
    "https://mx.indeed.com/rss?q=IoT+Developer&l=Mexico&sort=date",
    "https://mx.indeed.com/rss?q=Full+Stack+Developer&l=Mexico&sort=date",
    "https://www.occ.com.mx/empleos/de-ingeniero-mecanico/?rss=1",
    "https://www.occ.com.mx/empleos/de-desarrollador-full-stack/?rss=1",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def extract_jsonld(html_text):
    """Extrae el bloque JSON-LD de tipo JobPosting del HTML, manejando @graph."""
    try:
        matches = re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html_text, re.DOTALL | re.IGNORECASE
        )
        for raw in matches:
            data = json.loads(raw.strip())
            
            # Caso: lista directa o dict único
            items = data if isinstance(data, list) else [data]
            
            # Caso: @graph
            if isinstance(data, dict) and "@graph" in data:
                items.extend(data["@graph"])

            for item in items:
                if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                    return item
    except Exception:
        pass
    return {}

def insert_vacante(conn, titulo, empresa, enlace, requerimientos):
    try:
        # Normalización básica
        empresa = (empresa or "Desconocida").strip()
        if empresa.lower() == "buscar empresas": # Cleanup de falsos positivos
            empresa = "Desconocida"
            
        conn.execute(
            "INSERT OR IGNORE INTO vacantes (titulo, empresa, enlace, requerimientos) VALUES (?,?,?,?)",
            (titulo[:200], empresa[:100], enlace, (requerimientos or "")[:2000])
        )
        conn.commit()
        return conn.execute("SELECT changes()").fetchone()[0] == 1
    except Exception as e:
        print(f"  [DB error] {e}")
        return False

def scrape_rss_feeds(conn):
    count = 0
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:5]:
                titulo = e.get('title', 'Sin título')
                empresa = e.get('author', e.get('source', {}).get('title', 'Desconocida'))
                enlace = e.get('link', '')
                reqs = BeautifulSoup(e.get('summary', ''), 'html.parser').get_text(separator=' ')[:1000]
                if insert_vacante(conn, titulo, empresa, enlace, reqs):
                    print(f"  + {titulo[:60]} | {empresa[:30]}")
                    count += 1
            time.sleep(1)
        except Exception as ex:
            print(f"  [RSS error] {url[:60]} -> {ex}")
    return count

def scrape_computrabajo(conn, term):
    count = 0
    try:
        url = f"https://www.computrabajo.com.mx/trabajo-de-{term.lower().replace(' ', '-')}"
        r = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, 'html.parser')

        cards = soup.select('article.box_offer')[:5]
        for card in cards:
            titulo_el = card.select_one('h2 a, h3 a')
            if not titulo_el:
                continue

            titulo = titulo_el.get_text(strip=True)
            href = titulo_el.get('href', '')
            enlace = ("https://www.computrabajo.com.mx" + href) if href.startswith('/') else href

            # 1) Intento rápido desde el card
            emp_el = card.select_one('p.fs16.fc_base.mt5') or card.select_one('p.dcolor')
            empresa = emp_el.get_text(strip=True) if emp_el else None
            reqs = ""

            # 2) Detalle para requisitos y fallback de empresa
            if enlace:
                try:
                    print(f"  -> Detalle: {titulo[:40]}...")
                    detail = requests.get(enlace, headers=HEADERS, timeout=10)
                    jld = extract_jsonld(detail.text)
                    
                    if jld:
                        # Empresa desde JSON-LD
                        hiring = jld.get('hiringOrganization', {})
                        if not empresa or empresa == "Desconocida":
                            empresa = hiring.get('name') if isinstance(hiring, dict) else None
                        
                        # Requisitos desde JSON-LD
                        desc_raw = jld.get('description', '')
                        reqs = BeautifulSoup(desc_raw, 'html.parser').get_text(separator='\n', strip=True)
                    
                    if not reqs:
                        # Fallback a scraping HTML del detalle
                        d_soup = BeautifulSoup(detail.text, 'html.parser')
                        offer_div = d_soup.select_one('div[div-link="oferta"]')
                        if offer_div:
                            reqs = offer_div.get_text(separator='\n', strip=True)
                        
                    time.sleep(1.2)
                except Exception as ex:
                    print(f"    [Detail error] {ex}")

            if not empresa: empresa = "Desconocida"
            if not reqs: reqs = card.get_text(separator=' ', strip=True)[:800]

            if insert_vacante(conn, titulo, empresa, enlace, reqs):
                print(f"  + {titulo[:60]} | {empresa[:30]}")
                count += 1
        time.sleep(1)
    except Exception as ex:
        print(f"  [Computrabajo error] {term}: {ex}")
    return count

def main():
    if not os.path.exists(DB_PATH):
        print("DB no encontrada. Ejecuta primero: python src/init_db.py")
        return

    conn = sqlite3.connect(DB_PATH)
    total = 0

    print("\n[1/2] RSS feeds...")
    total += scrape_rss_feeds(conn)

    print("\n[2/2] Computrabajo...")
    for term in SEARCH_TERMS:
        total += scrape_computrabajo(conn, term)
        time.sleep(1.5)

    conn.close()
    print(f"\n✓ Insertadas: {total} vacantes nuevas")

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, titulo, empresa, status FROM vacantes ORDER BY id DESC LIMIT 10"
    ).fetchall()
    conn.close()
    print(f"\n--- Últimas {len(rows)} vacantes en DB ---")
    for r in rows:
        print(f"  [{r[0]:>3}] {r[1][:48]:<48} | {r[2][:22]:<22} | {r[3]}")

if __name__ == '__main__':
    main()
