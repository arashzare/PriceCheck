import os
import sys
from typing import List
from playwright.sync_api import sync_playwright
from sources.models import Deal
from sources.aliexpress import fetch_aliexpress_deals
from sources.amazon import fetch_amazon_deals
from sources.ebay import fetch_ebay_deals
from sources.importers import fetch_importer_deals
from sources.notifier import dispatch_notifications

def run_tracker():
    target_price_str = os.getenv("TARGET_PRICE_CAD", "420.0")
    try:
        target_price_cad = float(target_price_str)
    except ValueError:
        target_price_cad = 420.0

    print("=" * 70)
    print("  HUAWEI WATCH D2 / D3 DAILY PRICE & DEAL TRACKER (CANADA)")
    print(f"  Target Landed Threshold: ${target_price_cad:.2f} CAD (Item + Shipping to CA)")
    print("=" * 70)

    all_deals: List[Deal] = []

    # 1. Scrape with Playwright (AliExpress & Amazon)
    try:
        print("\n[Playwright] Launching browser engine for AliExpress & Amazon...")
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                locale="en-CA",
                viewport={"width": 1280, "height": 800}
            )
            
            ali_deals = fetch_aliexpress_deals(context)
            all_deals.extend(ali_deals)

            amazon_deals = fetch_amazon_deals(context)
            all_deals.extend(amazon_deals)
            
            browser.close()
    except Exception as e:
        print(f"[Main] Playwright browser error: {e}")

    # 2. Scrape eBay (New, Buy It Now, Ships to Canada)
    try:
        ebay_deals = fetch_ebay_deals()
        all_deals.extend(ebay_deals)
    except Exception as e:
        print(f"[Main] eBay fetch error: {e}")

    # 3. Scrape Importers (WondaMobile, Giztop)
    try:
        importer_deals = fetch_importer_deals()
        all_deals.extend(importer_deals)
    except Exception as e:
        print(f"[Main] Importer fetch error: {e}")

    print(f"\n[Main] Total listings collected across all stores: {len(all_deals)}")

    # Deduplicate by URL
    seen_urls = set()
    unique_deals: List[Deal] = []
    for d in all_deals:
        clean_url = d.url.split("?")[0]
        if clean_url not in seen_urls:
            seen_urls.add(clean_url)
            unique_deals.append(d)

    # Sort all deals from lowest to highest Total Landed Cost (CAD)
    unique_deals.sort(key=lambda x: x.total_price_cad)

    print("\n--- Current Lowest Available Market Listings (All Landed to CA with Direct Item Links) ---")
    if unique_deals:
        for i, d in enumerate(unique_deals[:10], 1):
            print(f"{i}. [{d.model}] {d.store}: ${d.total_price_cad:.2f} CAD (Item: ${d.item_price_cad:.2f} + Ship: ${d.shipping_price_cad:.2f})")
            print(f"   -> Title: {d.title[:65]}...")
            print(f"   -> Direct Item Link: {d.url}")
            print(f"   -> Details: {d.details}")
    else:
        print("No active listings found today.")

    matching_deals = [d for d in unique_deals if d.total_price_cad <= target_price_cad]

    print(f"\n[Main] Found {len(matching_deals)} deals under ${target_price_cad:.2f} CAD landed cost.")

    # Dispatch alerts (Discord / Telegram)
    dispatch_notifications(matching_deals, target_price_cad)

    # Generate summary report markdown artifact
    with open("latest_deals_report.md", "w", encoding="utf-8") as f:
        f.write("# Huawei Watch D2 / D3 Deal Report (Canada)\n\n")
        f.write(f"- **Target Threshold:** ${target_price_cad:.2f} CAD (all coupons, shipping & import fees included)\n")
        f.write(f"- **Qualifying Deals Found:** {len(matching_deals)}\n\n")
        
        f.write("## 🎯 Deals Under Target Price\n\n")
        if matching_deals:
            for d in matching_deals:
                f.write(f"### {d.model} — **${d.total_price_cad:.2f} CAD** (Landed)\n")
                f.write(f"- **Store:** {d.store}\n")
                f.write(f"- **Item Price (After Coupons):** ${d.item_price_cad:.2f} CAD\n")
                f.write(f"- **Shipping to Canada:** ${d.shipping_price_cad:.2f} CAD\n")
                f.write(f"- **Global Version:** {'Yes' if d.is_global_version else 'Check listing'}\n")
                f.write(f"- **Details / Promo:** {d.details}\n")
                f.write(f"- **Direct Purchase Link:** [Buy Direct on {d.store}]({d.url})\n\n")
        else:
            f.write("_No watches found under target price threshold on this run._\n\n")

        f.write("## 📊 Current Market Overview (Top Lowest Options)\n\n")
        if unique_deals:
            for d in unique_deals[:10]:
                f.write(f"- **{d.model}** ({d.store}): **${d.total_price_cad:.2f} CAD** (Item: ${d.item_price_cad:.2f} + Ship: ${d.shipping_price_cad:.2f}) — [Direct Item Link]({d.url})\n")
        else:
            f.write("_No listings tracked._\n")

    print("\n[Main] Finished. Report saved to latest_deals_report.md")

if __name__ == "__main__":
    run_tracker()
