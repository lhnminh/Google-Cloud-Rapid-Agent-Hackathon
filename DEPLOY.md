# Deploy Cheat Sheet

Use this file for the common commands. For full one-time setup, IAM, and troubleshooting, see [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md).

## Local Docker

```bash
docker compose up --build
```

Open:

```text
http://localhost:8080
```

For first-time Facebook login:

1. Click **Connect Facebook**.
2. Open `http://localhost:6080/vnc.html`.
3. Log in to Facebook in the noVNC browser.
4. Wait for the app to detect Messenger and upload the session to GCS.

Stop local Docker:

```bash
docker compose down
```

Do not use `docker compose down -v` unless you intentionally want to delete the local Facebook session volume.

## Build And Push

```bash
IMAGE="us-central1-docker.pkg.dev/xenon-depth-497608-a4/forgettext/app:latest"

docker buildx build \
  --platform linux/amd64 \
  -t "$IMAGE" \
  . \
  --push
```

## Deploy To Cloud Run

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

The important scheduler flags are `--min-instances=1` and `--no-cpu-throttling`.

## Logs

Read recent logs:

```bash
gcloud run services logs read forgettext \
  --region=us-central1 \
  --project=xenon-depth-497608-a4 \
  --limit=100
```

Stream logs:

```bash
gcloud run services logs tail forgettext \
  --region=us-central1 \
  --project=xenon-depth-497608-a4
```

## Current Service

```text
https://forgettext-haqwhjrx4a-uc.a.run.app
```
