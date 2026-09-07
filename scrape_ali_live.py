from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import re

def scrape_aliexpress_live():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-CA",
            extra_http_headers={
                "Accept-Language": "en-CA,en-US;q=0.9,en;q=0.8"
            }
        )
        page = context.new_page()
        # Set cookies for Canada + CAD currency
        page.goto("https://www.aliexpress.com", timeout=30000)
        page.context.add_cookies([
            {"name": "aep_usuc_f", "value": "region=CA&site=glo&b_locale=en_US&c_tp=CAD", "domain": ".aliexpress.com", "path": "/"}
        ])

        url = "https://www.aliexpress.com/w/wholesale-huawei-watch-d2-global.html?sortType=price_asc"
        print(f"Navigating to: {url}")
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        # Scroll down to load lazy cards
        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(2000)

        soup = BeautifulSoup(page.content(), "lxml")
        
        # Save page content for inspection
        with open("ali_page.html", "w", encoding="utf-8") as f:
            f.write(page.content())

        print("Page title:", page.title())
        
        # Find item titles & prices
        cards = soup.select("[class*='search-card-item'], [class*='list--gallery'], [class*='card--']")
        print(f"Total card containers found: {len(cards)}")
        
        links = soup.find_all("a", href=re.compile(r"/item/\d+\.html"))
        print(f"Direct item links found: {len(links)}")
        
        for a in links[:10]:
            title = a.get_text(" ", strip=True)
            href = a["href"]
            if href.startswith("//"):
                href = "https:" + href
            print(f"Link: {href[:60]} | Text: {title[:80]}")

        browser.close()

if __name__ == "__main__":
    scrape_aliexpress_live()
