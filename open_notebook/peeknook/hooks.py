"""Record local changes for PeekNook cloud sync."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from open_notebook.peeknook.sync_store import record_event


def track_notebook_created(notebook_id: str, name: str, description: str = "") -> None:
    record_event(
        "notebook",
        notebook_id,
        "create",
        {"name": name, "description": description},
    )


def track_source_created(
    source_id: str,
    notebook_ids: List[str],
    title: Optional[str] = None,
    source_type: str = "upload",
    file_path: Optional[str] = None,
) -> None:
    payload: Dict[str, Any] = {
        "notebook_ids": notebook_ids,
        "title": title,
        "type": source_type,
    }
    if file_path:
        payload["file_path"] = file_path
    record_event("source", source_id, "create", payload)


def track_note_created(
    note_id: str,
    notebook_id: Optional[str],
    title: Optional[str] = None,
) -> None:
    record_event(
        "note",
        note_id,
        "create",
        {"notebook_id": notebook_id, "title": title},
    )
