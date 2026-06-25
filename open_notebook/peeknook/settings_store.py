"""PeekNook local settings (cloud credentials, auto-sync prefs)."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from open_notebook.peeknook.sync_store import sync_connection


def _ensure_settings_table() -> None:
    with sync_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS peeknook_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_conflicts (
                id TEXT PRIMARY KEY,
                object_type TEXT NOT NULL,
                object_id TEXT NOT NULL,
                resolution TEXT NOT NULL,
                detail_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    _ensure_settings_table()
    with sync_connection() as conn:
        row = conn.execute(
            "SELECT value FROM peeknook_settings WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    _ensure_settings_table()
    with sync_connection() as conn:
        conn.execute(
            """
            INSERT INTO peeknook_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        conn.commit()


def get_settings() -> Dict[str, Any]:
    _ensure_settings_table()
    with sync_connection() as conn:
        rows = conn.execute("SELECT key, value FROM peeknook_settings").fetchall()
    out: Dict[str, Any] = {}
    for row in rows:
        key, value = row["key"], row["value"]
        if key in ("auto_sync", "e2e_sync"):
            out[key] = value.lower() in ("1", "true", "yes")
        elif key == "auto_sync_interval_sec":
            out[key] = int(value)
        else:
            out[key] = value
    return out


def record_conflict(
    object_type: str,
    object_id: str,
    resolution: str,
    detail: Optional[Dict[str, Any]] = None,
) -> None:
    import uuid
    from datetime import datetime, timezone

    _ensure_settings_table()
    with sync_connection() as conn:
        conn.execute(
            """
            INSERT INTO sync_conflicts (id, object_type, object_id, resolution, detail_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                object_type,
                object_id,
                resolution,
                json.dumps(detail) if detail else None,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()


def list_conflicts(limit: int = 50) -> list[Dict[str, Any]]:
    _ensure_settings_table()
    with sync_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, object_type, object_id, resolution, detail_json, created_at
            FROM sync_conflicts ORDER BY created_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
