from playwright.sync_api import sync_playwright

def launch_browser():

    playwright = sync_playwright().start()

    browser = playwright.chromium.launch_persistent_context(
        user_data_dir="./sessions/facebook",
        headless=False
    )

    page = browser.new_page()

    return browser, page