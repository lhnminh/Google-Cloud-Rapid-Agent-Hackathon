import os
# pyrefly: ignore [missing-import]
from playwright.sync_api import sync_playwright


def _log_page_state(page, label: str):
    try:
        body_text = page.locator("body").inner_text(timeout=3000)
    except Exception:
        body_text = ""

    login_markers = [
        "Log in",
        "Forgot password",
        "Create new account",
        "checkpoint",
        "Enter your password",
    ]
    matched_markers = [marker for marker in login_markers if marker.lower() in body_text.lower()]
    print(
        f"[Browser state: {label}] url={page.url} title={page.title()!r} login_markers={matched_markers}",
        flush=True,
    )


def _log_locator_details(locator, label: str):
    try:
        aria_label = locator.get_attribute("aria-label", timeout=3000)
        role = locator.get_attribute("role", timeout=3000)
        text = locator.inner_text(timeout=3000).strip()
        print(
            f"[Locator: {label}] role={role!r} aria-label={aria_label!r} text={text[:120]!r}",
            flush=True,
        )
    except Exception as error:
        print(f"[Locator: {label}] could not read details: {error}", flush=True)


def _get_messenger_message_box(page):
    if "facebook.com/messages" not in page.url:
        raise RuntimeError(
            f"Not on a Messenger URL ({page.url}). Refusing to type into a generic Facebook textbox."
        )

    composer_selectors = [
        'div[role="textbox"][aria-label="Message"]',
        'div[role="textbox"][aria-label*="Message"]',
        'div[role="textbox"][aria-placeholder="Message"]',
        'div[role="textbox"][aria-placeholder*="Message"]',
        'div[contenteditable="true"][aria-label="Message"]',
        'div[contenteditable="true"][aria-label*="Message"]',
        'div[contenteditable="true"][aria-placeholder="Message"]',
        'div[contenteditable="true"][aria-placeholder*="Message"]',
        'div[contenteditable="true"][data-lexical-editor="true"]',
    ]

    for selector in composer_selectors:
        message_box = page.locator(selector).last
        if message_box.count() == 0:
            continue

        try:
            if message_box.is_visible(timeout=3000):
                print(f"Using Messenger composer selector: {selector}", flush=True)
                return message_box
        except Exception as error:
            print(f"Could not use Messenger composer selector {selector}: {error}", flush=True)

    raise RuntimeError(
        "Could not find a Messenger message composer on the Messenger URL."
    )


def _get_messenger_search_box(page):
    search_selectors = [
        'input[placeholder="Search Messenger"]',
        'input[aria-label="Search Messenger"]',
        'div[role="combobox"][aria-label="Search Messenger"]',
        'div[role="textbox"][aria-label="Search Messenger"]',
        'div[contenteditable="true"][aria-label="Search Messenger"]',
    ]

    for selector in search_selectors:
        search_box = page.locator(selector).first
        if search_box.count() == 0:
            continue

        try:
            if search_box.is_visible(timeout=3000):
                print(f"Using Messenger search selector: {selector}", flush=True)
                return search_box
        except Exception as error:
            print(f"Could not use Messenger search selector {selector}: {error}", flush=True)

    facebook_search = page.locator(
        'input[aria-label="Search Facebook"], input[placeholder="Search Facebook"], '
        'div[role="combobox"][aria-label="Search Facebook"]'
    ).first
    if facebook_search.count() > 0:
        _log_locator_details(facebook_search, "rejected Facebook search box")

    raise RuntimeError("Could not find the Search Messenger box. Refusing to use Search Facebook.")


def _click_messenger_contact(page, recipient_name: str):
    """Click the best matching Messenger search result."""
    result_selectors = [
        'ul[role="listbox"] [role="option"]',
        'div[role="listbox"] [role="option"]',
        '[role="dialog"] [role="option"]',
        '[role="button"]',
        'a[role="link"]',
    ]

    for selector in result_selectors:
        result = page.locator(selector).filter(has_text=recipient_name).first
        try:
            if result.count() > 0 and result.is_visible(timeout=3000):
                print(f"Clicking Messenger result using selector: {selector}", flush=True)
                result.click(force=True, timeout=5000)
                return
        except Exception as click_error:
            print(f"Could not click selector {selector}: {click_error}", flush=True)

    print("No clickable result container found. Pressing Enter as fallback.", flush=True)
    page.keyboard.press("Enter")


def _log_open_conversation(page, recipient_name: str):
    visible_matches = page.get_by_text(recipient_name, exact=False).count()
    print(
        f"Conversation page contains {visible_matches} visible text matches for '{recipient_name}'.",
        flush=True,
    )


def run_browser_agent(recipient_name: str, message_text: str):
    print("\nLaunching browser to send scheduled message...", flush=True)
    
    session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions", "facebook")

    # Confirming headless mode work
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=session_dir,
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page()

        print("Navigating to Facebook Messages...", flush=True)
        page.goto("https://www.facebook.com/messages")
        
        page.wait_for_timeout(7000)
        _log_page_state(page, "after navigation")

        print(f"Searching for {recipient_name}...", flush=True)
        search_box = _get_messenger_search_box(page)
        _log_locator_details(search_box, "search box")
        search_box.click()
        search_box.fill(recipient_name)
        page.wait_for_timeout(4000) 
        _log_page_state(page, "after search")

        print(f"Attempting to open contact row for {recipient_name}...", flush=True)
        _click_messenger_contact(page, recipient_name)
            
        page.wait_for_timeout(5000) 
        _log_page_state(page, "after contact click")
        _log_open_conversation(page, recipient_name)

        print(f"Typing message: {message_text}", flush=True)
        message_box = _get_messenger_message_box(page)
        _log_locator_details(message_box, "message box")
        
        message_box.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        message_box.type(message_text, delay=25)
        page.wait_for_timeout(1000)
        _log_page_state(page, "after typing")
        
        print("Sending...", flush=True)
        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)
        _log_page_state(page, "after enter")
        print("Message successfully sent!", flush=True)

        page.wait_for_timeout(5000)
        browser.close()
