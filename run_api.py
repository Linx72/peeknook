#!/usr/bin/env python3
"""
Startup script for PeekNook API server.
"""

import os
import sys
from pathlib import Path

import uvicorn

# Add the current directory to Python path so imports work
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


def run_frozen_import_self_test() -> None:
    """Import the packaged runtime graph without starting local services."""
    from api.main import app
    from open_notebook.peeknook.standalone import bootstrap_embedded_services

    assert app.title == "PeekNook API"
    assert callable(bootstrap_embedded_services)
    print("PEEKNOOK_SIDECAR_IMPORTS_OK")


if __name__ == "__main__":
    if "--worker" in sys.argv:
        sys.argv.remove("--worker")
        from surreal_commands.cli.worker import main as run_worker

        run_worker()
        raise SystemExit(0)

    if "--self-test" in sys.argv:
        run_frozen_import_self_test()
        raise SystemExit(0)

    from open_notebook.peeknook.standalone import bootstrap_embedded_services

    bootstrap_embedded_services()
    # Default configuration
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "5055"))
    reload = os.getenv("API_RELOAD", "true").lower() == "true"

    print(f"Starting PeekNook API server on {host}:{port}")
    print(f"Reload mode: {reload}")

    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=reload,
        reload_dirs=[str(current_dir)] if reload else None,
    )
