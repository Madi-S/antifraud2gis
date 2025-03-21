from playwright.sync_api import sync_playwright

def dump_2gis_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )

        page = browser.new_page()

        page.goto("https://2gis.ru/", wait_until="load")
        reviewApiKey = page.evaluate("__customcfg.reviewApiKey")
        print("reviewApiKey:", reviewApiKey)
        
        browser.close()

if __name__ == "__main__":
    dump_2gis_html()

