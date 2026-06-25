"""Upload local source files to PeekNook Cloud blob storage during sync."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import httpx
from loguru import logger

from open_notebook.config import UPLOADS_FOLDER


async def upload_pending_blobs(cloud_url: str, token: str, events: List[Dict[str, Any]]) -> int:
    uploaded = 0
    async with httpx.AsyncClient(timeout=120.0) as client:
        for row in events:
            if row.get("object_type") != "source" or row.get("operation") != "create":
                continue
            payload_raw = row.get("payload_json")
            if not payload_raw:
                continue
            try:
                payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
            except json.JSONDecodeError:
                continue
            file_path = payload.get("file_path")
            if not file_path:
                continue
            path = Path(file_path)
            if not path.is_absolute():
                path = Path(UPLOADS_FOLDER) / path.name
            if not path.exists():
                continue
            uploads_root = Path(UPLOADS_FOLDER).resolve()
            if not str(path.resolve()).startswith(str(uploads_root)):
                logger.warning(f"Skipping blob outside uploads: {path}")
                continue

            with path.open("rb") as fh:
                response = await client.post(
                    f"{cloud_url.rstrip('/')}/blobs/upload",
                    data={
                        "object_type": "source",
                        "object_id": row["object_id"],
                        "filename": path.name,
                    },
                    files={"file": (path.name, fh, "application/octet-stream")},
                    headers={"Authorization": f"Bearer {token}"},
                )
            if response.status_code < 300:
                uploaded += 1
            else:
                logger.warning(f"Blob upload failed for {path.name}: {response.text}")
    return uploaded
