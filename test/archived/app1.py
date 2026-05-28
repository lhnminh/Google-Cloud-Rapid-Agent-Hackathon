from playwright.sync_api import sync_playwright

with sync_playwright() as p:

    browser = p.chromium.launch_persistent_context(
        user_data_dir="./sessions/facebook",
        headless=False
    )

    page = browser.new_page()

    page.goto("https://facebook.com")

    input("Log into Facebook manually, then press ENTER here...")