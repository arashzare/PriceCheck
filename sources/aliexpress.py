import re
from typing import List, Tuple
from bs4 import BeautifulSoup
from playwright.sync_api import BrowserContext
from sources.models import Deal
from sources.currency import convert_to_cad

EXCLUDE_KEYWORDS = [
    "strap", "band", "protector", "film", "case", "cover", "cable",
    "charger", "charging dock", "replacement", "silicone", "leather band",
    "bezel", "tempered glass", "bracket", "airbag strap", "wrist strap", "remote"
]

def extract_coupon_discount(coupon_texts: List[str], base_price: float) -> Tuple[float, str]:
    total_discount = 0.0
    applied_note = ""

    for c in coupon_texts:
        if not c:
            continue
        c_clean = c.replace("\xa0", " ").strip()
        
        match_tier = re.search(r"(?:C\$|\$|CA\$)?\s*(\d+(?:\.\d+)?)\s*off\s*on\s*(?:C\$|\$|CA\$)?\s*(\d+(?:\.\d+)?)", c_clean, re.IGNORECASE)
        if match_tier:
            off_amount = float(match_tier.group(1))
            tier_req = float(match_tier.group(2))
            if base_price >= tier_req and tier_req > 0:
                multiplier = min(int(base_price // tier_req), 8)
                discount = off_amount * multiplier
                if discount > total_discount:
                    total_discount = discount
                    applied_note = f"Coupon applied ({c_clean} -> -${discount:.2f} CAD)"
            continue

        match_flat = re.search(r"(?:save|off)\s*(?:C\$|\$|CA\$)?\s*(\d+(?:\.\d+)?)", c_clean, re.IGNORECASE)
        if match_flat:
            discount = float(match_flat.group(1))
            if 5.0 <= discount <= 150.0 and discount > total_discount:
                total_discount = discount
                applied_note = f"Discount applied: -${discount:.2f} CAD"

    return total_discount, applied_note

def scrape_aliexpress_search(context: BrowserContext, search_url: str, model_name: str) -> List[Deal]:
    deals: List[Deal] = []
    page = context.new_page()
    try:
        page.goto("https://www.aliexpress.com", timeout=30000)
        page.context.add_cookies([
            {"name": "aep_usuc_f", "value": "region=CA&site=glo&b_locale=en_US&c_tp=CAD", "domain": ".aliexpress.com", "path": "/"}
        ])
        page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3500)
        page.evaluate("window.scrollBy(0, 1500)")
        page.wait_for_timeout(2000)

        soup = BeautifulSoup(page.content(), "lxml")
        
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

            direct_item_url = f"https://www.aliexpress.com/item/{item_id}.html"

            price_matches = re.findall(r"(?:CA\s*|C\s*|\$)?\s*(\d{2,4}(?:\.\d{2})?)", card_text)
            raw_price = 0.0
            for pm in price_matches:
                v = float(pm)
                if 220.0 <= v <= 1200.0:
                    raw_price = v
                    break

            if raw_price < 200.0:
                continue

            coupon_elements = card_parent.select("[class*='coupon'], [class*='promo'], [class*='discount'], [class*='tag--']")
            coupon_texts = [c.get_text(" ", strip=True) for c in coupon_elements]
            
            discount, coupon_note = extract_coupon_discount(coupon_texts, raw_price)
            final_price_after_coupon = max(raw_price - discount, 0.0)
            shipping_cad = 0.0

            total_landed = final_price_after_coupon + shipping_cad

            details_str = f"Listed: ${raw_price:.2f} CAD"
            if discount > 0:
                details_str += f" | {coupon_note} -> Final: ${final_price_after_coupon:.2f} CAD"
            else:
                details_str += " | Free Shipping to Canada"

            deals.append(Deal(
                model=model_name,
                title=title[:90],
                store="AliExpress",
                item_price_cad=round(final_price_after_coupon, 2),
                shipping_price_cad=round(shipping_cad, 2),
                total_price_cad=round(total_landed, 2),
                url=direct_item_url,
                is_global_version="global" in title_lower or "original" in title_lower,
                condition="Brand New",
                details=details_str
            ))
    except Exception as e:
        print(f"[AliExpress] Error: {e}")
    finally:
        page.close()
    return deals

def fetch_aliexpress_deals(context: BrowserContext) -> List[Deal]:
    results = []
    print("[AliExpress] Checking Huawei Watch D2 Global...")
    results.extend(scrape_aliexpress_search(context, "https://www.aliexpress.com/w/wholesale-huawei-watch-d2-global.html?sortType=price_asc", "Huawei Watch D2"))
    print("[AliExpress] Checking Huawei Watch D3 Global...")
    results.extend(scrape_aliexpress_search(context, "https://www.aliexpress.com/w/wholesale-huawei-watch-d3-global.html?sortType=price_asc", "Huawei Watch D3"))
    return results
