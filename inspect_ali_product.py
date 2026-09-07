from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

def inspect_aliexpress_product():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-CA"
        )
        page = context.new_page()
        page.goto("https://www.aliexpress.com", timeout=30000)
        page.context.add_cookies([
            {"name": "aep_usuc_f", "value": "region=CA&site=glo&b_locale=en_US&c_tp=CAD", "domain": ".aliexpress.com", "path": "/"}
        ])

        test_item_url = "https://www.aliexpress.com/item/1005012881591386.html"
        print(f"Loading product page: {test_item_url}")
        page.goto(test_item_url, timeout=35000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        soup = BeautifulSoup(page.content(), "lxml")

        # 1. Title
        title_el = soup.select_one("h1[data-pl='product-title'], h1")
        title = title_el.get_text(strip=True) if title_el else page.title()
        print("Product Title:", title[:80])

        # 2. Main Price
        price_el = soup.select_one(".product-price-current, [class*='currentPrice'], [class*='price--currentPrice']")
        price_text = price_el.get_text(strip=True) if price_el else "N/A"
        print("Current Price Text:", price_text)

        # 3. Coupons / Discounts / Promo codes
        coupons = soup.select("[class*='coupon'], [class*='promo'], [class*='discount'], [class*='voucher']")
        print(f"Coupon elements count: {len(coupons)}")
        for c in coupons[:5]:
            t = c.get_text(" ", strip=True)
            if len(t) > 3 and not "coupon" == t.lower():
                print("  Coupon/Discount:", t)

        # 4. Shipping to Canada
        shipping_el = soup.select_one("[class*='shipping'], [class*='delivery'], [class*='logistics']")
        shipping_text = shipping_el.get_text(" ", strip=True) if shipping_el else "Free Shipping"
        print("Shipping Text:", shipping_text[:80])

        browser.close()

if __name__ == "__main__":
    inspect_aliexpress_product()
