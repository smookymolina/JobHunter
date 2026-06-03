import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def debug_detail(url):
    r = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Try to find requirements/description
    print("--- Description/Requirements candidates ---")
    
    # Common Computrabajo detail page structure
    desc_el = soup.select_one('p.mb10')
    if desc_el:
        print(f"p.mb10 found: {desc_el.get_text(strip=True)[:200]}...")
    
    # Another common one
    article = soup.select_one('article')
    if article:
        print(f"Article text: {article.get_text(separator=' ', strip=True)[:300]}...")

    # Look for Company name in detail page
    company_el = soup.select_one('a.fc_base[href*="/empresas/"]')
    if company_el:
        print(f"Company el (a.fc_base): {company_el.get_text(strip=True)}")

if __name__ == "__main__":
    url = "https://www.computrabajo.com.mx/ofertas-de-trabajo/oferta-de-trabajo-de-desarrollador-full-stack-en-cuauhtemoc-267118B7ED7E2A1261373E686DCF3405"
    debug_detail(url)
