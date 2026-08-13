"""Background auto-sync loop for PeekNook Desktop."""

from __future__ import annotations

import asyncio
import os
from typing import Optional

from loguru import logger

from open_notebook.peeknook.cloud_sync import pull_from_cloud, push_to_cloud
from open_notebook.peeknook.settings_store import get_setting, set_setting

_task: Optional[asyncio.Task] = None


async def run_sync_cycle() -> dict:
    cloud_url = get_setting("cloud_url")
    token = get_setting("cloud_token")
    if not cloud_url or not token:
        return {"skipped": True, "reason": "cloud not configured"}

    since = get_setting("last_pull_at")
    push_result = await push_to_cloud(cloud_url, token)
    pull_result = await pull_from_cloud(cloud_url, token, since=since)

    from datetime import datetime, timezone

    set_setting("last_pull_at", datetime.now(timezone.utc).isoformat())
    set_setting("last_sync_at", datetime.now(timezone.utc).isoformat())
    set_setting("last_sync_status", "ok")
    return {"push": push_result, "pull": pull_result}


async def _auto_sync_loop() -> None:
    while True:
        interval = int(get_setting("auto_sync_interval_sec", "300") or "300")
        enabled = (get_setting("auto_sync", "false") or "false").lower() in (
            "1",
            "true",
            "yes",
        )
        if enabled:
            try:
                result = await run_sync_cycle()
                logger.debug(f"PeekNook auto-sync: {result}")
            except Exception as exc:
                logger.warning(f"PeekNook auto-sync failed: {exc}")
                set_setting("last_sync_status", f"error: {exc}")
        await asyncio.sleep(max(60, interval))


def start_auto_sync() -> None:
    global _task
    if os.getenv("PEEKNOOK_AUTO_SYNC", "").lower() not in ("1", "true", "yes"):
        if (get_setting("auto_sync", "false") or "false").lower() not in ("1", "true", "yes"):
            return
    if _task and not _task.done():
        return
    _task = asyncio.create_task(_auto_sync_loop())
    logger.info("PeekNook auto-sync loop started")


def stop_auto_sync() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
    _task = None

