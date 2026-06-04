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
FLAG_PATH = os.path.join(SESSION_DIR, "logged_in.flag")
login_state = {"status": "idle"}  # "idle" | "pending" | "success"

GCS_BUCKET = os.environ.get("GCS_SESSION_BUCKET")  # None means GCS sync is disabled

app = FastAPI()

FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "../frontend/index.html")


def _verify_existing_session():
    """Background check on startup to verify if the saved session is actually valid."""
    if not os.path.exists(FLAG_PATH):
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
            
            # Wait up to 10 seconds for standard inbox indicators to load
            for _ in range(5):
                page.wait_for_timeout(2000)
                current_url = page.url
                if "facebook.com/messages" in current_url and "login" not in current_url and "checkpoint" not in current_url:
                    has_restored_signal = page.get_by_text("End-to-end encrypted messages restored").count() > 0 or "encrypted messages restored" in page.content() or "End-to-end encrypted" in page.content()
                    has_encrypted_link = "https://www.facebook.com/help/messenger-app/786613221989782/" in page.content() or "786613221989782" in page.content()
                    has_search = page.locator('input[placeholder*="Search"], input[placeholder*="search"], input[placeholder*="Messenger"]').count() > 0
                    has_chats = page.locator('[role="navigation"], [role="grid"], [role="main"]').count() > 0
                    has_pin_prompt = "Enter your PIN" in page.content() or "PIN" in page.content()
                    
                    if has_restored_signal or has_encrypted_link or (has_search and has_chats and not has_pin_prompt):
                        logged_in = True
                        break
            browser.close()
    except Exception as e:
        print(f"Error during background session verification: {e}")
        logged_in = False

    if not logged_in:
        print("Facebook session is invalid or expired. Removing logged_in.flag.")
        try:
            if os.path.exists(FLAG_PATH):
                os.remove(FLAG_PATH)
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


@app.get("/")
def serve_frontend():
    return FileResponse(FRONTEND_PATH)


@app.get("/login/status")
def login_status():
    if os.path.exists(FLAG_PATH):
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
        )
        page = browser.new_page()
        page.goto("https://www.facebook.com/messages")

        timeout_seconds = 120
        interval = 2
        elapsed = 0
        logged_in = False

        while elapsed < timeout_seconds:
            page.wait_for_timeout(interval * 1000)
            elapsed += interval
            current_url = page.url
            # 1. Must be on facebook.com/messages
            # 2. Must not be in any login or 2FA/PIN verification flow (e.g., checkpoint)
            if "facebook.com/messages" in current_url and "login" not in current_url and "checkpoint" not in current_url:
                # 3. Double-check that standard Messenger elements are rendered to ensure we are logged in
                try:
                    # Check if the explicit encryption restoration signal has appeared
                    has_restored_signal = page.get_by_text("End-to-end encrypted messages restored").count() > 0 or "encrypted messages restored" in page.content()
                    has_encrypted_link = "https://www.facebook.com/help/messenger-app/786613221989782/" in page.content() or "786613221989782" in page.content()
                    
                    # Also look for search bar or active chats navigation
                    has_search = page.locator('input[placeholder*="Search"], input[placeholder*="search"], input[placeholder*="Messenger"]').count() > 0
                    has_chats = page.locator('[role="navigation"], [role="grid"], [role="main"]').count() > 0
                    
                    # Detect if a PIN prompt is currently on screen
                    has_pin_prompt = "Enter your PIN" in page.content() or "PIN" in page.content()
                    
                    # We are logged in if:
                    # - The encryption restored text has appeared, OR
                    # - The encryption learn-more link is present, OR
                    # - Messenger UI is visible and there is no pending PIN entry prompt
                    if has_restored_signal or has_encrypted_link or (has_search and has_chats and not has_pin_prompt):
                        logged_in = True
                        # Wait 5 seconds to ensure browser flushes authentication state/cookies to disk
                        page.wait_for_timeout(5000)
                        break
                except Exception:
                    pass

        if logged_in:
            with open(FLAG_PATH, "w") as f:
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
