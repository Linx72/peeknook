"""Apply remote sync events to local PeekNook database (bi-directional sync)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from loguru import logger

from open_notebook.peeknook.settings_store import record_conflict


def _parse_ts(value: Optional[str]) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def apply_remote_event(event: Dict[str, Any]) -> Dict[str, str]:
    """Apply one cloud event locally. Returns status dict."""
    object_type = event.get("object_type", "")
    operation = event.get("operation", "")
    object_id = event.get("object_id", "")
    payload_raw = event.get("payload_json")
    payload: Dict[str, Any] = {}
    if payload_raw:
        try:
            payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
        except json.JSONDecodeError:
            payload = {"raw": payload_raw}
    if isinstance(payload.get("payload"), str):
        try:
            payload = {**payload, **json.loads(payload["payload"])}
        except json.JSONDecodeError:
            pass

    remote_ts = _parse_ts(event.get("created_at"))

    if object_type == "notebook" and operation == "create":
        return await _apply_notebook_create(object_id, payload, remote_ts)
    if object_type == "source" and operation == "create":
        return await _apply_source_stub(object_id, payload, remote_ts)

    return {"status": "ignored", "reason": f"{object_type}:{operation}"}


async def _apply_notebook_create(
    object_id: str, payload: Dict[str, Any], remote_ts: datetime
) -> Dict[str, str]:
    from open_notebook.domain.notebook import Notebook

    name = payload.get("name") or f"Synced {object_id[:8]}"
    description = payload.get("description") or ""

    try:
        existing = await Notebook.get(object_id)
    except Exception:
        existing = None

    if existing:
        local_ts = _parse_ts(str(existing.updated) if existing.updated else None)
        if remote_ts <= local_ts:
            record_conflict(
                "notebook",
                object_id,
                "local_wins",
                {"name": name, "remote_ts": remote_ts.isoformat()},
            )
            return {"status": "conflict", "resolution": "local_wins"}
        existing.name = name
        existing.description = description
        await existing.save()
        record_conflict("notebook", object_id, "remote_wins", {"name": name})
        return {"status": "updated", "resolution": "remote_wins"}

    notebook = Notebook(name=name, description=description)
    await notebook.save()
    return {"status": "created", "id": notebook.id or object_id}


async def _apply_source_stub(
    object_id: str, payload: Dict[str, Any], remote_ts: datetime
) -> Dict[str, str]:
    """Source file import handled by blob_pull after pull batch."""
    logger.info(f"PeekNook sync: queued remote source {object_id} ({payload.get('title')})")
    return {"status": "queued_for_blob_import", "object_id": object_id}
