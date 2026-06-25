#!/usr/bin/env python3
"""Seed a local source sync event with PDF file for blob push tests."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from open_notebook.config import UPLOADS_FOLDER  # noqa: E402
from open_notebook.peeknook.sync_store import record_event  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--notebook-id", required=True)
    args = parser.parse_args()

    uploads = Path(UPLOADS_FOLDER)
    uploads.mkdir(parents=True, exist_ok=True)
    dest = uploads / f"sync-verify-{uuid.uuid4().hex[:8]}.pdf"
    shutil.copy2(args.pdf, dest)

    source_id = f"source:syncverify{uuid.uuid4().hex[:10]}"
    record_event(
        "source",
        source_id,
        "create",
        {
            "notebook_ids": [args.notebook_id],
            "title": "Sync Verify PDF",
            "type": "upload",
            "file_path": str(dest.resolve()),
        },
    )
    print(json.dumps({"source_id": source_id, "file_path": str(dest.resolve())}))


if __name__ == "__main__":
    main()
