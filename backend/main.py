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

SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions", "facebook")
FLAG_PATH = os.path.join(SESSION_DIR, "logged_in.flag")
login_state = {"status": "idle"}  # "idle" | "pending" | "success"

app = FastAPI()

FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "../frontend/index.html")


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
                    
                    # Also look for search bar or active chats navigation
                    has_search = page.locator('input[placeholder*="Search"], input[placeholder*="search"], input[placeholder*="Messenger"]').count() > 0
                    has_chats = page.locator('[role="navigation"], [role="grid"], [role="main"]').count() > 0
                    
                    # Detect if a PIN prompt is currently on screen
                    has_pin_prompt = "Enter your PIN" in page.content() or "PIN" in page.content()
                    
                    # We are logged in if:
                    # - The encryption restored text has appeared, OR
                    # - Messenger UI is visible and there is no pending PIN entry prompt
                    if has_restored_signal or (has_search and has_chats and not has_pin_prompt):
                        logged_in = True
                        # Wait 5 seconds to ensure browser flushes authentication state/cookies to disk
                        page.wait_for_timeout(5000)
                        break
                except Exception:
                    pass

        if logged_in:
            with open(FLAG_PATH, "w") as f:
                f.write("true")

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
