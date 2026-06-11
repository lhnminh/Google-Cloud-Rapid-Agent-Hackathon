# Cloud Deployment

This guide is the end-to-end Cloud Run deployment path for this repo.

The app runs as a Docker container on Cloud Run. Facebook browser session files are persisted in Google Cloud Storage, because Cloud Run containers are stateless. The scheduler runs inside the app process, so Cloud Run must keep one instance alive and keep CPU allocated outside request handling.

## 1. Local Prerequisites

Install and authenticate these locally:

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project xenon-depth-497608-a4
```

Make sure Docker Desktop is running.

## 2. Enable Google Cloud APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com \
  --project=xenon-depth-497608-a4
```

## 3. Create The GCS Session Bucket

Facebook login/session data is uploaded to this bucket and downloaded by Cloud Run on startup.

```bash
gcloud storage buckets create gs://forgettext-sessions \
  --project=xenon-depth-497608-a4 \
  --location=us-central1 \
  --uniform-bucket-level-access
```

If the bucket name is already taken, choose another globally unique name and use that value everywhere below.

Set these in `.env` for local Docker:

```bash
GCP_PROJECT_ID=xenon-depth-497608-a4
GCP_LOCATION=us-central1
GCS_SESSION_BUCKET=forgettext-sessions
```

## 4. Create Artifact Registry

```bash
gcloud artifacts repositories create forgettext \
  --repository-format=docker \
  --location=us-central1 \
  --project=xenon-depth-497608-a4
```

If this returns `ALREADY_EXISTS`, continue.

Allow Docker to push images:

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

## 5. Store Optional Secrets

The current Vertex AI path uses Google Cloud authentication and `GCP_PROJECT_ID` / `GCP_LOCATION`.

If you use API-key based Gemini code or want to keep the deploy command compatible with the existing docs, create this secret:

```bash
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY \
  --data-file=- \
  --project=xenon-depth-497608-a4
```

If GitLab issue summarization is used, create this secret too:

```bash
echo -n "YOUR_GITLAB_PERSONAL_ACCESS_TOKEN" | gcloud secrets create GITLAB_PERSONAL_ACCESS_TOKEN \
  --data-file=- \
  --project=xenon-depth-497608-a4
```

To update an existing secret:

```bash
echo -n "NEW_VALUE" | gcloud secrets versions add GEMINI_API_KEY \
  --data-file=- \
  --project=xenon-depth-497608-a4
```

## 6. Upload A Facebook Session To GCS

Do this locally first. Local Docker exposes noVNC on port `6080`, which lets you complete Facebook login in the browser running inside the container.

```bash
docker compose up --build
```

Then:

1. Open `http://localhost:8080`.
2. Click the Facebook connect/login button.
3. Open `http://localhost:6080/vnc.html`.
4. Log in to Facebook inside the noVNC browser.
5. Complete any 2FA/checkpoint prompts.
6. Wait for the app to save and upload the session to GCS.

Expected local Docker logs:

```text
Uploading session to GCS bucket: forgettext-sessions
Session archive uploaded successfully.
```

Stop local Docker after the session is uploaded:

```bash
docker compose down
```

Do not use `docker compose down -v` unless you intentionally want to remove the local session volume.

## 7. Grant Cloud Run Runtime Permissions

Get the project number:

```bash
PROJECT_NUMBER=$(gcloud projects describe xenon-depth-497608-a4 --format="value(projectNumber)")
echo $PROJECT_NUMBER
```

The default Cloud Run service account is:

```text
PROJECT_NUMBER-compute@developer.gserviceaccount.com
```

Grant it access to the session bucket:

```bash
gcloud storage buckets add-iam-policy-binding gs://forgettext-sessions \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

Grant Vertex AI access:

```bash
gcloud projects add-iam-policy-binding xenon-depth-497608-a4 \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

Grant Secret Manager access if using secrets:

