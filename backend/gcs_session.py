import os
import tarfile
import tempfile
from google.cloud import storage

# Cache dirs are huge and don't affect session validity
_SKIP_DIRS = {
    "Cache",
    "Code Cache",
    "GPUCache",
    "DawnCache",
    "ShaderCache",
    "Crashpad",
    "GrShaderCache",
    "GraphiteDawnCache",
}

_SKIP_FILE_PREFIXES = {
    "Singleton",
}

ARCHIVE_NAME = "facebook_session.tar.gz"


def _gcs_client():
    return storage.Client()


def download_session(
    bucket_name: str,
    session_dir: str,
    gcs_blob_name: str = f"sessions/{ARCHIVE_NAME}",
):
    """
    Download compressed session archive from GCS and extract it.
    """

    try:
        client = _gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_blob_name)

        if not blob.exists():
            print("No session archive found in GCS.")
            return

        os.makedirs(session_dir, exist_ok=True)

        archive_path = os.path.join(tempfile.gettempdir(), ARCHIVE_NAME)

        print("Downloading session archive from GCS...")

        blob.download_to_filename(archive_path)

        print("Extracting session archive...")

        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=session_dir)

        print("Session download and extraction complete.")

    except Exception as e:
        print(f"GCS download skipped: {e}")


def upload_session(
    bucket_name: str,
    session_dir: str,
    gcs_blob_name: str = f"sessions/{ARCHIVE_NAME}",
):
    """
    Compress session directory and upload as a single archive.
    """

    try:
        client = _gcs_client()
        bucket = client.bucket(bucket_name)

        archive_path = os.path.join(tempfile.gettempdir(), ARCHIVE_NAME)

        print("Creating compressed session archive...")

        with tarfile.open(archive_path, "w:gz") as tar:

            for root, dirs, files in os.walk(session_dir):

                # Skip cache directories
                dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]

                for filename in files:

                    # Skip Chromium lock/runtime files
                    if any(
                        filename.startswith(prefix)
                        for prefix in _SKIP_FILE_PREFIXES
                    ):
                        continue

                    local_path = os.path.join(root, filename)

                    # File disappeared during runtime
                    if not os.path.exists(local_path):
                        continue

                    # Skip sockets/special files
                    if not os.path.isfile(local_path):
                        continue

                    relative_path = os.path.relpath(
                        local_path,
                        session_dir,
                    )

                    try:
                        tar.add(
                            local_path,
                            arcname=relative_path,
                        )
                    except Exception as file_error:
                        print(
                            f"Skipping archive for {local_path}: {file_error}"
                        )

        print("Uploading compressed session archive to GCS...")

        blob = bucket.blob(gcs_blob_name)

        blob.upload_from_filename(archive_path)

        print("Session archive uploaded successfully.")

    except Exception as e:
        print(f"GCS upload failed: {e}")