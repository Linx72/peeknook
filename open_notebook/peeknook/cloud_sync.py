"""PeekNook desktop ↔ cloud sync client."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from open_notebook.peeknook.apply_sync import apply_remote_event
from open_notebook.peeknook.blob_sync import upload_pending_blobs
from open_notebook.peeknook.blob_pull import apply_remote_blobs
from open_notebook.peeknook.settings_store import get_setting, record_conflict, set_setting
from open_notebook.peeknook.sync_store import list_pending, mark_synced, record_remote_event


def _mark_sync(status: str) -> None:
    from datetime import datetime, timezone

    set_setting("last_sync_at", datetime.now(timezone.utc).isoformat())
    set_setting("last_sync_status", status)


async def push_to_cloud(cloud_url: str, token: str, limit: int = 100) -> Dict[str, Any]:
    try:
        return await _push_to_cloud(cloud_url, token, limit)
    except Exception as exc:
        _mark_sync(f"error: {exc}")
        raise


async def _push_to_cloud(cloud_url: str, token: str, limit: int = 100) -> Dict[str, Any]:
    pending = list_pending(limit=limit)
    if not pending:
        _mark_sync("ok")
        return {"pushed": 0, "blobs": 0, "message": "Nothing to sync"}

    events = []
    for row in pending:
        payload = row.get("payload_json")
        if payload is not None and not isinstance(payload, str):
            import json

            payload = json.dumps(payload)
        events.append(
            {
                "id": row["id"],
                "object_type": row["object_type"],
                "object_id": row["object_id"],
                "operation": row["operation"],
                "payload": payload,
                "created_at": row["created_at"],
            }
        )

    blobs = await upload_pending_blobs(cloud_url, token, pending)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{cloud_url.rstrip('/')}/sync/push",
            json={"events": events},
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        body = response.json()

    ids = [e["id"] for e in pending]
    mark_synced(ids)
    _mark_sync("ok")
    logger.info(f"PeekNook sync: pushed {len(ids)} events, {blobs} blobs")
    return {"pushed": len(ids), "blobs": blobs, "cloud": body}


async def pull_from_cloud(
    cloud_url: str,
    token: str,
    since: Optional[str] = None,
    apply: bool = True,
) -> Dict[str, Any]:
    try:
        return await _pull_from_cloud(cloud_url, token, since=since, apply=apply)
    except Exception as exc:
        _mark_sync(f"error: {exc}")
        raise


async def _pull_from_cloud(
    cloud_url: str,
    token: str,
    since: Optional[str] = None,
    apply: bool = True,
) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            f"{cloud_url.rstrip('/')}/sync/pull",
            params={"since": since} if since else None,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        body = response.json()

    applied = 0
    results: List[Dict[str, str]] = []
    e2e = (get_setting("e2e_sync", "false") or "false").lower() in ("1", "true", "yes")

    for event in body.get("events", []):
        record_remote_event(
            event.get("object_type", "remote"),
            event.get("object_id", "unknown"),
            event.get("operation", "update"),
            {"payload": event.get("payload_json")},
            remote_id=event.get("id"),
        )
        if apply:
            try:
                outcome = await apply_remote_event(event)
                results.append(outcome)
                if outcome.get("status") == "conflict":
                    record_conflict(
                        event.get("object_type", "unknown"),
                        event.get("object_id", "unknown"),
                        outcome.get("resolution", "unknown"),
                        {"e2e": e2e},
                    )
            except Exception as exc:
                logger.warning(f"Failed to apply remote event: {exc}")
                results.append({"status": "error", "error": str(exc)})
        applied += 1

    blob_results: List[Dict[str, str]] = []
    if apply and body.get("events"):
        try:
            blob_results = await apply_remote_blobs(cloud_url, token, body.get("events", []))
        except Exception as exc:
            logger.warning(f"PeekNook blob pull failed: {exc}")

    _mark_sync("ok")

    return {
        "applied": applied,
        "events": body.get("events", []),
        "results": results,
        "blob_imports": blob_results,
    }
