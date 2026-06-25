"""TermitPro IDE ↔ PeekNook Cloud API bridge."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_db
from api.deps import get_current_user
from api.models import BlobRecord, SyncEvent, User

router = APIRouter(prefix="/termitpro/v1", tags=["termitpro"])


@router.get("/status")
def termitpro_status(user: User = Depends(get_current_user)):
    return {
        "service": "peeknook-cloud",
        "bridge": "termitpro/v1",
        "user_id": user.id,
        "capabilities": ["sync_events", "blobs", "notebooks_metadata"],
    }


@router.get("/notebooks")
def termitpro_notebooks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, le=200),
) -> Dict[str, List[Dict[str, Any]]]:
    """Notebook metadata derived from sync events (TermitPro research panel)."""
    rows = db.scalars(
        select(SyncEvent)
        .where(SyncEvent.user_id == user.id, SyncEvent.object_type == "notebook")
        .order_by(SyncEvent.created_at.desc())
        .limit(limit)
    ).all()
    notebooks: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        payload: Dict[str, Any] = {}
        if row.payload_json:
            try:
                payload = json.loads(row.payload_json)
            except json.JSONDecodeError:
                payload = {}
        nb_id = row.object_id
        if nb_id not in notebooks or row.operation == "create":
            notebooks[nb_id] = {
                "id": nb_id,
                "name": payload.get("name", nb_id),
                "description": payload.get("description", ""),
                "last_operation": row.operation,
                "updated_at": row.created_at.isoformat(),
            }
    return {"notebooks": list(notebooks.values())}


@router.get("/sources")
def termitpro_sources(
    notebook_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, le=200),
):
    query = select(SyncEvent).where(
        SyncEvent.user_id == user.id, SyncEvent.object_type == "source"
    )
    rows = db.scalars(query.order_by(SyncEvent.created_at.desc()).limit(limit)).all()
    sources = []
    for row in rows:
        payload = {}
        if row.payload_json:
            try:
                payload = json.loads(row.payload_json)
            except json.JSONDecodeError:
                pass
        nb_ids = payload.get("notebook_ids") or []
        if notebook_id and notebook_id not in nb_ids:
            continue
        sources.append(
            {
                "id": row.object_id,
                "title": payload.get("title"),
                "notebook_ids": nb_ids,
                "updated_at": row.created_at.isoformat(),
            }
        )
    return {"sources": sources}


@router.get("/search")
def termitpro_search(
    q: str = Query(min_length=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=20, le=100),
):
    """Simple text search over sync event payloads (semantic search via desktop API)."""
    needle = q.lower()
    rows = db.scalars(
        select(SyncEvent)
        .where(SyncEvent.user_id == user.id)
        .order_by(SyncEvent.created_at.desc())
        .limit(500)
    ).all()
    hits = []
    for row in rows:
        hay = (row.payload_json or "") + row.object_type + row.object_id
        if needle in hay.lower():
            hits.append(
                {
                    "object_type": row.object_type,
                    "object_id": row.object_id,
                    "operation": row.operation,
                    "snippet": hay[:200],
                    "created_at": row.created_at.isoformat(),
                }
            )
        if len(hits) >= limit:
            break
    return {"query": q, "results": hits}


@router.get("/blobs")
def termitpro_blobs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
):
    rows = db.scalars(
        select(BlobRecord)
        .where(BlobRecord.user_id == user.id)
        .order_by(BlobRecord.created_at.desc())
        .limit(limit)
    ).all()
    return {
        "blobs": [
            {
                "id": r.id,
                "filename": r.filename,
                "object_type": r.object_type,
                "object_id": r.object_id,
                "size_bytes": r.size_bytes,
            }
            for r in rows
        ]
    }
