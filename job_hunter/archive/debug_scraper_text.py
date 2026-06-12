import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def debug_computrabajo():
    url = "https://www.computrabajo.com.mx/trabajo-de-ingeniero-mecanico"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        cards = soup.select('article.box_offer')
        
        for i, card in enumerate(cards[:1]):
            print(f"Card {i+1} all text:")
            print(card.get_text(separator=' | ', strip=True))
            
            print("\nTrying to find description/reqs specifically:")
            # Description is often in a p or span with a specific class
            desc_el = card.select_one('p.fs13.fc_aux') # Common in some versions
            if desc_el:
                print(f"  Found p.fs13.fc_aux: {desc_el.get_text(strip=True)}")
            
            # Let's check all p tags
            for p in card.find_all('p'):
                print(f"  p tag (class={p.get('class')}): {p.get_text(strip=True)[:100]}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_computrabajo()
