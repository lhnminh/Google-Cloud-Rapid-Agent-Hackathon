# Facebook Login Flow — Design Spec

**Date:** 2026-06-02
**Status:** Approved

## Problem

The current app requires a Facebook session to already exist locally before scheduling messages. The login step (`verify_login_session`) only runs from the terminal. Users have no way to log in through the web UI.

## Goal

Add a login step to the web app: users connect their Facebook account first, then access the scheduling chat. Works locally (and via Cloud Run with a pre-uploaded GCS session).

---

## Architecture

### Flow

1. App loads → `GET /login/status` → session exists? → skip login, show chat
2. No session → show login panel
3. User clicks "Connect Facebook" → `POST /login/start` → backend launches Playwright (`headless=False`) in a background thread
4. Frontend polls `GET /login/status` every 2s
5. Backend detects inbox loaded (URL contains `facebook.com/messages` and no login form) → closes browser → sets status to `success`
6. Frontend gets `{"logged_in": true}` → hides login panel → shows chat UI

---

## Backend

**File:** `backend/main.py` (additions only)

### State

A module-level dict tracks login state:

```python
login_state = {"status": "idle"}  # "idle" | "pending" | "success"
```

### `GET /login/status`

- Checks if `backend/sessions/facebook/` exists and is non-empty → `{"logged_in": true}`
- If login is in progress (`status == "pending"`) → `{"logged_in": false, "pending": true}`
- Otherwise → `{"logged_in": false, "pending": false}`

### `POST /login/start`

- If status is already `"pending"`, returns immediately (idempotent)
- Sets `login_state["status"] = "pending"`
- Launches a background thread running the adapted login function:
  - Opens Playwright with `headless=False`, persistent context at `backend/sessions/facebook/`
  - Navigates to `facebook.com/messages`
  - Polls `page.url` every 2s (up to 120s timeout)
  - Success condition: URL contains `facebook.com/messages` AND no element matching `[data-testid="royal_login_button"]` is visible
  - On success: closes browser, sets `login_state["status"] = "success"`
  - On timeout: sets `login_state["status"] = "idle"` (allows retry)

### Reuse

`verify_login_session()` in `main_agent.py` is the basis — the `input()` call is replaced with the URL polling loop.

---

## Frontend

**File:** `frontend/index.html` (additions only)

### New login panel (inline, same file)

```
┌─────────────────────────────────────────┐
│                                         │
│           forgetText                    │
│                                         │
│   Connect your Facebook account to      │
│   start scheduling messages.            │
│                                         │
│        [ Connect Facebook ]             │
│                                         │
│   ← status line (hidden until clicked)  │
│                                         │
└─────────────────────────────────────────┘
```

### States

| Body class | Visible |
|---|---|
| *(none)* | Login panel |
| `active` | Chat UI (existing) |

The status line within the login panel is toggled via JS (show/hide), not a body class.

### On page load

```js
fetch('/login/status')
  → logged_in: true  → body.classList.add('active')
  → logged_in: false → show login panel (default)
```

### On "Connect Facebook" click

1. `POST /login/start`
2. Disable button, show status: *"Browser opened — please log in to Facebook in the window that just appeared..."*
3. Poll `GET /login/status` every 2s
4. On `logged_in: true`: `body.classList.add('active')` (hides login panel, shows chat)
5. On timeout (>120s without success): re-enable button, show error: *"Login timed out. Please try again."*

---

## Error Cases

| Scenario | Behavior |
|---|---|
| `/login/start` called while already pending | Returns 200, no-op |
| Login times out (120s) | Status resets to idle, frontend shows retry message |
| Session directory exists but is corrupted | `GET /login/status` returns `logged_in: false` (directory must be non-empty) |

---

## Out of Scope

- Cloud Run login (session is uploaded to GCS separately via `scripts/upload_session.py`)
- Logout / session invalidation
- Multi-user support
