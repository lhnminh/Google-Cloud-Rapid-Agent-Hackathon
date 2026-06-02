# Facebook Login Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Facebook login step to the web UI so users authenticate before scheduling messages.

**Architecture:** `GET /login/status` checks for a saved session on disk; `POST /login/start` launches a local headless=False Playwright browser in a background thread and auto-detects login completion by polling the page URL. The frontend checks login status on load and shows a login panel or chat UI accordingly.

**Tech Stack:** Python 3, FastAPI, Playwright (sync API), threading, HTML/CSS/JS (vanilla)

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Modify | `backend/main.py` | Add `login_state`, `/login/status`, `/login/start` endpoints |
| Modify | `frontend/index.html` | Add login panel HTML/CSS, on-load status check, polling JS |

---

## Task 1: Add login state and `/login/status` endpoint to backend

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Add login_state and SESSION_DIR to main.py**

Open `backend/main.py` and add these lines after the existing imports and before `app = FastAPI()`:

```python
import threading

SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions", "facebook")
login_state = {"status": "idle"}  # "idle" | "pending" | "success"
```

- [ ] **Step 2: Add `/login/status` endpoint**

Add this endpoint to `backend/main.py` after the existing `serve_frontend` route:

```python
@app.get("/login/status")
def login_status():
    if os.path.isdir(SESSION_DIR) and any(os.scandir(SESSION_DIR)):
        return {"logged_in": True, "pending": False}
    if login_state["status"] == "pending":
        return {"logged_in": False, "pending": True}
    return {"logged_in": False, "pending": False}
```

- [ ] **Step 3: Write tests for `/login/status`**

Create `test/test_login_status.py`:

```python
import os
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient

# Patch SESSION_DIR before importing main
import backend.main as main_module

@pytest.fixture(autouse=True)
def reset_state():
    main_module.login_state["status"] = "idle"
    yield

def test_login_status_no_session(tmp_path):
    original = main_module.SESSION_DIR
    main_module.SESSION_DIR = str(tmp_path / "facebook")
    client = TestClient(main_module.app)

    response = client.get("/login/status")
    assert response.status_code == 200
    assert response.json() == {"logged_in": False, "pending": False}

    main_module.SESSION_DIR = original


def test_login_status_with_session(tmp_path):
    original = main_module.SESSION_DIR
    session_dir = tmp_path / "facebook"
    session_dir.mkdir()
    (session_dir / "Default").mkdir()  # non-empty

    main_module.SESSION_DIR = str(session_dir)
    client = TestClient(main_module.app)

    response = client.get("/login/status")
    assert response.status_code == 200
    assert response.json()["logged_in"] is True

    main_module.SESSION_DIR = original


def test_login_status_pending(tmp_path):
    original = main_module.SESSION_DIR
    main_module.SESSION_DIR = str(tmp_path / "facebook")
    main_module.login_state["status"] = "pending"
    client = TestClient(main_module.app)

    response = client.get("/login/status")
    assert response.status_code == 200
    data = response.json()
    assert data["logged_in"] is False
    assert data["pending"] is True

    main_module.SESSION_DIR = original
```

- [ ] **Step 4: Run tests**

```bash
cd /c/Users/VHV/Documents/Minh/Google-Cloud-Rapid-Agent-Hackathon
python -m pytest test/test_login_status.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py test/test_login_status.py
git commit -m "feat: add /login/status endpoint with session dir check"
```

---

## Task 2: Add `/login/start` endpoint to backend

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Add the background login function**

Add this function to `backend/main.py` (before the endpoint definitions):

```python
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
```

- [ ] **Step 2: Add `/login/start` endpoint**

Add this endpoint to `backend/main.py`:

```python
@app.post("/login/start")
def login_start():
    if login_state["status"] == "pending":
        return {"started": False, "reason": "already in progress"}
    login_state["status"] = "pending"
    thread = threading.Thread(target=_run_login, daemon=True)
    thread.start()
    return {"started": True}
```

- [ ] **Step 3: Write test for idempotency**

Add to `test/test_login_status.py`:

