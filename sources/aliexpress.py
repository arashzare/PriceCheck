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
    """
    Parses coupons like 'C$6.00 off on C$45.00', 'C$40 off on C$300', 'Save C$50'
    and calculates the exact discount amount.
    """
    total_discount = 0.0
    applied_note = ""

    for c in coupon_texts:
        if not c:
            continue
        c_clean = c.replace("\xa0", " ").strip()
        
        # Match "C$6.00 off on C$45.00" or "$6 off on $45" (Tiered discount)
        match_tier = re.search(r"(?:C\$|\$|CA\$)?\s*(\d+(?:\.\d+)?)\s*off\s*on\s*(?:C\$|\$|CA\$)?\s*(\d+(?:\.\d+)?)", c_clean, re.IGNORECASE)
        if match_tier:
            off_amount = float(match_tier.group(1))
            tier_req = float(match_tier.group(2))
            if base_price >= tier_req and tier_req > 0:
                multiplier = int(base_price // tier_req)
                # AliExpress usually caps tiered discounts at around $60-$80 max per order
                multiplier = min(multiplier, 10)
                discount = off_amount * multiplier
                if discount > total_discount:
                    total_discount = discount
                    applied_note = f"Coupon Applied: {c_clean} (-${discount:.2f} CAD)"
            continue

        # Match direct flat discounts: "Save $X", "Save C$X", "$X off"
        match_flat = re.search(r"(?:save|off)\s*(?:C\$|\$|CA\$)?\s*(\d+(?:\.\d+)?)", c_clean, re.IGNORECASE)
        if match_flat:
            discount = float(match_flat.group(1))
            # Ignore bogus multi-hundred fake MSRP 'savings' (e.g. Save $500), only match real coupons < 150
            if 4.0 <= discount <= 120.0 and discount > total_discount:
                total_discount = discount
                applied_note = f"Coupon Applied: -${discount:.2f} CAD"

    return total_discount, applied_note

def classify_model(title: str) -> str:
    title_lower = title.lower()
    if "d3" in title_lower or "watch d 3" in title_lower or "watch d3" in title_lower:
        return "Huawei Watch D3"
    elif "d2" in title_lower or "watch d 2" in title_lower or "watch d2" in title_lower:
        return "Huawei Watch D2"
    elif "watch d" in title_lower:
        return "Huawei Watch D (Gen 1)"
    return "Huawei Watch D Series"

def inspect_product_page_for_coupons(context: BrowserContext, item_url: str, fallback_price: float) -> Tuple[float, float, str, str]:
    """
    Visits the direct product page to extract the EXACT displayed price and any product page coupons.
    Returns: (exact_price, discount, coupon_note, shipping_text)
    """
    page = context.new_page()
    try:
        page.goto(item_url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        
        soup = BeautifulSoup(page.content(), "lxml")
        
        # 1. Exact price on product page
        price_el = soup.select_one(".product-price-current, [class*='currentPrice'], [class*='price--currentPrice']")
        raw_price_str = price_el.get_text(strip=True) if price_el else ""
        price_match = re.search(r"(?:C\$|\$|CA\$)?\s*(\d{2,4}\.\d{2})", raw_price_str)
        exact_price = float(price_match.group(1)) if price_match else fallback_price

        # 2. Extract coupons (e.g. 'C$6.00 off on C$45.00')
        coupon_elements = soup.select("[class*='coupon'], [class*='promo'], [class*='voucher'], [class*='discount']")
        # Also grab all text elements matching "off on"
        all_text = page.locator("text=/off on/i").all_inner_texts()
        coupon_texts = [c.get_text(" ", strip=True) for c in coupon_elements] + all_text
        
        discount, coupon_note = extract_coupon_discount(coupon_texts, exact_price)

        # 3. Shipping
        shipping_el = soup.select_one("[class*='shipping'], [class*='delivery'], [class*='logistics']")
        shipping_str = shipping_el.get_text(" ", strip=True) if shipping_el else "Free Shipping"

        return exact_price, discount, coupon_note, shipping_str
    except Exception as e:
        print(f"[AliExpress Product Inspector] Error on {item_url}: {e}")
        return fallback_price, 0.0, "", "Free Shipping"
    finally:
        page.close()

def scrape_aliexpress_search(context: BrowserContext, search_url: str, default_model: str) -> List[Deal]:
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
        candidate_items = []

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

            if "watch" not in title_lower or ("watch d" not in title_lower and "d2" not in title_lower and "d3" not in title_lower):
                continue
            if any(k in title_lower for k in EXCLUDE_KEYWORDS):
                continue

            # Parse rough base price
            price_matches = re.findall(r"(?:CA\s*|C\s*|\$)?\s*(\d{2,4}\.\d{2})", card_text)
            if not price_matches:
                price_matches = re.findall(r"(?:CA\s*|C\s*|\$)?\s*(\d{2,4})", card_text)

            base_price = 0.0
            for pm in price_matches:
                v = float(pm)
                if 200.0 <= v <= 1200.0:
                    base_price = v
                    break

            if base_price < 200.0:
                continue

            direct_item_url = f"https://www.aliexpress.com/item/{item_id}.html"
            candidate_items.append((title, base_price, direct_item_url))

        page.close()

        # For the top candidate items, inspect the product page directly to extract coupons & exact price
        print(f"[AliExpress] Inspecting {len(candidate_items[:6])} top product pages for coupons...")
        for title, base_price, direct_item_url in candidate_items[:6]:
            exact_price, discount, coupon_note, shipping_str = inspect_product_page_for_coupons(context, direct_item_url, base_price)
            
            final_price = max(exact_price - discount, 0.0)
            shipping_cad = 0.0

            actual_model = classify_model(title)
            
            details_str = f"Listed: ${exact_price:.2f} CAD"
            if discount > 0:
                details_str += f" | {coupon_note} -> Checkout Total: ${final_price:.2f} CAD"
            else:
                details_str += " | Free Shipping to Canada"

            deals.append(Deal(
                model=actual_model,
                title=title[:90],
                store="AliExpress",
                item_price_cad=round(final_price, 2),
                shipping_price_cad=round(shipping_cad, 2),
                total_price_cad=round(final_price + shipping_cad, 2),
                url=direct_item_url,
                is_global_version="global" in title.lower() or "original" in title.lower(),
                condition="Brand New" if "98new" not in title.lower() else "Open Box / 98% New",
                details=details_str
            ))

    except Exception as e:
        print(f"[AliExpress] Error: {e}")

    return deals

def fetch_aliexpress_deals(context: BrowserContext) -> List[Deal]:
    results = []
    print("[AliExpress] Checking Huawei Watch D2 Global...")
    results.extend(scrape_aliexpress_search(context, "https://www.aliexpress.com/w/wholesale-huawei-watch-d2-global.html?sortType=price_asc", "Huawei Watch D2"))
    return results
