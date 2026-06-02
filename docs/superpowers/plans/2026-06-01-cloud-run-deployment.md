# Cloud Run Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the forgetText FastAPI + Playwright app to Google Cloud Run with Facebook session persistence via Cloud Storage.

**Architecture:** FastAPI serves the UI and schedules jobs via APScheduler BackgroundScheduler running inside a single Cloud Run instance (min=1). The Playwright browser runs headless inside the container. Facebook session files are stored in a GCS bucket and synced to `/tmp/sessions/facebook/` before each send.

**Tech Stack:** Python 3.11, FastAPI, Playwright (headless Chromium), APScheduler BackgroundScheduler, google-cloud-storage, Docker (`mcr.microsoft.com/playwright/python:v1.45.0-jammy`), Google Cloud Run, Google Cloud Storage

---

## Pre-requisites

- Google Cloud project with billing enabled
- `gcloud` CLI installed and authenticated (`gcloud auth login`)
- Docker installed locally
- A GCS bucket name chosen (e.g. `forgottext-sessions`)
- The Facebook session directory currently lives at `./sessions/facebook/` locally (from prior login)

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Modify | `requirements.txt` | Add `google-cloud-storage`, remove unused deps |
| Create | `backend/session_store.py` | GCS download/upload of session tarball |
| Modify | `backend/browser_agent.py` | headless=True, /tmp path, GCS sync |
| Modify | `backend/main.py` | Fix import, wire Gemini→scheduler→browser |
| Create | `scripts/upload_session.py` | One-time local script: zip & upload session to GCS |
| Create | `Dockerfile` | Playwright base image, app setup |
| Create | `.dockerignore` | Exclude venv, sessions, .env, test dirs |

---

## Task 1: Fix requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Replace requirements.txt content**

```
fastapi>=0.111.0
uvicorn>=0.30.0
httpx>=0.27.0
python-dotenv>=1.0.0
google-genai
playwright
apscheduler
google-cloud-storage
```

Remove: `streamlit`, `browser-use`, `langchain-anthropic`, `pytest`, `pytest-asyncio` (not needed in the container; add back to a `requirements-dev.txt` if desired).

- [ ] **Step 2: Verify locally (optional)**

```bash
pip install -r requirements.txt
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: slim requirements.txt for Cloud Run"
```

---

## Task 2: Create backend/session_store.py

**Files:**
- Create: `backend/session_store.py`

This module handles syncing the Playwright persistent context directory to/from GCS as a `.tar.gz` file.

- [ ] **Step 1: Create the file**

```python
import os
import tarfile
import tempfile
from google.cloud import storage

SESSION_BLOB_NAME = "sessions/facebook.tar.gz"
LOCAL_SESSION_DIR = "/tmp/sessions/facebook"


def download_session(bucket_name: str) -> bool:
    """Download session tarball from GCS and extract to LOCAL_SESSION_DIR.
    Returns True if session was found and extracted, False if not found."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(SESSION_BLOB_NAME)

    if not blob.exists():
        return False

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        blob.download_to_filename(tmp.name)
        with tarfile.open(tmp.name, "r:gz") as tar:
            tar.extractall("/tmp/sessions/")

    os.unlink(tmp.name)
    return True


def upload_session(bucket_name: str) -> None:
    """Compress LOCAL_SESSION_DIR and upload to GCS."""
    if not os.path.exists(LOCAL_SESSION_DIR):
        return

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        with tarfile.open(tmp.name, "w:gz") as tar:
            tar.add(LOCAL_SESSION_DIR, arcname="facebook")
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(SESSION_BLOB_NAME)
        blob.upload_from_filename(tmp.name)

    os.unlink(tmp.name)
```

- [ ] **Step 2: Commit**

```bash
git add backend/session_store.py
git commit -m "feat: add GCS session store for Playwright"
```

---

## Task 3: Update backend/browser_agent.py

**Files:**
- Modify: `backend/browser_agent.py`

Changes: headless=True, session path → `/tmp/sessions/facebook`, sync session from/to GCS.

- [ ] **Step 1: Replace the file**

