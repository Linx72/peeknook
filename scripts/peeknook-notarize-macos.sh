#!/usr/bin/env bash
# Notarize PeekNook DMG (requires signed app + Apple credentials).
#
# Env:
#   APPLE_ID, APPLE_PASSWORD (app-specific), APPLE_TEAM_ID
#   Optional: DMG path as first argument
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DMG="${1:-}"

if [[ -z "$DMG" ]]; then
  DMG="$(ls -1 "$ROOT"/desktop/src-tauri/target/release/bundle/dmg/*.dmg 2>/dev/null | head -1 || true)"
fi

if [[ -z "$DMG" || ! -f "$DMG" ]]; then
  echo "DMG not found. Build first: ./scripts/peeknook-build-release.sh" >&2
  exit 1
fi

for var in APPLE_ID APPLE_PASSWORD APPLE_TEAM_ID; do
  if [[ -z "${!var:-}" ]]; then
    echo "Skip notarization — set $var (and other APPLE_* vars) to notarize."
    exit 0
  fi
done

echo "Submitting $DMG for notarization..."
xcrun notarytool submit "$DMG" \
  --apple-id "$APPLE_ID" \
  --password "$APPLE_PASSWORD" \
  --team-id "$APPLE_TEAM_ID" \
  --wait

xcrun stapler staple "$DMG"
echo "Notarized and stapled: $DMG"
