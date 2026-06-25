"""PeekNook Cloud blob storage — MinIO or local filesystem fallback."""

from __future__ import annotations

import hashlib
import os
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "peeknook")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "peeknooksecret")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "peeknook-sync")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
LOCAL_BLOB_DIR = Path(os.getenv("PEEKNOOK_BLOB_DIR", "./peeknook_blobs"))


def _minio_client():
    from minio import Minio

    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )


def _ensure_bucket() -> None:
    client = _minio_client()
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)


def storage_backend() -> str:
    return "minio" if MINIO_ENDPOINT else "local"


def upload_blob(user_id: str, blob_id: str, data: bytes, content_type: str) -> Tuple[str, str]:
    """Returns (storage_key, sha256)."""
    digest = hashlib.sha256(data).hexdigest()
    key = f"{user_id}/{blob_id}"

    if MINIO_ENDPOINT:
        _ensure_bucket()
        client = _minio_client()
        client.put_object(
            MINIO_BUCKET,
            key,
            BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return f"minio://{MINIO_BUCKET}/{key}", digest

    path = LOCAL_BLOB_DIR / user_id / blob_id
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return f"local://{path}", digest


def download_blob(storage_key: str) -> Tuple[bytes, str]:
    if storage_key.startswith("minio://"):
        _, rest = storage_key.split("://", 1)
        bucket, key = rest.split("/", 1)
        client = _minio_client()
        response = client.get_object(bucket, key)
        try:
            data = response.read()
        finally:
            response.close()
            response.release_conn()
        return data, "application/octet-stream"

    path = Path(storage_key.removeprefix("local://"))
    if not path.exists():
        raise FileNotFoundError(storage_key)
    return path.read_bytes(), "application/octet-stream"


def delete_blob(storage_key: str) -> None:
    if storage_key.startswith("minio://"):
        _, rest = storage_key.split("://", 1)
        bucket, key = rest.split("/", 1)
        _minio_client().remove_object(bucket, key)
        return
    path = Path(storage_key.removeprefix("local://"))
    if path.exists():
        path.unlink()