```python
import os
import time
from playwright.sync_api import sync_playwright
from backend.session_store import download_session, upload_session

SESSION_DIR = "/tmp/sessions/facebook"


def run_browser_agent(recipient_name: str, message_text: str, bucket_name: str):
    print(f"\nSyncing session from GCS bucket '{bucket_name}'...")
    found = download_session(bucket_name)
    if not found:
        raise RuntimeError(
            f"No session found in GCS bucket '{bucket_name}'. "
            "Run scripts/upload_session.py locally first."
        )

    print("Launching headless browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page()

        print("Navigating to Facebook Messages...")
        page.goto("https://www.facebook.com/messages")
        page.wait_for_load_state("networkidle", timeout=30000)

        print(f"Searching for {recipient_name}...")
        search_box = page.locator('input[placeholder="Search Messenger"]')
        search_box.click()
        search_box.fill(recipient_name)
        page.wait_for_timeout(4000)

        contact_row = page.locator(f'ul[role="listbox"] >> text="{recipient_name}"').first
        if contact_row.is_visible():
            contact_row.click()
        else:
            page.get_by_text(recipient_name).first.click()

        page.wait_for_load_state("networkidle", timeout=15000)

        print(f"Typing message: {message_text}")
        message_box = page.locator(
            'div[role="textbox"][aria-label="Message"], div[contenteditable="true"]'
        ).first
        message_box.click()
        message_box.fill(message_text)
        page.wait_for_timeout(1000)

        print("Sending...")
        page.keyboard.press("Enter")
        page.wait_for_timeout(3000)
        browser.close()

    print("Syncing updated session back to GCS...")
    upload_session(bucket_name)
    print("Done.")
```

- [ ] **Step 2: Commit**

```bash
git add backend/browser_agent.py
git commit -m "feat: headless browser agent with GCS session sync"
```

---

## Task 4: Update backend/main.py

**Files:**
- Modify: `backend/main.py`

Changes: fix broken import, wire Gemini → json parse → BackgroundScheduler → browser agent.

- [ ] **Step 1: Replace the file**

```python
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.browser_agent import run_browser_agent
from backend.text_function import extract_schedule_details

FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "../frontend/index.html")
GCS_BUCKET = os.environ.get("GCS_BUCKET_NAME", "")

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)


@app.get("/")
def serve_frontend():
    return FileResponse(FRONTEND_PATH)


class SendMessageRequest(BaseModel):
    instruction: str


@app.post("/send-message")
async def send_message(request: SendMessageRequest):
    raw = extract_schedule_details(request.instruction)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "failed", "message": f"Could not parse AI response: {raw}", "clarification": ""}

    recipient = data.get("recipient", "unknown")
    message = data.get("message", "")
    execution_time = data.get("execution_time", "")

    try:
        run_date = datetime.strptime(execution_time, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return {
            "status": "failed",
            "message": f"Could not parse execution time: {execution_time}",
            "clarification": "",
        }

    scheduler.add_job(
        run_browser_agent,
        "date",
        run_date=run_date,
        args=[recipient, message, GCS_BUCKET],
    )

    return {
        "status": "sent",
        "message": f"Scheduled! Will message {recipient} at {execution_time}: \"{message}\"",
        "clarification": "",
    }
```

- [ ] **Step 2: Commit**

```bash
git add backend/main.py
git commit -m "feat: wire Gemini parser to BackgroundScheduler in FastAPI"
```

---

## Task 5: Create scripts/upload_session.py

**Files:**
- Create: `scripts/upload_session.py`

This is a **local-only** script run once to upload an existing Facebook session directory to GCS. Run it before deploying to Cloud Run.

- [ ] **Step 1: Create the file**

```python
"""
One-time setup: upload local Playwright Facebook session to GCS.

Usage:
    python scripts/upload_session.py --bucket YOUR_BUCKET_NAME --session ./sessions/facebook
"""
import argparse
import os
import tarfile
import tempfile

from google.cloud import storage

SESSION_BLOB_NAME = "sessions/facebook.tar.gz"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True, help="GCS bucket name")
    parser.add_argument("--session", default="./sessions/facebook", help="Local session directory path")
    args = parser.parse_args()

    session_dir = os.path.abspath(args.session)
    if not os.path.isdir(session_dir):
        print(f"ERROR: Session directory not found: {session_dir}")
        print("Run main_agent.py locally first to log in and save the session.")
        raise SystemExit(1)

    print(f"Compressing {session_dir}...")
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        with tarfile.open(tmp.name, "w:gz") as tar:
            tar.add(session_dir, arcname="facebook")
        tmp_path = tmp.name

    print(f"Uploading to gs://{args.bucket}/{SESSION_BLOB_NAME}...")
    client = storage.Client()
    bucket = client.bucket(args.bucket)
    blob = bucket.blob(SESSION_BLOB_NAME)
    blob.upload_from_filename(tmp_path)
    os.unlink(tmp_path)

    print("Done. Session uploaded successfully.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create scripts/__init__.py (empty)**

```bash
touch scripts/__init__.py
```

- [ ] **Step 3: Commit**

```bash
git add scripts/
git commit -m "feat: add one-time session upload script for GCS"
```

---

## Task 6: Create Dockerfile

**Files:**
- Create: `Dockerfile`

Uses the official Playwright Python image which ships with Chromium pre-installed.

- [ ] **Step 1: Create the file**

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 2: Commit**

```bash
git add Dockerfile
git commit -m "feat: add Dockerfile for Cloud Run"
```

---

## Task 7: Create .dockerignore

**Files:**
- Create: `.dockerignore`

- [ ] **Step 1: Create the file**

```
.venv/
sessions/
.env
__pycache__/
*.pyc
*.pyo
test/
tests/
scripts/
docs/
.git/
.claude/
*.md
```

- [ ] **Step 2: Commit**

```bash
git add .dockerignore
git commit -m "chore: add .dockerignore"
```

---

## Task 8: Build and Deploy to Cloud Run

This task uses `gcloud` CLI commands. Replace placeholders:
- `PROJECT_ID` → your Google Cloud project ID
- `REGION` → e.g. `us-central1`
- `BUCKET_NAME` → e.g. `forgottext-sessions`
- `SERVICE_NAME` → e.g. `forgottext`

- [ ] **Step 1: Set gcloud project**

```bash
gcloud config set project PROJECT_ID
```

- [ ] **Step 2: Enable required APIs**

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com storage.googleapis.com
```

