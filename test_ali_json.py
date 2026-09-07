from playwright.sync_api import sync_playwright
import json
import re

def test_ali_json():
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
        page.context.add_cookies([
            {"name": "aep_usuc_f", "value": "region=CA&site=glo&b_locale=en_US&c_tp=CAD", "domain": ".aliexpress.com", "path": "/"}
        ])

        url = "https://www.aliexpress.com/item/1005012881591386.html"
        page.goto(url, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(2000)

        # Check window.runParams
        run_params = page.evaluate("() => window.runParams || {}")
        print("runParams keys:", list(run_params.keys()) if isinstance(run_params, dict) else type(run_params))
        
        # Check visible price text
        price_text = page.locator("[class*='price'], [class*='Price']").all_inner_texts()
        print("Price elements found:", price_text[:6])

        # Check coupons / discounts on page
        coupons = page.locator("[class*='coupon'], [class*='promo'], [class*='discount']").all_inner_texts()
        print("Coupon texts:", coupons[:6])

        browser.close()

if __name__ == "__main__":
    test_ali_json()
