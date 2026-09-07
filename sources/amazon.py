import re
from typing import List
from bs4 import BeautifulSoup
from playwright.sync_api import BrowserContext
from sources.models import Deal
from sources.currency import convert_to_cad

EXCLUDE_KEYWORDS = [
    "strap", "band", "protector", "film", "case", "cover", "cable",
    "charger", "charging dock", "replacement", "silicone", "leather band",
    "bezel", "tempered glass", "bracket", "airbag strap", "wrist strap", "cuff only"
]

def parse_price(text: str) -> float:
    if not text:
        return 0.0
    clean = text.replace(",", "").replace("\xa0", " ")
    match = re.search(r"(\d+(?:\.\d+)?)", clean)
    if match:
        return float(match.group(1))
    return 0.0

def scrape_amazon_search(context: BrowserContext, search_url: str, base_domain: str, target_model: str) -> List[Deal]:
    deals: List[Deal] = []
    page = context.new_page()
    try:
        page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        soup = BeautifulSoup(page.content(), "lxml")

        cards = soup.select("div[data-component-type='s-search-result']")
        for card in cards:
            # Full title is in a.a-link-normal with text or h2 + div
            title = ""
            link = search_url
            
            # Check all links for the product title link
            a_links = card.select("a.a-link-normal")
            for a in a_links:
                t = a.get_text(" ", strip=True)
                if len(t) > len(title) and not t.startswith("$") and not "ratings" in t.lower() and not "stars" in t.lower():
                    title = t
                    if "href" in a.attrs:
                        href = a["href"]
                        link = (base_domain + href.split("?")[0]) if href.startswith("/") else href.split("?")[0]

            if not title:
                h2 = card.select_one("h2")
                title = h2.get_text(" ", strip=True) if h2 else ""

            title_lower = title.lower()

            # Must mention Huawei and Watch
            if "huawei" not in title_lower or "watch" not in title_lower:
                continue

            # Check if this card matches Huawei Watch D, D2, or D3 (blood pressure models)
            is_d2 = "d2" in title_lower or "watch d 2" in title_lower
            is_d3 = "d3" in title_lower or "watch d 3" in title_lower
            is_d_original = "watch d" in title_lower and not ("fit" in title_lower or "gt" in title_lower)

            if not (is_d2 or is_d3 or is_d_original):
                continue

            # Must not be an accessory
            if any(k in title_lower for k in EXCLUDE_KEYWORDS):
                continue

            # Extract price
            price_offscreen = card.select_one(".a-price .a-offscreen")
            price_whole = card.select_one(".a-price-whole")
            price_frac = card.select_one(".a-price-fraction")

            if price_offscreen:
                raw_price_str = price_offscreen.get_text(strip=True)
            elif price_whole and price_frac:
                raw_price_str = f"{price_whole.get_text(strip=True).replace('.', '')}.{price_frac.get_text(strip=True)}"
            else:
                continue

            price_val = parse_price(raw_price_str)
            if price_val < 150.0:
                continue

            # Currency check
            if "US" in raw_price_str or "USD" in raw_price_str or ("$" in raw_price_str and "amazon.com" in base_domain):
                item_price_cad = convert_to_cad(price_val, "USD")
            elif "EUR" in raw_price_str or "€" in raw_price_str:
                item_price_cad = convert_to_cad(price_val, "EUR")
            elif "GBP" in raw_price_str or "£" in raw_price_str:
                item_price_cad = convert_to_cad(price_val, "GBP")
            else:
                item_price_cad = price_val

            # Shipping / Delivery details
            delivery_el = card.select_one(".a-row.a-size-base.a-color-secondary, [aria-label*='delivery'], [aria-label*='Delivery']")
            delivery_str = delivery_el.get_text(strip=True) if delivery_el else "Standard Delivery"
            
            shipping_cad = 0.0
            if "free" in delivery_str.lower() or "prime" in delivery_str.lower():
                shipping_cad = 0.0
            else:
                ship_match = parse_price(delivery_str)
                if ship_match > 0:
                    shipping_cad = ship_match if "amazon.ca" in base_domain else convert_to_cad(ship_match, "USD")

            model_label = "Huawei Watch D3" if is_d3 else ("Huawei Watch D2" if is_d2 else "Huawei Watch D")
            is_global = "global" in title_lower or "international" in title_lower or True

            deals.append(Deal(
                model=model_label,
                title=title,
                store=f"Amazon ({'Canada' if 'amazon.ca' in base_domain else 'Global'})",
                item_price_cad=round(item_price_cad, 2),
                shipping_price_cad=round(shipping_cad, 2),
                total_price_cad=round(item_price_cad + shipping_cad, 2),
                url=link,
                is_global_version=is_global,
                condition="Brand New",
                details=f"Listed: {raw_price_str} | Delivery: {delivery_str[:60]}"
            ))
    except Exception as e:
        print(f"[Amazon] Error scraping {search_url}: {e}")
    finally:
        page.close()
    return deals

def fetch_amazon_deals(context: BrowserContext) -> List[Deal]:
    results: List[Deal] = []
    
    searches = [
        ("https://www.amazon.ca/s?k=Huawei+Watch+D2+blood+pressure&rh=p_36%3A20000-120000", "https://www.amazon.ca", "Huawei Watch D2"),
        ("https://www.amazon.ca/s?k=Huawei+Watch+D3+blood+pressure&rh=p_36%3A20000-120000", "https://www.amazon.ca", "Huawei Watch D3"),
        ("https://www.amazon.ca/s?k=Huawei+Watch+D+blood+pressure&rh=p_36%3A20000-120000", "https://www.amazon.ca", "Huawei Watch D"),
        ("https://www.amazon.com/s?k=Huawei+Watch+D2+Global&rh=p_36%3A20000-120000", "https://www.amazon.com", "Huawei Watch D2"),
        ("https://www.amazon.com/s?k=Huawei+Watch+D3+Global&rh=p_36%3A20000-120000", "https://www.amazon.com", "Huawei Watch D3"),
    ]

    for url, base, model in searches:
        deals = scrape_amazon_search(context, url, base, model)
        if deals:
            print(f"[Amazon] Found {len(deals)} items for {model} on {base}")
        results.extend(deals)

    return results
