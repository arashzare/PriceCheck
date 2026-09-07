import re
import requests
from bs4 import BeautifulSoup
from typing import List
from sources.models import Deal
from sources.currency import convert_to_cad

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-CA,en-US;q=0.9,en;q=0.8"
})

EXCLUDE_KEYWORDS = [
    "strap", "band", "protector", "film", "case", "cover", "cable",
    "charger", "charging dock", "replacement", "silicone", "leather band",
    "bezel", "tempered glass", "bracket", "airbag strap", "wrist strap", "cuff"
]

def parse_price_str(text: str) -> float:
    if not text:
        return 0.0
    clean = text.replace(",", "").replace("\xa0", " ")
    match = re.search(r"(\d+(?:\.\d+)?)", clean)
    if match:
        return float(match.group(1))
    return 0.0

def search_ebay_model(model_keyword: str, model_name: str) -> List[Deal]:
    deals: List[Deal] = []
    encoded_query = requests.utils.quote(f"{model_keyword} -strap -case -film -band -glass -charger")
    url = f"https://www.ebay.ca/sch/i.html?_nkw={encoded_query}&_sop=15&LH_BIN=1&LH_ItemCondition=1000&_ipg=60"

    try:
        resp = SESSION.get(url, timeout=15)
        if resp.status_code != 200:
            return deals

        soup = BeautifulSoup(resp.text, "lxml")
        items = soup.select(".s-item, .srp-results .s-item")

        for item in items:
            title_el = item.select_one(".s-item__title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            title_lower = title.lower()

            if "shop on ebay" in title_lower or len(title) < 10:
                continue

            if "watch" not in title_lower or ("d2" not in title_lower and "d3" not in title_lower and "watch d" not in title_lower):
                continue

            if any(k in title_lower for k in EXCLUDE_KEYWORDS):
                continue

            # DIRECT ITEM LINK EXTRACTION
            link_el = item.select_one(".s-item__link")
            if not link_el or "href" not in link_el.attrs:
                continue
            
            raw_href = link_el["href"]
            # Extract item id: https://www.ebay.ca/itm/123456789...
            match_itm = re.search(r"/itm/(?:.*?/)?(\d+)", raw_href)
            if match_itm:
                direct_item_url = f"https://www.ebay.ca/itm/{match_itm.group(1)}"
            else:
                direct_item_url = raw_href.split("?")[0]

            price_el = item.select_one(".s-item__price")
            if not price_el:
                continue
            price_text = price_el.get_text(strip=True)

            item_price = parse_price_str(price_text)
            if "US" in price_text or "USD" in price_text or ("$" in price_text and "C" not in price_text):
                item_price_cad = convert_to_cad(item_price, "USD")
            elif "EUR" in price_text or "€" in price_text:
                item_price_cad = convert_to_cad(item_price, "EUR")
            elif "GBP" in price_text or "£" in price_text:
                item_price_cad = convert_to_cad(item_price, "GBP")
            else:
                item_price_cad = item_price

            shipping_el = item.select_one(".s-item__shipping, .s-item__logisticsCost")
            shipping_price_cad = 0.0
            ship_text = shipping_el.get_text(strip=True) if shipping_el else "Free"
            
            if "free" in ship_text.lower():
                shipping_price_cad = 0.0
            else:
                ship_val = parse_price_str(ship_text)
                if "us" in ship_text.lower() or ("$" in ship_text and "c" not in ship_text.lower()):
                    shipping_price_cad = convert_to_cad(ship_val, "USD")
                else:
                    shipping_price_cad = ship_val

            total_price_cad = item_price_cad + shipping_price_cad

            if total_price_cad < 180.0:
                continue

            is_global = "global" in title_lower or "international" in title_lower or "english" in title_lower

            deals.append(Deal(
                model=model_name,
                title=title,
                store="eBay",
                item_price_cad=round(item_price_cad, 2),
                shipping_price_cad=round(shipping_price_cad, 2),
                total_price_cad=round(total_price_cad, 2),
                url=direct_item_url,
                is_global_version=is_global,
                condition="Brand New",
                details=f"Listed: {price_text} | Ship: {ship_text}"
            ))

    except Exception as e:
        print(f"[eBay] Error scraping for {model_name}: {e}")

    return deals

def fetch_ebay_deals() -> List[Deal]:
    results = []
    results.extend(search_ebay_model("Huawei Watch D2", "Huawei Watch D2"))
    results.extend(search_ebay_model("Huawei Watch D3", "Huawei Watch D3"))
    return results
