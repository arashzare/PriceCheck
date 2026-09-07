from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
from sources.models import Deal
from sources.currency import convert_to_cad

EXCLUDE_KEYWORDS = [
    "strap", "band", "protector", "film", "case", "cover", "cable",
    "charger", "charging dock", "replacement", "silicone", "leather band",
    "bezel", "tempered glass", "bracket", "airbag strap", "wrist strap", "remote"
]

def parse_price(text: str) -> float:
    if not text:
        return 0.0
    clean = text.replace(",", "").replace("\xa0", " ")
    match = re.search(r"(\d+(?:\.\d+)?)", clean)
    if match:
        return float(match.group(1))
    return 0.0

def scrape_aliexpress_search(context, search_url: str, model_name: str):
    deals = []
    page = context.new_page()
    try:
        page.goto("https://www.aliexpress.com", timeout=30000)
        page.context.add_cookies([
            {"name": "aep_usuc_f", "value": "region=CA&site=glo&b_locale=en_US&c_tp=CAD", "domain": ".aliexpress.com", "path": "/"}
        ])
        page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3500)
        page.evaluate("window.scrollBy(0, 1200)")
        page.wait_for_timeout(2000)

        soup = BeautifulSoup(page.content(), "lxml")
        
        # Parse search cards
        cards = soup.select("a[href*='/item/']")
        seen_items = set()

        for a in cards:
            href = a.get("href", "")
            match_id = re.search(r"/item/(\d+)\.html", href)
            if not match_id:
                continue
            item_id = match_id.group(1)
            if item_id in seen_items:
                continue
            seen_items.add(item_id)

            card_parent = a.find_parent("div", class_=re.compile(r"search-card-item|list--gallery|card--")) or a
            card_text = card_parent.get_text(" ", strip=True)
            title = a.get_text(" ", strip=True)
            if len(title) < 15:
                title = card_text

            title_lower = title.lower()

            if "watch" not in title_lower or ("d2" not in title_lower and "d3" not in title_lower and "watch d" not in title_lower):
                continue
            if any(k in title_lower for k in EXCLUDE_KEYWORDS):
                continue

            # Look for price in card
            price_matches = re.findall(r"(?:CA\s*|C\s*|\$)?\s*(\d{2,4}(?:\.\d{2})?)", card_text)
            price_val = 0.0
            for pm in price_matches:
                v = float(pm)
                if 200.0 <= v <= 1200.0:  # Valid watch price range
                    price_val = v
                    break

            if price_val < 180.0:
                continue

            clean_link = f"https://www.aliexpress.com/item/{item_id}.html"
            shipping_cad = 0.0  # Most global stores offer free shipping to Canada

            deals.append(Deal(
                model=model_name,
                title=title[:90],
                store="AliExpress",
                item_price_cad=round(price_val, 2),
                shipping_price_cad=shipping_cad,
                total_price_cad=round(price_val + shipping_cad, 2),
                url=clean_link,
                is_global_version="global" in title_lower or "original" in title_lower,
                condition="Brand New",
                details="AliExpress Direct Listing (Ships to Canada)"
            ))
    except Exception as e:
        print(f"[AliExpress] Error: {e}")
    finally:
        page.close()
    return deals
