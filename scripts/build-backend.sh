#!/usr/bin/env bash
# Build PeekNook backend binary with PyInstaller (Tauri sidecar).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
DIST="$ROOT/dist/peeknook-backend"
TAURI_BIN="$ROOT/desktop/src-tauri/binaries"
TARGET="$(rustc -Vv 2>/dev/null | awk '/host:/ {print $2}')"

echo "Building PeekNook API bundle..."
uv run pip install pyinstaller >/dev/null 2>&1 || uv pip install pyinstaller

uv run pyinstaller \
  --noconfirm \
  --clean \
  --onefile \
  --name peeknook-api \
  --distpath "$DIST" \
  --workpath "$ROOT/build/pyinstaller" \
  --specpath "$ROOT/scripts" \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.loops \
  --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.protocols \
  --hidden-import uvicorn.protocols.http \
  --hidden-import uvicorn.protocols.http.auto \
  --hidden-import uvicorn.lifespan \
  --hidden-import uvicorn.lifespan.on \
  run_api.py

mkdir -p "$TAURI_BIN"
if [[ -n "$TARGET" && -f "$DIST/peeknook-api" ]]; then
  cp "$DIST/peeknook-api" "$TAURI_BIN/peeknook-api-${TARGET}"
  chmod +x "$TAURI_BIN/peeknook-api-${TARGET}"
  echo "Sidecar: $TAURI_BIN/peeknook-api-${TARGET}"
fi

echo "Built: $DIST/peeknook-api"
ls -la "$DIST/peeknook-api" 2>/dev/null || ls -la "$DIST"
