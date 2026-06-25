#!/usr/bin/env bash
# Local release when GitHub Actions billing is unavailable.
# Produces signed updater artifacts when TAURI_SIGNING_PRIVATE_KEY is set.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

KEY="${PEEKNOOK_TAURI_KEY:-$ROOT/.tauri/peeknook.key}"
export PEEKNOOK_GITHUB_REPO="${PEEKNOOK_GITHUB_REPO:-Linx72/peeknook}"
export PEEKNOOK_RELEASE_TAG="${PEEKNOOK_RELEASE_TAG:-v0.2.0}"

if [[ -f "$KEY" ]]; then
  export TAURI_SIGNING_PRIVATE_KEY="$KEY"
  export TAURI_SIGNING_PRIVATE_KEY_PASSWORD="${TAURI_SIGNING_PRIVATE_KEY_PASSWORD:-peeknook-updater-dev}"
fi

echo "== PeekNook local release =="
echo "Repo: $PEEKNOOK_GITHUB_REPO  Tag: $PEEKNOOK_RELEASE_TAG"
bash scripts/peeknook-ship-check.sh

bash scripts/peeknook-build-release.sh

BUNDLE="$ROOT/desktop/src-tauri/target/release/bundle"
DMG="$(ls -1 "$BUNDLE"/dmg/*.dmg 2>/dev/null | head -1 || true)"
TAR="$(ls -1 "$BUNDLE"/macos/*.tar.gz 2>/dev/null | head -1 || true)"
MANIFEST="$(mktemp)"
TAG="${PEEKNOOK_RELEASE_TAG#v}"
python3 scripts/peeknook-updater-manifest.py \
  --version "$TAG" \
  --tag "$PEEKNOOK_RELEASE_TAG" \
  --repo "$PEEKNOOK_GITHUB_REPO" \
  --out "$MANIFEST" \
  "$BUNDLE/macos" 2>/dev/null || true

OUT="$HOME/Library/Application Support/PeekNook/releases"
mkdir -p "$OUT"
[[ -n "$DMG" ]] && cp "$DMG" "$OUT/"
[[ -n "$TAR" ]] && cp "$TAR" "$OUT/" && cp "${TAR}.sig" "$OUT/" 2>/dev/null || true
[[ -f "$MANIFEST" ]] && cp "$MANIFEST" "$OUT/latest.json"

echo ""
echo "OK — local release artifacts"
[[ -n "$DMG" ]] && echo "  DMG: $DMG"
[[ -n "$TAR" ]] && echo "  Updater: $TAR"
echo "  Copied to: $OUT"
echo ""
echo "Manual GitHub upload (if CI blocked):"
echo "  gh release upload $PEEKNOOK_RELEASE_TAG $OUT/* --repo $PEEKNOOK_GITHUB_REPO"
