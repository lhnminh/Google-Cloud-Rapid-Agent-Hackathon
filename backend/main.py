# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.responses import FileResponse
# pyrefly: ignore [missing-import]
from pydantic import BaseModel
import os
import sys
import threading
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from main_agent import main_agent
from gcs_session import download_session, upload_session

SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions", "facebook")
login_state = {"status": "idle"}  # "idle" | "pending" | "success"

GCS_BUCKET = os.environ.get("GCS_SESSION_BUCKET")  # None means GCS sync is disabled
IS_DOCKER = os.environ.get("IS_DOCKER") == "true"

app = FastAPI()

FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "../frontend/index.html")


def _flag_path():
    return os.path.join(SESSION_DIR, "logged_in.flag")


def _has_visible_control_in_lower_screen(page, selectors, excluded_terms=None):
    excluded_terms = excluded_terms or []
    viewport = page.viewport_size or {"width": 1280, "height": 900}
    min_y = viewport["height"] * 0.45

    for selector in selectors:
        locator = page.locator(selector)
        for index in range(locator.count()):
            candidate = locator.nth(index)
            try:
                if not candidate.is_visible(timeout=1000):
                    continue

                label_parts = [
                    candidate.get_attribute("aria-label", timeout=1000) or "",
                    candidate.get_attribute("aria-placeholder", timeout=1000) or "",
                    candidate.get_attribute("placeholder", timeout=1000) or "",
                    candidate.inner_text(timeout=1000) or "",
                ]
                label_text = " ".join(label_parts).lower()
                if any(term in label_text for term in excluded_terms):
                    continue

                box = candidate.bounding_box(timeout=1000)
                if not box:
                    continue

                center_y = box["y"] + (box["height"] / 2)
                if center_y >= min_y:
                    return True
            except Exception:
                continue

    return False


def _page_has_messenger_ready_controls(page):
    current_url = page.url
    if "facebook.com/messages" not in current_url:
        return False
    if "login" in current_url or "checkpoint" in current_url:
        return False

    textbox_selectors = [
        'div[role="textbox"]',
        'div[contenteditable="true"]',
    ]
    send_selectors = [
        'div[aria-label="Send"][role="button"]',
        'div[aria-label*="Send"][role="button"]',
        'button[aria-label="Send"]',
        'button[aria-label*="Send"]',
    ]

    has_message_textbox = _has_visible_control_in_lower_screen(
        page,
        textbox_selectors,
        excluded_terms=["search", "comment"],
    )
    has_send_button = _has_visible_control_in_lower_screen(page, send_selectors)
    return has_message_textbox and has_send_button


def _verify_existing_session():
    """Background check on startup to verify if the saved session is actually valid."""
    if not os.path.exists(_flag_path()):
        return

    print("Verifying existing Facebook session in the background...")
    # pyrefly: ignore [missing-import]
    from playwright.sync_api import sync_playwright

    logged_in = False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=SESSION_DIR,
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            page = browser.new_page()
            page.goto("https://www.facebook.com/messages")
            
            # Wait up to 10 seconds for Messenger composer controls to load.
            for _ in range(5):
                page.wait_for_timeout(2000)
                if _page_has_messenger_ready_controls(page):
                    logged_in = True
                    break
            browser.close()
    except Exception as e:
        print(f"Error during background session verification: {e}")
        logged_in = False

    if not logged_in:
        print("Facebook session is invalid or expired. Removing logged_in.flag.")
        try:
            flag_path = _flag_path()
            if os.path.exists(flag_path):
                os.remove(flag_path)
        except Exception as e:
            print(f"Error removing flag file: {e}")
    else:
        print("Facebook session verified successfully!")


def _startup_task():
    if GCS_BUCKET:
        print(f"Downloading session from GCS bucket: {GCS_BUCKET}")
        download_session(GCS_BUCKET, SESSION_DIR)
    _verify_existing_session()


@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=_startup_task, daemon=True)
    thread.start()


@app.get("/config")
def config():
    return {"docker": IS_DOCKER}


@app.get("/")
def serve_frontend():
    return FileResponse(FRONTEND_PATH)


@app.get("/login/status")
def login_status():
    if os.path.exists(_flag_path()):
        return {"logged_in": True, "pending": False}
    if login_state["status"] == "pending":
        return {"logged_in": False, "pending": True}
    return {"logged_in": False, "pending": False}


def _run_login():
    """Launch a visible browser, navigate to Facebook, auto-detect login, save session."""
    # pyrefly: ignore [missing-import]
    from playwright.sync_api import sync_playwright

    os.makedirs(SESSION_DIR, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page()
        page.goto("https://www.facebook.com/messages")

        try:
            # Wait a bit longer to ensure the DOM is fully interactive
            page.wait_for_timeout(3000) 
            
            # Specifically target the decline button
            decline_btn = page.get_by_role("button", name="Decline optional cookies", exact=False)
            
            if decline_btn.count() > 0:
                decline_btn.first.click()
                print("Successfully rejected optional cookies.")
            else:
                # If we don't see it, it might already be gone, or Facebook has changed the UI
                print("Decline button not found. Proceeding with login.")
                
        except Exception as e:
            # We don't want to crash the whole app just because we couldn't click a button
            print(f"Could not reject cookies automatically: {e}")

        timeout_seconds = 120
        interval = 2
        elapsed = 0
        logged_in = False

        while elapsed < timeout_seconds:
            page.wait_for_timeout(interval * 1000)
            elapsed += interval
            if _page_has_messenger_ready_controls(page):
                logged_in = True
                # Wait 5 seconds to ensure browser flushes authentication state/cookies to disk.
                page.wait_for_timeout(5000)
                break

        if logged_in:
            with open(_flag_path(), "w") as f:
                f.write("true")
            if GCS_BUCKET:
                print(f"Uploading session to GCS bucket: {GCS_BUCKET}")
                upload_session(GCS_BUCKET, SESSION_DIR)

        browser.close()

    login_state["status"] = "success" if logged_in else "idle"


@app.post("/login/start")
def login_start():
    if login_state["status"] == "pending":
        return {"started": False, "reason": "already in progress"}
    login_state["status"] = "pending"
    thread = threading.Thread(target=_run_login, daemon=True)
    thread.start()
    return {"started": True}


class SendMessageRequest(BaseModel):
    instruction: str


@app.post("/send-message")
async def send_message(request: SendMessageRequest):
    return main_agent(request.instruction)
