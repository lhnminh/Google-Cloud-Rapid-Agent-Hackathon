# Startup

---

## Running with Docker (local)

### Prerequisites
- Docker Desktop installed and running
- A GCS bucket created (see Cloud Run section below for how to create one)
- Your `.env` file has `GCS_SESSION_BUCKET` set

### 1. Build and start

```bash
docker compose up --build
```

App runs at http://localhost:8080

### 2. Log in to Facebook

Open http://localhost:8080 in your browser and click **Login to Facebook**.

A browser inside the container will open on a virtual display. The login detection is automatic — once it sees Messenger load, it saves the session to GCS. Future container restarts will pull the session from GCS automatically.

### 3. Stop

```bash
docker compose down
```

The session is in GCS, not the container, so it survives this.

---

## Deploying to Google Cloud Run

### Prerequisites
- `gcloud` CLI installed and authenticated: `gcloud auth login`
- Docker Desktop running
- Project ID: `xenon-depth-497608-a4`

### 1. Create a GCS bucket for sessions (one-time)

```bash
gcloud storage buckets create gs://forgettext-sessions \
  --project=xenon-depth-497608-a4 \
  --location=us-central1
```

Use any bucket name you want. Add it to your `.env`:

```
GCS_SESSION_BUCKET=forgettext-sessions
```

### 2. Configure Docker to push to Google Artifact Registry

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### 3. Create an Artifact Registry repository (one-time)

```bash
gcloud artifacts repositories create forgettext \
  --repository-format=docker \
  --location=us-central1 \
  --project=xenon-depth-497608-a4
```

### 4. Build and push the image

```bash
IMAGE=us-central1-docker.pkg.dev/xenon-depth-497608-a4/forgettext/app:latest

docker build -t $IMAGE .
docker push $IMAGE
```

### 5. Deploy to Cloud Run

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
  --set-env-vars="GCP_PROJECT_ID=xenon-depth-497608-a4,GCP_LOCATION=us-central1,GCS_SESSION_BUCKET=forgettext-sessions" \
  --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest"
```

> **Note:** `ANTHROPIC_API_KEY` and `GEMINI_API_KEY` should be stored in Google Secret Manager rather than passed as plain env vars. See the section below.

### 6. Grant the Cloud Run service account access to GCS

Cloud Run uses a default service account. Give it access to your session bucket:

```bash
# Get the service account email
gcloud run services describe forgettext \
  --region=us-central1 \
  --project=xenon-depth-497608-a4 \
  --format="value(spec.template.spec.serviceAccountName)"

# Grant storage access (replace SERVICE_ACCOUNT with the value above)
gcloud storage buckets add-iam-policy-binding gs://forgettext-sessions \
  --member="serviceAccount:SERVICE_ACCOUNT" \
  --role="roles/storage.objectAdmin"
```

If the service account field is empty, Cloud Run is using the default compute service account:
`PROJECT_NUMBER-compute@developer.gserviceaccount.com`

Find your project number:
```bash
gcloud projects describe xenon-depth-497608-a4 --format="value(projectNumber)"
```

### 7. Log in to Facebook via Cloud Run

Once deployed, open the Cloud Run service URL (printed at the end of the deploy command) and click **Login to Facebook**. The session is saved to GCS and will persist across all future deployments.

---

## Storing secrets in Secret Manager (recommended)

Instead of passing API keys as plain env vars:

```bash
# Create the secret
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY \
  --data-file=- \
  --project=xenon-depth-497608-a4

# Grant Cloud Run access to it
gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --member="serviceAccount:SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor" \
  --project=xenon-depth-497608-a4
```

Then in the deploy command use `--set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest"` instead of `--set-env-vars`.

---

## Re-deploying after code changes

```bash
IMAGE=us-central1-docker.pkg.dev/xenon-depth-497608-a4/forgettext/app:latest

docker build -t $IMAGE .
docker push $IMAGE
gcloud run deploy forgettext \
  --image=$IMAGE \
  --region=us-central1 \
  --project=xenon-depth-497608-a4
```

The session in GCS is untouched — no need to log in to Facebook again.

---

## Local development (no Docker)

### First-time setup

```bash
python -m pip install uv
uv venv
source .venv/Scripts/activate   # Windows Git Bash
uv pip install -r requirements.txt
playwright install chromium
```

### Daily startup

```bash
source .venv/Scripts/activate
python -m uvicorn backend.main:app --reload --port 8000
```

Open http://127.0.0.1:8000
