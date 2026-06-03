import os
# pyrefly: ignore [missing-import]
from playwright.sync_api import sync_playwright

def run_browser_agent(recipient_name: str, message_text: str):
    print("\nLaunching browser to send scheduled message...")
    
    session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions", "facebook")

    # Confirming headless mode work
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=session_dir,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page()

        print("Navigating to Facebook Messages...")
        page.goto("https://www.facebook.com/messages")
        
        page.wait_for_timeout(7000)

        print(f"Searching for {recipient_name}...")
        search_box = page.locator('input[placeholder="Search Messenger"]')
        search_box.click()
        search_box.fill(recipient_name)
        page.wait_for_timeout(4000) 

        print(f"Attempting to click the contact row for {recipient_name}...")
        
        contact_row = page.locator(f'ul[role="listbox"] >> text="{recipient_name}"').first
        
        if contact_row.is_visible():
            contact_row.click()
        else:
            # Find ANY visible text block matching their name on the screen and click it
            page.get_by_text(recipient_name).first.click()
            
        page.wait_for_timeout(5000) 

        print(f"✉️ Typing message: {message_text}")
        message_box = page.locator('div[role="textbox"][aria-label="Message"], div[contenteditable="true"]').first
        
        message_box.click()
        message_box.fill(message_text)
        page.wait_for_timeout(1000)
        
        print("Sending...")
        page.keyboard.press("Enter")
        print("Message successfully sent!")

        page.wait_for_timeout(5000)
        browser.close()