import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def debug_computrabajo():
    url = "https://www.computrabajo.com.mx/trabajo-de-ingeniero-mecanico"
    print(f"Fetching {url}...")
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        print(f"Status: {r.status_code}")
        soup = BeautifulSoup(r.text, 'html.parser')
        cards = soup.select('article.box_offer')
        print(f"Found {len(cards)} cards")
        
        for i, card in enumerate(cards[:3]):
            print(f"\nCard {i+1}:")
            # All text in card
            # print(card.get_text(separator=' | ', strip=True))
            
            titulo_el = card.select_one('h2 a, h3 a')
            if titulo_el:
                print(f"  Title: {titulo_el.get_text(strip=True)}")
            
            # Try different selectors for company
            selectors = ['p.fs16.fc_base.mt5', 'p.dcolor', 'a.fc_base', 'span.fc_base']
            for sel in selectors:
                el = card.select_one(sel)
                if el:
                    print(f"  Selector '{sel}': {el.get_text(strip=True)}")
            
            # Let's see the HTML of the first card to find the right selector
            if i == 0:
                print("\n  Full HTML of first card (truncated):")
                print(str(card)[:1000])

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_computrabajo()