```python
def test_login_start_idempotent(tmp_path):
    original = main_module.SESSION_DIR
    main_module.SESSION_DIR = str(tmp_path / "facebook")
    main_module.login_state["status"] = "pending"
    client = TestClient(main_module.app)

    response = client.post("/login/start")
    assert response.status_code == 200
    assert response.json()["started"] is False

    main_module.SESSION_DIR = original
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest test/test_login_status.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py test/test_login_status.py
git commit -m "feat: add /login/start endpoint with background Playwright login"
```

---

## Task 3: Add login panel to frontend

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Add login panel CSS**

Inside the `<style>` block in `frontend/index.html`, add these rules before the closing `</style>` tag:

```css
/* Login panel */
#login-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  max-width: 720px;
  gap: 16px;
  padding: 16px;
}

#login-panel h2 {
  font-size: 1.6rem;
  font-weight: 600;
  color: #ffffff;
  text-align: center;
}

#login-panel p {
  font-size: 0.85rem;
  color: #666;
  text-align: center;
}

#login-status {
  font-size: 0.8rem;
  color: #aaa;
  text-align: center;
  display: none;
}

body.active #login-panel {
  display: none;
}
```

- [ ] **Step 2: Add login panel HTML**

In `frontend/index.html`, add the login panel div immediately before `<div id="center-wrap">`:

```html
<!-- Login panel — shown when no Facebook session exists -->
<div id="login-panel">
  <h2>forgetText</h2>
  <p>Connect your Facebook account to start scheduling messages.</p>
  <button id="connect-btn">Connect Facebook</button>
  <span id="login-status">Browser opened — please log in to Facebook in the window that just appeared...</span>
</div>
```

- [ ] **Step 3: Add login JS**

In the `<script>` block of `frontend/index.html`, add this code before the existing event listeners:

```js
const loginPanel = document.getElementById('login-panel');
const connectBtn = document.getElementById('connect-btn');
const loginStatusEl = document.getElementById('login-status');

// On load: check if already logged in
(async function checkLoginOnLoad() {
  const res = await fetch('/login/status');
  const data = await res.json();
  if (data.logged_in) {
    loginPanel.style.display = 'none';
  } else {
    // Hide chat UI elements until logged in
    document.getElementById('center-wrap').style.display = 'none';
  }
})();

// Poll until logged in
function pollLoginStatus() {
  let succeeded = false;

  const interval = setInterval(async () => {
    const res = await fetch('/login/status');
    const data = await res.json();
    if (data.logged_in) {
      succeeded = true;
      clearInterval(interval);
      loginPanel.style.display = 'none';
      document.getElementById('center-wrap').style.display = '';
    }
  }, 2000);

  // Stop polling after 130s and show retry message if not yet succeeded
  setTimeout(() => {
    clearInterval(interval);
    if (!succeeded) {
      loginStatusEl.textContent = 'Login timed out. Please try again.';
      connectBtn.disabled = false;
    }
  }, 130000);
}

connectBtn.addEventListener('click', async () => {
  connectBtn.disabled = true;
  loginStatusEl.style.display = 'block';
  await fetch('/login/start', { method: 'POST' });
  pollLoginStatus();
});
```

- [ ] **Step 4: Manual test — no session**

1. Delete `backend/sessions/facebook/` if it exists
2. Start the server: `uvicorn backend.main:app --reload`
3. Open `http://localhost:8000`
4. Expected: login panel is shown with "Connect Facebook" button; chat UI is hidden

- [ ] **Step 5: Manual test — existing session**

1. Create a non-empty dummy session dir: `mkdir -p backend/sessions/facebook/Default`
2. Restart the server and open `http://localhost:8000`
3. Expected: login panel is skipped, chat UI shows immediately
4. Clean up: `rm -rf backend/sessions/facebook/Default`

- [ ] **Step 6: Manual test — full login flow**

1. Delete `backend/sessions/facebook/`
2. Start the server
3. Click "Connect Facebook" — browser should open and navigate to Facebook
4. Log in to Facebook in the browser window
5. Within ~2s of inbox loading, the web UI should transition to the chat UI automatically

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add Facebook login panel to frontend with auto-detect polling"
```
