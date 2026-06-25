"""Download remote blobs from PeekNook Cloud and import as local sources."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from open_notebook.config import UPLOADS_FOLDER


async def fetch_blobs_for_object(
    cloud_url: str, token: str, object_id: str
) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(
            f"{cloud_url.rstrip('/')}/blobs",
            params={"object_id": object_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        body = response.json()
    return body.get("items", [])


async def download_blob_bytes(cloud_url: str, token: str, blob_id: str) -> bytes:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(
            f"{cloud_url.rstrip('/')}/blobs/{blob_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.content


async def import_source_from_cloud(
    cloud_url: str,
    token: str,
    source_id: str,
    payload: Dict[str, Any],
) -> Dict[str, str]:
    """Download PDF/file from cloud and create local source with embedding."""
    from api.routers.sources import generate_unique_filename
    from commands.source_commands import SourceProcessingInput
    from api.command_service import CommandService
    from open_notebook.database.repository import ensure_record_id
    from open_notebook.domain.notebook import Source
    from open_notebook.peeknook.sync_store import is_cloud_object_imported, mark_cloud_object_imported

    if is_cloud_object_imported(source_id):
        return {"status": "already_imported", "source_id": source_id}

    blobs = await fetch_blobs_for_object(cloud_url, token, source_id)
    if not blobs:
        return {"status": "no_blob", "source_id": source_id}

    blob = blobs[0]
    data = await download_blob_bytes(cloud_url, token, blob["id"])
    filename = blob.get("filename") or f"sync-{source_id}.pdf"
    file_path = generate_unique_filename(filename, UPLOADS_FOLDER)
    Path(file_path).write_bytes(data)

    notebook_ids: List[str] = payload.get("notebook_ids") or []
    title = payload.get("title") or filename

    source = Source(title=title, topics=[])
    await source.save()

    for notebook_id in notebook_ids:
        await source.add_to_notebook(notebook_id)

    import commands.source_commands  # noqa: F401

    command_input = SourceProcessingInput(
        source_id=str(source.id),
        content_state={"file_path": file_path, "delete_source": False},
        notebook_ids=notebook_ids,
        transformations=[],
        embed=True,
    )
    command_id = await CommandService.submit_command_job(
        "open_notebook",
        "process_source",
        command_input.model_dump(),
    )
    source.command = ensure_record_id(command_id)
    await source.save()
    mark_cloud_object_imported(source_id, str(source.id))

    logger.info(f"PeekNook sync: imported source {source.id} from cloud blob {blob['id']}")
    return {"status": "imported", "source_id": str(source.id), "command_id": command_id}


async def apply_remote_blobs(
    cloud_url: str,
    token: str,
    events: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    for event in events:
        if event.get("object_type") != "source" or event.get("operation") != "create":
            continue
        payload_raw = event.get("payload_json")
        payload: Dict[str, Any] = {}
        if payload_raw:
            try:
                payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
            except json.JSONDecodeError:
                payload = {}
        if isinstance(payload.get("payload"), str):
            try:
                payload = {**payload, **json.loads(payload["payload"])}
            except json.JSONDecodeError:
                pass
        try:
            outcome = await import_source_from_cloud(
                cloud_url, token, event.get("object_id", ""), payload
            )
            results.append(outcome)
        except Exception as exc:
            logger.warning(f"Blob import failed for {event.get('object_id')}: {exc}")
            results.append({"status": "error", "error": str(exc)})
    return results
