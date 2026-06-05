# Deployment Guide

Two paths depending on whether you want persistent Facebook sessions across restarts.

---

## Without GCS — Local only

Sessions are stored in a Docker named volume. They survive container restarts but are lost if you remove the volume or move to another machine. **Cloud Run is not viable without GCS** (stateless containers, no persistent disk).

### Prerequisites
- Docker Desktop installed and running

### Steps

**1. Build and start**
```bash
docker compose up --build
```
App runs at http://localhost:8080

**2. Log in to Facebook**

1. Open http://localhost:8080 and click **Connect Facebook**
2. Open http://localhost:6080/vnc.html in a new tab — you will see a Chrome window running inside the container
3. Log in to Facebook in that noVNC tab — complete any 2FA prompts there
4. Once Messenger loads, the app detects the login and saves the session automatically
5. The noVNC tab is no longer needed after this

> The Docker volume is named `facebook_sessions`. If you run `docker compose down -v` it will be deleted and you will need to log in again. Use `docker compose down` (without `-v`) to preserve it.

**3. Stop**
```bash
docker compose down
```

### Common problems

| Symptom | Fix |
|---|---|
| Port 8080 already in use | Change `"8080:8080"` to `"8081:8080"` in `docker-compose.yml` |
| Port 6080 already in use | Change `"6080:6080"` to `"6081:6080"` in `docker-compose.yml`, then open `:6081/vnc.html` |
| noVNC tab shows black screen | Xvfb hasn't started yet — wait a few seconds and refresh |
| noVNC tab shows desktop but no browser | Click Login first at `:8080`, then switch to the noVNC tab |
| Session lost after restart | You used `docker compose down -v` — log in again |

### Local dev (no Docker)

```bash
source .venv/Scripts/activate
python -m uvicorn backend.main:app --reload --port 8000
```

Open http://127.0.0.1:8000. Login opens a real visible Chrome window on your desktop — complete it normally.

---

## With GCS — Docker + Cloud Run

Sessions are stored in Google Cloud Storage. They persist across container restarts, machine changes, and Cloud Run deployments. Login once, works everywhere.

---

### One-time setup

**1. Enable GCP APIs**
```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  --project=xenon-depth-497608-a4
```

**2. Create a GCS bucket**
```bash
gcloud storage buckets create gs://forgettext-sessions \
  --project=xenon-depth-497608-a4 \
  --location=us-central1 \
  --uniform-bucket-level-access
```
> If the name is taken, pick another. Bucket names are globally unique.

Add to your `.env`:
```
GCS_SESSION_BUCKET=forgettext-sessions
```

**3. Store API keys in Secret Manager**
```bash
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY \
  --data-file=- --project=xenon-depth-497608-a4
```
> To update an existing secret: `echo -n "NEW_VALUE" | gcloud secrets versions add GEMINI_API_KEY --data-file=-`

**4. Create Artifact Registry repo**
```bash
gcloud artifacts repositories create forgettext \
  --repository-format=docker \
  --location=us-central1 \
  --project=xenon-depth-497608-a4
```
> `ALREADY_EXISTS` error means it's already there — continue.

**5. Authenticate Docker to Artifact Registry**
```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

---

### Step A: Log in to Facebook via Docker

```bash
docker compose up --build
```

1. Open http://localhost:8080 → click **Connect Facebook**
2. Open http://localhost:6080/vnc.html in a new tab — Chrome is running inside the container
3. Log in to Facebook in the noVNC tab — complete any 2FA there
4. Once Messenger loads the app detects the login, saves the session, and uploads it to GCS automatically

You should see in the Docker terminal:
```
Uploading session to GCS bucket: forgettext-sessions
Uploaded N session files to GCS.
```

> **Login times out after 120 seconds.** If you need more time (slow 2FA), click Connect again.

---

### Step B: Docker with GCS (subsequent runs)

Once the session is in GCS, Docker works with no extra steps:

```bash
docker compose up --build
```

On startup you will see:
```
Downloading session from GCS bucket: forgettext-sessions
Downloaded N session files from GCS.
Facebook session verified successfully!
```

> **"GCS download skipped"?** Your container can't reach GCS. Mount local credentials temporarily:
> Add to `docker-compose.yml` under `volumes:` → `- ~/.config/gcloud:/root/.config/gcloud:ro`

---

### Step C: Deploy to Cloud Run

**1. Get your project number**
```bash
gcloud projects describe xenon-depth-497608-a4 --format="value(projectNumber)"
```
The default Cloud Run service account is: `PROJECT_NUMBER-compute@developer.gserviceaccount.com`

**2. Grant GCS access to the service account**
```bash
gcloud storage buckets add-iam-policy-binding gs://forgettext-sessions \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```
> Skip this → Cloud Run logs `403 Forbidden` when downloading the session.

**3. Grant Secret Manager access to the service account**
```bash
gcloud projects add-iam-policy-binding xenon-depth-497608-a4 \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```
> Skip this → Cloud Run fails to start entirely.

**4. Build and push the image**
```bash
IMAGE=us-central1-docker.pkg.dev/xenon-depth-497608-a4/forgettext/app:latest

docker build -t $IMAGE .
docker push $IMAGE
```
> `docker push` unauthorized? Re-run step 5 of one-time setup.

**5. Deploy**
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
  --set-env-vars="GCP_PROJECT_ID=xenon-depth-497608-a4,GCP_LOCATION=us-central1,GCS_SESSION_BUCKET=forgettext-sessions" \
  --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest"
```

The service URL is printed at the end. Open it — the app is live.

> **`--min-instances=1` is important.** Without it, Cloud Run scales to zero when idle, killing the message scheduler background thread. Scheduled messages stop firing.

**6. Verify it worked**
```bash
gcloud run services logs read forgettext \
  --region=us-central1 \
  --project=xenon-depth-497608-a4 \
  --limit=50
```
Look for `Facebook session verified successfully!`

---

### Redeploying after code changes

```bash
IMAGE=us-central1-docker.pkg.dev/xenon-depth-497608-a4/forgettext/app:latest

docker build -t $IMAGE .
docker push $IMAGE
gcloud run deploy forgettext --image=$IMAGE --region=us-central1 --project=xenon-depth-497608-a4
```

Session in GCS is untouched. No re-login needed.

---

### Common problems (GCS path)

| Symptom | Cause | Fix |
|---|---|---|
| `GCS download skipped: 403` in Cloud Run | Service account lacks GCS access | Step C-2 |
| Service fails to start, `403` on secrets | Service account lacks Secret Manager access | Step C-3 |
| `Facebook session is invalid or expired` | Facebook cookies expired | Redo Step A, then redeploy |
| `No session files found in GCS` | Never logged in | Complete Step A |
| Container exits immediately | Out of memory | Increase `--memory` to `4Gi` |
| Scheduled messages stop after idle | Min-instances is 0 | Add `--min-instances=1` to deploy |
