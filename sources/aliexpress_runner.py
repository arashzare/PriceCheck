from sources.aliexpress import scrape_aliexpress_search

def fetch_aliexpress_deals(context):
    results = []
    print("[AliExpress] Checking Huawei Watch D2 Global...")
    results.extend(scrape_aliexpress_search(context, "https://www.aliexpress.com/w/wholesale-huawei-watch-d2-global.html?sortType=price_asc", "Huawei Watch D2"))
    print("[AliExpress] Checking Huawei Watch D3 Global...")
    results.extend(scrape_aliexpress_search(context, "https://www.aliexpress.com/w/wholesale-huawei-watch-d3-global.html?sortType=price_asc", "Huawei Watch D3"))
    return results
