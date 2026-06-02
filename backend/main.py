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
login_state = {"status": "idle"}  # "idle" | "pending" | "success"

app = FastAPI()

FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "../frontend/index.html")


@app.get("/")
def serve_frontend():
    return FileResponse(FRONTEND_PATH)


@app.get("/login/status")
def login_status():
    if os.path.isdir(SESSION_DIR) and any(os.scandir(SESSION_DIR)):
        return {"logged_in": True, "pending": False}
    if login_state["status"] == "pending":
        return {"logged_in": False, "pending": True}
    return {"logged_in": False, "pending": False}


def _run_login():
    """Launch a visible browser, navigate to Facebook, auto-detect login, save session."""
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
            if "facebook.com" in current_url and "/login" not in current_url:
                logged_in = True
                break

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
