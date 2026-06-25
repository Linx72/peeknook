#!/usr/bin/env bash
# Build PeekNook release artifacts: sidecar, Vite UI, Tauri .app/.dmg, optional sign.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

REPO="$(bash "$ROOT/scripts/peeknook-github-repo.sh")"
TAG="${PEEKNOOK_RELEASE_TAG:-latest}"
UPDATER_CONFIG="$(mktemp)"
trap 'rm -f "$UPDATER_CONFIG"' EXIT

echo "== PeekNook release build =="
echo "Updater endpoint repo: $REPO (tag: $TAG)"

python3 -c "
import json, sys
repo = sys.argv[1]
tag = sys.argv[2]
path = sys.argv[3]
endpoint = f'https://github.com/{repo}/releases/{tag}/download/latest.json' if tag != 'latest' else f'https://github.com/{repo}/releases/latest/download/latest.json'
json.dump({'plugins': {'updater': {'endpoints': [endpoint]}}}, open(path, 'w'))
" "$REPO" "$TAG" "$UPDATER_CONFIG"

echo "[1/4] Backend sidecar…"
bash scripts/build-backend.sh

echo "[2/4] Vite UI…"
cd ui && npm ci && npm run build && cd ..

echo "[3/4] Tauri bundle (updater artifacts enabled)…"
cd desktop && npm ci && npm run tauri build -- --config "$UPDATER_CONFIG" && cd ..

echo "[4/4] Code sign (if APPLE_SIGNING_IDENTITY set)…"
bash scripts/peeknook-sign-macos.sh || true

APP="$ROOT/desktop/src-tauri/target/release/bundle/macos/PeekNook.app"
DMG="$(ls -1 "$ROOT"/desktop/src-tauri/target/release/bundle/dmg/*.dmg 2>/dev/null | head -1 || true)"
TAR="$(ls -1 "$ROOT"/desktop/src-tauri/target/release/bundle/macos/*.tar.gz 2>/dev/null | head -1 || true)"

echo ""
echo "Done."
[[ -d "$APP" ]] && echo "  App: $APP"
[[ -n "$DMG" ]] && echo "  DMG: $DMG"
[[ -n "$TAR" ]] && echo "  Updater: $TAR"
