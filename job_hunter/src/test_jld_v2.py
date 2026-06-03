import requests
import re
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def test_link(url):
    r = requests.get(url, headers=HEADERS, timeout=10)
    matches = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', r.text, re.DOTALL | re.IGNORECASE)
    for i, raw in enumerate(matches):
        print(f"Block {i}:")
        print(raw.strip()[:500])
        try:
            data = json.loads(raw.strip())
            print(f"Type: {data.get('@type') if isinstance(data, dict) else 'List'}")
        except:
            print("Failed to parse JSON")

if __name__ == "__main__":
    url = "https://www.computrabajo.com.mx/ofertas-de-trabajo/oferta-de-trabajo-de-desarrollador-full-stack-en-cuauhtemoc-267118B7ED7E2A1261373E686DCF3405"
    test_link(url)
