import re
import json
import requests
from bs4 import BeautifulSoup
from typing import List
from sources.models import Deal
from sources.currency import convert_to_cad

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-CA,en-US;q=0.9,en;q=0.8",
    "Cookie": "aep_usuc_f=region=CA&site=glo&b_locale=en_US&c_tp=CAD;"
}

def parse_price_str(text: str) -> float:
    if not text:
        return 0.0
    clean = text.replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)", clean)
    if match:
        return float(match.group(1))
    return 0.0

def search_aliexpress_model(query: str, model_name: str) -> List[Deal]:
    """
    Searches AliExpress for Huawei Watch D2/D3 Global version with ship to Canada.
    """
    deals: List[Deal] = []
    encoded = requests.utils.quote(query)
    url = f"https://www.aliexpress.com/w/wholesale-{encoded}.html?page=1&sortType=price_asc&shipFromCountry=all"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return deals

        # Look for window._dida_config_ or raw product cards
        soup = BeautifulSoup(resp.text, "lxml")
        
        # Check script JSON tags for modern AliExpress client-side hydration data
        scripts = soup.find_all("script")
        for s in scripts:
            script_text = s.string or ""
            if "itemList" in script_text or "products" in script_text or "pageData" in script_text:
                matches = re.findall(r'"title":\{"displayTitle":"(.*?)"\}.*?"price":\{"appPriceFormatted":"(.*?)"\}', script_text)
                for title, price_str in matches:
                    title_lower = title.lower()
                    if "watch" not in title_lower or ("d2" not in title_lower and "d3" not in title_lower):
                        continue
                    if any(x in title_lower for x in ["strap", "band", "case", "film", "cover", "protector"]):
                        continue
                    
                    price_val = parse_price_str(price_str)
                    if price_val < 150:
                        continue
                    
                    # Estimate free or ~$10 CAD shipping for AliExpress standard
                    shipping_cad = 0.0
                    deals.append(Deal(
                        model=model_name,
                        title=title,
                        store="AliExpress",
                        item_price_cad=price_val,
                        shipping_price_cad=shipping_cad,
                        total_price_cad=price_val + shipping_cad,
                        url=url,
                        is_global_version="global" in title_lower,
                        condition="Brand New",
                        details="AliExpress Global Listing (Standard Shipping to Canada included)"
                    ))

        # Also fallback HTML parsing
        cards = soup.select(".search-card-item, .list--gallery--34mggGX, a[class*='search-card-item']")
        for card in cards:
            title_el = card.select_one("h1, h3, [class*='title'], .multi--titleText--1QXePa2")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            title_lower = title.lower()

            if "watch" not in title_lower or ("d2" not in title_lower and "d3" not in title_lower):
                continue
            if any(x in title_lower for x in ["strap", "band", "case", "film", "cover"]):
                continue

            price_el = card.select_one("[class*='price'], [class*='salePrice']")
            if not price_el:
                continue

            price_val = parse_price_str(price_el.get_text(strip=True))
            if price_val < 150:
                continue

            link_el = card if card.name == "a" else card.select_one("a")
            link = link_el["href"] if (link_el and "href" in link_el.attrs) else url
            if link.startswith("//"):
                link = "https:" + link

            deals.append(Deal(
                model=model_name,
                title=title,
                store="AliExpress",
                item_price_cad=price_val,
                shipping_price_cad=0.0,
                total_price_cad=price_val,
                url=link,
                is_global_version="global" in title_lower,
                condition="Brand New",
                details="AliExpress Listing with CAD pricing & standard Canada shipping"
            ))

    except Exception as e:
        print(f"[AliExpress] Error: {e}")

    return deals

def fetch_aliexpress_deals() -> List[Deal]:
    results = []
    print("[AliExpress] Checking Huawei Watch D2 Global...")
    results.extend(search_aliexpress_model("huawei watch d2 global", "Huawei Watch D2"))
    print("[AliExpress] Checking Huawei Watch D3 Global...")
    results.extend(search_aliexpress_model("huawei watch d3 global", "Huawei Watch D3"))
    return results