```bash
gcloud projects add-iam-policy-binding xenon-depth-497608-a4 \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## 8. Build And Push The Image

Use `buildx` so the pushed image is Linux AMD64 compatible, especially on Apple Silicon machines.

```bash
IMAGE=us-central1-docker.pkg.dev/xenon-depth-497608-a4/forgettext/app:latest

docker buildx build \
  --platform linux/amd64 \
  -t $IMAGE \
  . \
  --push
```

## 9. Deploy To Cloud Run

```bash
gcloud run deploy forgettext \
  --image=us-central1-docker.pkg.dev/xenon-depth-497608-a4/forgettext/app:latest \
  --region=us-central1 \
  --project=xenon-depth-497608-a4 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=300 \
  --min-instances=1 \
  --no-cpu-throttling \
  --set-env-vars="GCP_PROJECT_ID=xenon-depth-497608-a4,GCP_LOCATION=us-central1,GCS_SESSION_BUCKET=forgettext-sessions" \
  --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest"
```

Important flags:

- `--min-instances=1` keeps one container alive for scheduled jobs.
- `--no-cpu-throttling` keeps CPU available after HTTP requests finish, so APScheduler can wake up at the scheduled time.
- `--memory=2Gi` is the minimum recommended memory for Playwright/Chromium. Use `4Gi` if the container exits or Chromium crashes.

If you did not create `GEMINI_API_KEY`, remove this part from the deploy command:

```bash
--set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest"
```

## 10. Verify Deployment

Read recent Cloud Run logs:

```bash
gcloud run services logs read forgettext \
  --region=us-central1 \
  --project=xenon-depth-497608-a4 \
  --limit=100
```

Expected startup/session logs:

```text
Downloading session from GCS bucket: forgettext-sessions
Session download and extraction complete.
Facebook session verified successfully!
```

Expected scheduling logs after sending a request:

```text
Web request received instruction: ...
Extraction Successful:
Execution Time: ...
Launching browser to send scheduled message...
Navigating to Facebook Messages...
Searching for ...
Attempting to open contact row for ...
Typing message: ...
Sending...
```

## 11. Redeploy After Code Changes

```bash
IMAGE=us-central1-docker.pkg.dev/xenon-depth-497608-a4/forgettext/app:latest

docker buildx build \
  --platform linux/amd64 \
  -t $IMAGE \
  . \
  --push

gcloud run deploy forgettext \
  --image=$IMAGE \
  --region=us-central1 \
  --project=xenon-depth-497608-a4 \
  --min-instances=1 \
  --no-cpu-throttling
```

The Facebook session stored in GCS is not removed by redeploying.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Scheduled job logs stop after the HTTP `200 OK` response | Cloud Run CPU is throttled outside requests | Redeploy/update with `--no-cpu-throttling` |
| Scheduled messages never fire after idle time | Cloud Run scaled to zero | Redeploy/update with `--min-instances=1` |
| `GCS download skipped: 403` | Cloud Run service account lacks bucket access | Grant `roles/storage.objectAdmin` on the bucket |
| Secret access errors | Cloud Run service account lacks Secret Manager access | Grant `roles/secretmanager.secretAccessor` |
| `Facebook session is invalid or expired` | Cookies/session expired or checkpoint required | Redo the local noVNC login and upload session again |
| `No session archive found in GCS` | Login session was never uploaded | Run local Docker login flow first |
| Browser sends to the wrong Facebook surface | Automation selected a generic Facebook textbox | Keep the Messenger composer guard in `backend/browser_agent.py` and check Cloud Run browser logs |
| Search opens a Facebook profile instead of Messenger thread | Facebook search result points to profile | The current code attempts to click the profile `Message` button, then requires a Messenger composer before typing |
| Container exits or Chromium crashes | Not enough memory | Increase Cloud Run memory to `4Gi` |

## Security Notes

- Do not commit `.env`.
- Do not commit service account JSON files from `creds/`.
- Cloud Run should use IAM permissions on its runtime service account, not a bundled local credential file.
- If a token/API key appears in logs, chat, or screenshots, rotate it.