- [ ] **Step 3: Create GCS bucket**

```bash
gsutil mb -l REGION gs://BUCKET_NAME
```

- [ ] **Step 4: Upload Facebook session to GCS**

Do this step with the local session from `./sessions/facebook/`. You must have already logged in locally (via `main_agent.py`) so the session directory exists.

```bash
python scripts/upload_session.py --bucket BUCKET_NAME --session ./sessions/facebook
```

Expected output:
```
Compressing ./sessions/facebook...
Uploading to gs://BUCKET_NAME/sessions/facebook.tar.gz...
Done. Session uploaded successfully.
```

- [ ] **Step 5: Create Artifact Registry Docker repository**

```bash
gcloud artifacts repositories create forgottext \
  --repository-format=docker \
  --location=REGION
```

- [ ] **Step 6: Configure Docker auth**

```bash
gcloud auth configure-docker REGION-docker.pkg.dev
```

- [ ] **Step 7: Build and push Docker image**

```bash
docker build -t REGION-docker.pkg.dev/PROJECT_ID/forgottext/app:latest .
docker push REGION-docker.pkg.dev/PROJECT_ID/forgottext/app:latest
```

Expected: image builds and pushes without error. Build will take 3-5 minutes on first run (downloading Playwright base image ~1.5GB).

- [ ] **Step 8: Grant Cloud Run service account access to GCS bucket**

```bash
PROJECT_NUMBER=$(gcloud projects describe PROJECT_ID --format='value(projectNumber)')
gsutil iam ch serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com:roles/storage.objectAdmin gs://BUCKET_NAME
```

- [ ] **Step 9: Deploy to Cloud Run**

```bash
gcloud run deploy SERVICE_NAME \
  --image REGION-docker.pkg.dev/PROJECT_ID/forgottext/app:latest \
  --region REGION \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 1 \
  --memory 2Gi \
  --cpu 1 \
  --set-env-vars "GEMINI_API_KEY=YOUR_GEMINI_KEY,GCS_BUCKET_NAME=BUCKET_NAME"
```

Notes:
- `--min-instances 1` keeps one instance alive so APScheduler doesn't get killed before firing scheduled jobs
- `--max-instances 1` prevents duplicate job execution across multiple instances
- `2Gi` memory is needed for headless Chromium
- `GEMINI_API_KEY` should eventually be moved to Secret Manager for production

Expected output ends with:
```
Service [SERVICE_NAME] revision [...] has been deployed and is serving 100 percent of traffic.
Service URL: https://SERVICE_NAME-xxxx-uc.a.run.app
```

- [ ] **Step 10: Smoke test**

Open the Service URL in a browser. Type a message like:

> "Send John a reminder about our meeting tomorrow at 3pm"

Expected chat response: `Scheduled! Will message John at 2026-06-02 15:00:00: "..."`

---

## Known Limitations (acceptable for hackathon)

1. **Single instance only:** APScheduler lives in-process. If the Cloud Run instance restarts between scheduling and execution, the job is lost. For production, use Cloud Scheduler + Cloud Run Jobs.
2. **Facebook session expiry:** Sessions eventually expire. Re-run `scripts/upload_session.py` when the session is stale.
3. **Headless detection:** Facebook may occasionally block headless Chromium. If sends fail, add `--user-agent` flag or use a custom UA string in `browser_agent.py`.
4. **GEMINI_API_KEY in env var:** Move to Secret Manager before sharing the Cloud Run URL publicly.
