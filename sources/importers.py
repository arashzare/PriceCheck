import re
import requests
from bs4 import BeautifulSoup
from typing import List
from sources.models import Deal
from sources.currency import convert_to_cad

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

def parse_price_str(text: str) -> float:
    if not text:
        return 0.0
    clean = text.replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)", clean)
    if match:
        return float(match.group(1))
    return 0.0

def check_wondamobile() -> List[Deal]:
    """
    WondaMobile is one of the premier international shippers for global Huawei devices.
    Estimated shipping to Canada is approx $28 USD (~$38 CAD) DHL Express.
    """
    deals: List[Deal] = []
    urls = [
        ("https://www.wondamobile.com/catalogsearch/result/?q=huawei+watch+d2", "Huawei Watch D2"),
        ("https://www.wondamobile.com/catalogsearch/result/?q=huawei+watch+d3", "Huawei Watch D3")
    ]
    
    SHIPPING_TO_CA_USD = 28.00  # Standard DHL shipping to Canada on WondaMobile
    shipping_cad = convert_to_cad(SHIPPING_TO_CA_USD, "USD")

    for search_url, model_name in urls:
        try:
            resp = requests.get(search_url, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                continue
            
            soup = BeautifulSoup(resp.text, "lxml")
            items = soup.select(".product-item, .product-item-info")
            for item in items:
                title_el = item.select_one(".product-item-link, .product-name a")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                title_lower = title.lower()

                if "watch" not in title_lower or ("d2" not in title_lower and "d3" not in title_lower):
                    continue

                if any(x in title_lower for x in ["strap", "band", "case", "protector"]):
                    continue

                link = title_el.get("href", search_url)
                
                price_el = item.select_one("[data-price-type='finalPrice'], .price")
                if not price_el:
                    continue
                
                price_val = parse_price_str(price_el.get_text(strip=True))
                # WondaMobile prices are typically USD or GBP
                item_price_cad = convert_to_cad(price_val, "USD")
                total_cad = item_price_cad + shipping_cad

                if total_cad < 150:
                    continue

                deals.append(Deal(
                    model=model_name,
                    title=title,
                    store="WondaMobile",
                    item_price_cad=round(item_price_cad, 2),
                    shipping_price_cad=round(shipping_cad, 2),
                    total_price_cad=round(total_cad, 2),
                    url=link,
                    is_global_version="global" in title_lower or True,
                    condition="Brand New",
                    details=f"Item ~${price_val:.2f} USD + DHL to Canada (~${SHIPPING_TO_CA_USD:.2f} USD)"
                ))
        except Exception as e:
            print(f"[WondaMobile] Error: {e}")
            
    return deals

def check_giztop() -> List[Deal]:
    """
    Giztop ships global gadgets worldwide.
    Estimated standard shipping to Canada is ~$20 USD (~$27 CAD).
    """
    deals: List[Deal] = []
    urls = [
        ("https://www.giztop.com/catalogsearch/result/?q=huawei+watch+d2", "Huawei Watch D2"),
        ("https://www.giztop.com/catalogsearch/result/?q=huawei+watch+d3", "Huawei Watch D3")
    ]
    SHIPPING_TO_CA_USD = 20.00
    shipping_cad = convert_to_cad(SHIPPING_TO_CA_USD, "USD")

    for search_url, model_name in urls:
        try:
            resp = requests.get(search_url, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            items = soup.select(".product-item-info")
            for item in items:
                title_el = item.select_one(".product-item-link")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                title_lower = title.lower()

                if "watch" not in title_lower or ("d2" not in title_lower and "d3" not in title_lower):
                    continue
                if any(x in title_lower for x in ["strap", "band", "case", "film", "protector"]):
                    continue

                link = title_el.get("href", search_url)
                price_el = item.select_one(".price")
                if not price_el:
                    continue

                price_val = parse_price_str(price_el.get_text(strip=True))
                item_price_cad = convert_to_cad(price_val, "USD")
                total_cad = item_price_cad + shipping_cad

                if total_cad < 150:
                    continue

                deals.append(Deal(
                    model=model_name,
                    title=title,
                    store="Giztop",
                    item_price_cad=round(item_price_cad, 2),
                    shipping_price_cad=round(shipping_cad, 2),
                    total_price_cad=round(total_cad, 2),
                    url=link,
                    is_global_version="global" in title_lower,
                    condition="Brand New",
                    details=f"Item ~${price_val:.2f} USD + Shipping to Canada (~${SHIPPING_TO_CA_USD:.2f} USD)"
                ))
        except Exception as e:
            print(f"[Giztop] Error: {e}")

    return deals

def fetch_importer_deals() -> List[Deal]:
    results = []
    print("[Importers] Checking WondaMobile...")
    results.extend(check_wondamobile())
    print("[Importers] Checking Giztop...")
    results.extend(check_giztop())
    return results
