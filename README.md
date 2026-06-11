# ForgetText

ForgetText is an AI message scheduler for Facebook Messenger. A user types a natural-language instruction such as "send Minh a reminder in 20 minutes", and the app parses the recipient, writes or extracts the message, schedules the job, and uses a real browser session to send it through Messenger.

Built for the Google Cloud Rapid Agent Hackathon, the project demonstrates an agentic workflow that combines Gemini on Vertex AI, FastAPI, Playwright browser automation, Cloud Run, and Google Cloud Storage.

## Demo Flow

1. Open the web app.
2. Connect a Facebook account once through the noVNC browser login flow.
3. Type a scheduling instruction in plain English.
4. Gemini extracts structured scheduling details and drafts the message when needed.
5. APScheduler queues the send job.
6. At the target time, Playwright opens Messenger with the saved session and sends the message.

Example prompts:

```text
Send Minh Ngoc "testing from Cloud Run" in 20 seconds
```

```text
Tell Alex happy birthday tomorrow at 9am
```

```text
Send Minh a summary of my GitLab issues at 5pm
```

The GitLab summary flow requires `GITLAB_PERSONAL_ACCESS_TOKEN`.

## What It Uses

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | HTML, CSS, JavaScript | Chat-style scheduling UI and Facebook login status flow |
| API | FastAPI | Serves the frontend and exposes `/login/*` and `/send-message` endpoints |
| Agent reasoning | Gemini 2.5 Flash on Vertex AI | Parses natural language into recipient, message, target time, and optional GitLab intent |
| Scheduler | APScheduler | Runs future message jobs inside the app process |
| Browser automation | Playwright Chromium | Reuses a saved Messenger session and sends the message |
| Session persistence | Google Cloud Storage | Stores the Facebook browser session for Cloud Run redeploys/restarts |
| Deployment | Docker, Artifact Registry, Cloud Run | Runs the app as a container with one warm instance for scheduled jobs |

## Architecture

```text
User
  |
  v
Frontend chat UI
  |
  v
FastAPI /send-message
  |
  v
Gemini on Vertex AI
  |
  v
APScheduler job
  |
  v
Playwright + saved Messenger session
  |
  v
Facebook Messenger
```

For Cloud Run, the Facebook session is downloaded from GCS on startup. Local Docker uses noVNC so the user can complete the first Facebook login inside the container; after login, the session is uploaded to GCS.

## Repository Map

```text
backend/main.py          FastAPI app, login endpoints, session verification
backend/main_agent.py    Agent orchestration and scheduling
backend/text_function.py Gemini parsing and optional GitLab summarization
backend/browser_agent.py Playwright Messenger automation
backend/gcs_session.py   GCS upload/download for Facebook session archive
frontend/index.html      Single-page web UI
entrypoint.sh            Docker startup for Xvfb, noVNC, and Uvicorn
CLOUD_DEPLOYMENT.md      End-to-end Cloud Run deployment guide
DEPLOY.md                Shorter local and deployment notes
```

## Local Run

Prerequisites:

- Docker Desktop
- Google Cloud CLI authenticated with access to the project
- `.env` containing:

```text
GCP_PROJECT_ID=xenon-depth-497608-a4
GCP_LOCATION=us-central1
GCS_SESSION_BUCKET=forgettext-sessions
```

Start the app:

```bash
docker compose up --build
```

Open:

```text
http://localhost:8080
```

For first-time Facebook login:

1. Click **Connect Facebook** in the app.
2. Open `http://localhost:6080/vnc.html`.
3. Log in to Facebook inside the noVNC browser.
4. Wait for the app to detect Messenger and upload the session to GCS.

Do not run `docker compose down -v` unless you want to delete the local Facebook session volume.

## Cloud Run Deploy

The deployed service must keep one instance alive and keep CPU allocated after requests, because scheduled jobs run inside the app process.

Build and push:

```bash
IMAGE="us-central1-docker.pkg.dev/xenon-depth-497608-a4/forgettext/app:latest"

docker buildx build \
  --platform linux/amd64 \
  -t "$IMAGE" \
  . \
  --push
```

Deploy:

```bash
gcloud run deploy forgettext \
  --image="$IMAGE" \
  --region=us-central1 \
  --project=xenon-depth-497608-a4 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=300 \
  --min-instances=1 \
  --no-cpu-throttling \
  --set-env-vars="GCP_PROJECT_ID=xenon-depth-497608-a4,GCP_LOCATION=us-central1,GCS_SESSION_BUCKET=forgettext-sessions,SEND_BROWSER_HEADLESS=true" \
  --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest"
```

Read logs:

```bash
gcloud run services logs read forgettext \
  --region=us-central1 \
  --project=xenon-depth-497608-a4 \
  --limit=100
```

More detailed deployment setup, IAM permissions, and troubleshooting are in [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md).

## Testing

```bash
uv run pytest -q
```

Current tests cover login status behavior, Messenger-ready detection, and scheduled browser headless configuration.

## Hackathon Notes

Why this is agentic:

- The user gives a goal in natural language rather than filling out a rigid form.
- Gemini converts that goal into structured execution data.
- The system schedules work for the future and executes it later without another user action.
- Playwright performs the final task in a real browser session, allowing automation of a consumer messaging surface that does not expose a simple scheduling API.

Why Google Cloud matters:

- Vertex AI provides the Gemini reasoning step.
- Cloud Run hosts the always-on containerized agent service.
- Cloud Storage persists browser session state across stateless Cloud Run instances.
- Artifact Registry stores the deployable image.

## Current Limitations

- Facebook UI changes can break selectors; the app includes guardrails to avoid typing into generic Facebook search or comment boxes.
- Scheduled jobs are in-process, so production-grade durability would require an external queue or database-backed scheduler.
- The first Facebook session must be created manually through noVNC.
- GitLab summarization requires a configured `GITLAB_PERSONAL_ACCESS_TOKEN` secret.

## Security

- Do not commit `.env`, Google credential files, API keys, or Facebook session files.
- Use Secret Manager for deploy-time secrets.
- Use Cloud Run service account IAM for GCS, Vertex AI, and Secret Manager access.
