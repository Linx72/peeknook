"""
PeekNook SQLite sync event log (cloud sync foundation).

Stores local change events for future bi-directional sync with PeekNook Cloud.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

DEFAULT_DB = Path.home() / "Library/Application Support/PeekNook/sync_events.sqlite"


def _db_path() -> Path:
    raw = os.getenv("PEEKNOOK_SYNC_DB")
    if raw:
        return Path(raw)
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home())) / "PeekNook"
    else:
        base = Path.home() / "Library/Application Support/PeekNook"
    return base / "sync_events.sqlite"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_sync_store() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sync_events (
                id TEXT PRIMARY KEY,
                object_type TEXT NOT NULL,
                object_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                payload_json TEXT,
                created_at TEXT NOT NULL,
                synced_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_sync_events_pending
                ON sync_events(synced_at) WHERE synced_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_sync_events_object
                ON sync_events(object_type, object_id);
            CREATE TABLE IF NOT EXISTS cloud_imports (
                cloud_object_id TEXT PRIMARY KEY,
                local_object_id TEXT,
                imported_at TEXT NOT NULL
            );
            """
        )
        conn.commit()


@contextmanager
def sync_connection() -> Iterator[sqlite3.Connection]:
    init_sync_store()
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


def record_event(
    object_type: str,
    object_id: str,
    operation: str,
    payload: Optional[Dict[str, Any]] = None,
) -> str:
    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with sync_connection() as conn:
        conn.execute(
            """
            INSERT INTO sync_events (id, object_type, object_id, operation, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                object_type,
                object_id,
                operation,
                json.dumps(payload) if payload else None,
                now,
            ),
        )
        conn.commit()
    return event_id


def list_pending(limit: int = 100) -> List[Dict[str, Any]]:
    with sync_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, object_type, object_id, operation, version, payload_json, created_at
            FROM sync_events WHERE synced_at IS NULL
            ORDER BY created_at ASC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def record_remote_event(
    object_type: str,
    object_id: str,
    operation: str,
    payload: Optional[Dict[str, Any]] = None,
    remote_id: Optional[str] = None,
) -> str:
    """Store cloud event locally without re-pushing."""
    event_id = remote_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with sync_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO sync_events
            (id, object_type, object_id, operation, payload_json, created_at, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                object_type,
                object_id,
                operation,
                json.dumps(payload) if payload else None,
                now,
                now,
            ),
        )
        conn.commit()
    return event_id


def is_cloud_object_imported(cloud_object_id: str) -> bool:
    with sync_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM cloud_imports WHERE cloud_object_id = ?",
            (cloud_object_id,),
        ).fetchone()
    return row is not None


def mark_cloud_object_imported(cloud_object_id: str, local_object_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with sync_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO cloud_imports (cloud_object_id, local_object_id, imported_at)
            VALUES (?, ?, ?)
            """,
            (cloud_object_id, local_object_id, now),
        )
        conn.commit()


def mark_synced(event_ids: List[str]) -> int:
    if not event_ids:
        return 0
    now = datetime.now(timezone.utc).isoformat()
    with sync_connection() as conn:
        cur = conn.executemany(
            "UPDATE sync_events SET synced_at = ? WHERE id = ?",
            [(now, eid) for eid in event_ids],
        )
        conn.commit()
        return cur.rowcount
