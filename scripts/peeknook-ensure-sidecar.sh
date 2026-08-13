#!/usr/bin/env bash
# Build Tauri sidecar if missing (after git clone or sync without binary).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$ROOT/desktop/src-tauri/binaries"
TARGET="$(rustc -Vv 2>/dev/null | awk '/host:/ {print $2}')" || true
SIDECAR="$BIN/peeknook-api-${TARGET}"

if [[ -n "$TARGET" && -x "$SIDECAR" ]]; then
  echo "Sidecar OK: $SIDECAR"
  exit 0
fi

echo "Sidecar missing — building via scripts/build-backend.sh…"
bash "$ROOT/scripts/build-backend.sh"
test -x "$SIDECAR" || { echo "Build failed: $SIDECAR" >&2; exit 1; }
echo "OK — $SIDECAR"
