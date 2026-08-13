#!/usr/bin/env bash
# Verify that every public macOS artifact contains the signed and notarized app.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUNDLE_ROOT="${1:-$ROOT/desktop/src-tauri/target/release/bundle}"
TEMP_ROOT="${RUNNER_TEMP:-${TMPDIR:-/tmp}}"
MOUNT_DIR=""
EXTRACT_DIR=""

cleanup() {
  if [[ -n "$MOUNT_DIR" ]] && mount | grep -Fq " on $MOUNT_DIR "; then
    hdiutil detach "$MOUNT_DIR" -quiet || hdiutil detach "$MOUNT_DIR" -force -quiet || true
  fi
  for directory in "$MOUNT_DIR" "$EXTRACT_DIR"; do
    if [[ -z "$directory" ]]; then
      continue
    fi
    case "$directory" in
      "$TEMP_ROOT"/peeknook-macos-verify.*)
        [[ -d "$directory" ]] && find "$directory" -depth -delete
        ;;
      *)
        echo "Refusing to remove unexpected verification directory: $directory" >&2
        ;;
    esac
  done
}
trap cleanup EXIT

verify_app() {
  local label="$1"
  local app_path="$2"
  local details

  echo "Verifying $label: $app_path"
  codesign --verify --deep --strict --verbose=2 "$app_path"
  details="$(codesign -dv --verbose=4 "$app_path" 2>&1)"
  if ! grep -q '^Authority=Developer ID Application:' <<< "$details"; then
    echo "$label is not signed with a Developer ID Application certificate" >&2
    exit 1
  fi
  spctl --assess --type execute --verbose=2 "$app_path"
  xcrun stapler validate "$app_path"
}

APP="$(find "$BUNDLE_ROOT" -type d -name 'PeekNook.app' -print -quit 2>/dev/null || true)"
DMG="$(find "$BUNDLE_ROOT" -type f -name '*.dmg' -print -quit 2>/dev/null || true)"
UPDATER="$(find "$BUNDLE_ROOT" -type f -name '*.app.tar.gz' -print -quit 2>/dev/null || true)"

if [[ -z "$DMG" || -z "$UPDATER" ]]; then
  echo "Signed macOS release requires both a DMG and an app updater archive under: $BUNDLE_ROOT" >&2
  exit 1
fi
if [[ ! -s "${UPDATER}.sig" ]]; then
  echo "Missing or empty Tauri updater signature: ${UPDATER}.sig" >&2
  exit 1
fi

if [[ -n "$APP" ]]; then
  verify_app "loose app bundle" "$APP"
fi

MOUNT_DIR="$(mktemp -d "$TEMP_ROOT/peeknook-macos-verify.XXXXXX")"
hdiutil attach -readonly -nobrowse -mountpoint "$MOUNT_DIR" "$DMG" >/dev/null
DMG_APP="$(find "$MOUNT_DIR" -maxdepth 2 -type d -name 'PeekNook.app' -print -quit)"
if [[ -z "$DMG_APP" ]]; then
  echo "DMG does not contain PeekNook.app: $DMG" >&2
  exit 1
fi
verify_app "app inside DMG" "$DMG_APP"
hdiutil detach "$MOUNT_DIR" -quiet
find "$MOUNT_DIR" -depth -delete
MOUNT_DIR=""

EXTRACT_DIR="$(mktemp -d "$TEMP_ROOT/peeknook-macos-verify.XXXXXX")"
tar -xzf "$UPDATER" -C "$EXTRACT_DIR"
UPDATER_APP="$(find "$EXTRACT_DIR" -type d -name 'PeekNook.app' -print -quit)"
if [[ -z "$UPDATER_APP" ]]; then
  echo "Updater archive does not contain PeekNook.app: $UPDATER" >&2
  exit 1
fi
verify_app "app inside updater archive" "$UPDATER_APP"

echo "macOS release signature and notarization checks passed"
