import os
from google.cloud import storage

# Cache dirs are huge and don't affect session validity — skip them
_SKIP_DIRS = {"Cache", "Code Cache", "GPUCache", "DawnCache", "ShaderCache"}

_SKIP_FILE_PREFIXES = {
    "Singleton",
}

def _gcs_client():
    return storage.Client()


def download_session(bucket_name: str, session_dir: str, gcs_prefix: str = "sessions/facebook/"):
    """Download session files from GCS into session_dir. Skips missing bucket gracefully."""
    try:
        client = _gcs_client()
        bucket = client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix=gcs_prefix))
        if not blobs:
            print("No session files found in GCS.")
            return
        for blob in blobs:
            relative = blob.name[len(gcs_prefix):]
            if not relative:
                continue
            local_path = os.path.join(session_dir, relative)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            blob.download_to_filename(local_path)
        print(f"Downloaded {len(blobs)} session files from GCS.")
    except Exception as e:
        print(f"GCS download skipped: {e}")


def upload_session(bucket_name: str, session_dir: str, gcs_prefix: str = "sessions/facebook/"):
    """Upload session files from session_dir to GCS, skipping cache directories."""
    try:
        client = _gcs_client()
        bucket = client.bucket(bucket_name)
        uploaded = 0
        for root, dirs, files in os.walk(session_dir):
            # Prune cache dirs in-place so os.walk won't descend into them
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
            for filename in files:
                if any(filename.startswith(prefix) for prefix in _SKIP_FILE_PREFIXES):
                    continue
                local_path = os.path.join(root, filename)
                # File disappeared during runtime
                if not os.path.exists(local_path):
                    continue
                # Skip sockets / special files
                if not os.path.isfile(local_path):
                    continue
                relative = os.path.relpath(local_path, session_dir).replace("\\", "/")
                blob = bucket.blob(gcs_prefix + relative)
                blob.upload_from_filename(local_path)
                uploaded += 1
        print(f"Uploaded {uploaded} session files to GCS.")
    except Exception as e:
        print(f"GCS upload failed: {e}")
