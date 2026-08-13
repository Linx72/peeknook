#!/usr/bin/env bash
# Build PeekNook release artifacts. Tauri performs signing before it creates installers.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

REPO="$(bash "$ROOT/scripts/peeknook-github-repo.sh")"
TAG="${PEEKNOOK_RELEASE_TAG:-latest}"
UPDATER_CONFIG="$(mktemp)"
trap 'rm -f "$UPDATER_CONFIG"' EXIT

echo "== PeekNook release build =="
echo "Updater endpoint repo: $REPO (tag: $TAG)"

python3 scripts/peeknook-build-config.py \
  --repo "$REPO" \
  --tag "$TAG" \
  --out "$UPDATER_CONFIG"

echo "[1/3] Backend sidecar…"
bash scripts/build-backend.sh

echo "[2/3] Vite UI…"
cd ui && npm ci && npm run build && cd ..

echo "[3/3] Tauri bundle (updater artifacts and configured platform signing)…"
cd desktop && npm ci && npm run tauri build -- --config "$UPDATER_CONFIG" && cd ..

APP="$ROOT/desktop/src-tauri/target/release/bundle/macos/PeekNook.app"
DMG="$(find "$ROOT/desktop/src-tauri/target/release/bundle/dmg" -maxdepth 1 -type f -name '*.dmg' -print 2>/dev/null | sort | head -1 || true)"
TAR="$(find "$ROOT/desktop/src-tauri/target/release/bundle/macos" -maxdepth 1 -type f -name '*.tar.gz' -print 2>/dev/null | sort | head -1 || true)"

echo ""
echo "Done."
[[ -d "$APP" ]] && echo "  App: $APP"
[[ -n "$DMG" ]] && echo "  DMG: $DMG"
[[ -n "$TAR" ]] && echo "  Updater: $TAR"
