import requests
import re
import json
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def extract_jsonld(html_text):
    try:
        matches = re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html_text, re.DOTALL | re.IGNORECASE
        )
        for raw in matches:
            data = json.loads(raw.strip())
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get('@type') == 'JobPosting':
                    return item
    except Exception as e:
        print(f"Error parsing JSON: {e}")
    return {}

def test_link(url):
    print(f"Fetching {url}...")
    r = requests.get(url, headers=HEADERS, timeout=10)
    print(f"Status: {r.status_code}")
    jld = extract_jsonld(r.text)
    if jld:
        print("Found JobPosting JSON-LD!")
        hiring = jld.get('hiringOrganization', {})
        print(f"Company: {hiring.get('name') if isinstance(hiring, dict) else hiring}")
        desc = jld.get('description', '')
        print(f"Description length: {len(desc)}")
    else:
        print("No JobPosting JSON-LD found.")
        # Check if there's ANY JSON-LD
        matches = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', r.text, re.DOTALL | re.IGNORECASE)
        print(f"Total JSON-LD blocks found: {len(matches)}")

if __name__ == "__main__":
    url = "https://www.computrabajo.com.mx/ofertas-de-trabajo/oferta-de-trabajo-de-desarrollador-full-stack-en-cuauhtemoc-267118B7ED7E2A1261373E686DCF3405"
    test_link(url)
