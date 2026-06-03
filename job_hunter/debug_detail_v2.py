import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def debug_detail(url):
    r = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    with open("detail.html", "w", encoding="utf-8") as f:
        f.write(r.text)
    print("Saved HTML to detail.html")

    # Find the company name
    # Usually it's in a box with some classes
    for a in soup.find_all('a', href=True):
        if '/empresas/' in a['href']:
            print(f"Potential company link: {a.get_text(strip=True)} ({a['href']})")

    # Find the requirements
    for li in soup.select('ul.disc.mb10 li'):
        print(f"Requirement li: {li.get_text(strip=True)}")

if __name__ == "__main__":
    url = "https://www.computrabajo.com.mx/ofertas-de-trabajo/oferta-de-trabajo-de-desarrollador-full-stack-en-cuauhtemoc-267118B7ED7E2A1261373E686DCF3405"
    debug_detail(url)
