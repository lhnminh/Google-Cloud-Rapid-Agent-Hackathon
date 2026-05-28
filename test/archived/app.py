from playwright.sync_api import sync_playwright
import time

FRIEND_NAME = "Minh Ngoc"
MESSAGE = "hello from playwright"

with sync_playwright() as p:

    browser = p.chromium.launch_persistent_context(
        user_data_dir="./sessions/facebook",
        headless=False
    )

    page = browser.new_page()

    page.goto("https://www.facebook.com/messages")

    page.wait_for_timeout(5000)

    search_box = page.locator('input[placeholder="Search Messenger"]')
    search_box.fill(FRIEND_NAME)

    page.wait_for_timeout(2000)

    page.keyboard.press("Enter")

    page.wait_for_timeout(3000)

    message_box = page.locator('[contenteditable="true"]').last

    message_box.fill(MESSAGE)

    page.keyboard.press("Enter")

    print("Message sent.")

    time.sleep(10)