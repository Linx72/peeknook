#!/usr/bin/env bash
# Legacy helper for signing only a loose PeekNook.app during development.
# Public installers must be signed by Tauri while it creates the DMG and updater archive.
#
# Env:
#   APPLE_SIGNING_IDENTITY — e.g. "Developer ID Application: Your Name (TEAMID)"
#   APPLE_ID, APPLE_PASSWORD, APPLE_TEAM_ID — for notarization (optional)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="${1:-$ROOT/desktop/src-tauri/target/release/bundle/macos/PeekNook.app}"

if [[ ! -d "$APP" ]]; then
  echo "App not found: $APP — run: cd desktop && npm run tauri build" >&2
  exit 1
fi

if [[ "${PEEKNOOK_ALLOW_STANDALONE_APP_SIGNING:-0}" != "1" ]]; then
  BUNDLE_ROOT="$ROOT/desktop/src-tauri/target/release/bundle"
  if find "$BUNDLE_ROOT" -type f \( -name '*.dmg' -o -name '*.app.tar.gz' \) -print -quit 2>/dev/null | grep -q .; then
    echo "Refusing post-build signing: existing DMG/updater files would still contain the old app." >&2
    echo "Set APPLE_SIGNING_IDENTITY and Apple notarization credentials before running tauri build." >&2
    echo "For a loose development app only, set PEEKNOOK_ALLOW_STANDALONE_APP_SIGNING=1." >&2
    exit 1
  fi
fi

IDENTITY="${APPLE_SIGNING_IDENTITY:-}"
if [[ -z "$IDENTITY" ]]; then
  echo "Set APPLE_SIGNING_IDENTITY to sign. Available identities:"
  security find-identity -v -p codesigning | head -10
  echo ""
  echo "Unsigned app is at: $APP"
  exit 0
fi

echo "Signing $APP with $IDENTITY"
codesign --force --options runtime --entitlements "$ROOT/desktop/src-tauri/entitlements.plist" --sign "$IDENTITY" "$APP/Contents/MacOS/peeknook-api" 2>/dev/null || true
codesign --force --deep --options runtime --entitlements "$ROOT/desktop/src-tauri/entitlements.plist" --sign "$IDENTITY" "$APP"
codesign --verify --verbose "$APP"
spctl --assess --verbose "$APP" || true

if [[ -n "${APPLE_ID:-}" && -n "${APPLE_PASSWORD:-}" && -n "${APPLE_TEAM_ID:-}" ]]; then
  bash "$ROOT/scripts/peeknook-notarize-macos.sh"
fi

echo "Done: $APP"
