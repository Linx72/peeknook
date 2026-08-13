#!/usr/bin/env bash
# Import a Developer ID certificate into an ephemeral CI keychain before Tauri builds.
set -euo pipefail

MODE="${1:-import}"
TEMP_ROOT="${RUNNER_TEMP:-${TMPDIR:-/tmp}}"

cleanup_signing_keychain() {
  local keychain_path="${PEEKNOOK_BUILD_KEYCHAIN:-}"
  local signing_dir="${PEEKNOOK_SIGNING_TEMP_DIR:-}"
  local original_keychain="${PEEKNOOK_ORIGINAL_KEYCHAIN:-}"

  if [[ -n "$original_keychain" ]]; then
    security default-keychain -d user -s "$original_keychain" >/dev/null 2>&1 || true
  fi
  if [[ -n "$keychain_path" ]]; then
    security delete-keychain "$keychain_path" >/dev/null 2>&1 || true
  fi
  if [[ -n "$signing_dir" ]]; then
    case "$signing_dir" in
      "$TEMP_ROOT"/peeknook-macos-signing.*)
        [[ -d "$signing_dir" ]] && find "$signing_dir" -depth -delete
        ;;
      *)
        echo "Refusing to remove unexpected signing directory: $signing_dir" >&2
        return 1
        ;;
    esac
  fi
}

if [[ "$MODE" == "--cleanup" ]]; then
  cleanup_signing_keychain
  echo "Removed the ephemeral macOS signing keychain"
  exit 0
fi
if [[ "$MODE" != "import" ]]; then
  echo "Usage: $0 [--cleanup]" >&2
  exit 2
fi

for variable in APPLE_CERTIFICATE APPLE_CERTIFICATE_PASSWORD KEYCHAIN_PASSWORD GITHUB_ENV; do
  if [[ -z "${!variable:-}" ]]; then
    echo "Missing required environment variable: $variable" >&2
    exit 1
  fi
done

SIGNING_DIR="$(mktemp -d "$TEMP_ROOT/peeknook-macos-signing.XXXXXX")"
CERTIFICATE_PATH="$SIGNING_DIR/developer-id.p12"
KEYCHAIN_PATH="$SIGNING_DIR/peeknook-build.keychain-db"
ORIGINAL_KEYCHAIN="$(security default-keychain -d user | tr -d '"' | xargs)"

cleanup_failed_import() {
  PEEKNOOK_BUILD_KEYCHAIN="$KEYCHAIN_PATH" \
    PEEKNOOK_SIGNING_TEMP_DIR="$SIGNING_DIR" \
    PEEKNOOK_ORIGINAL_KEYCHAIN="$ORIGINAL_KEYCHAIN" \
    cleanup_signing_keychain || true
}
trap cleanup_failed_import ERR INT TERM

python3 - "$CERTIFICATE_PATH" <<'PY'
import base64
import binascii
import os
import sys
from pathlib import Path

try:
    encoded_certificate = "".join(os.environ["APPLE_CERTIFICATE"].split())
    certificate = base64.b64decode(encoded_certificate, validate=True)
except binascii.Error as exc:
    raise SystemExit(f"APPLE_CERTIFICATE is not valid base64: {exc}") from exc
if not certificate:
    raise SystemExit("APPLE_CERTIFICATE decoded to an empty file")
Path(sys.argv[1]).write_bytes(certificate)
PY

security create-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN_PATH"
security default-keychain -d user -s "$KEYCHAIN_PATH"
security unlock-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN_PATH"
security set-keychain-settings -t 3600 -u "$KEYCHAIN_PATH"
security import "$CERTIFICATE_PATH" \
  -k "$KEYCHAIN_PATH" \
  -P "$APPLE_CERTIFICATE_PASSWORD" \
  -T /usr/bin/codesign
security set-key-partition-list \
  -S apple-tool:,apple:,codesign: \
  -s \
  -k "$KEYCHAIN_PASSWORD" \
  "$KEYCHAIN_PATH"

SIGNING_IDENTITY="$(
  security find-identity -v -p codesigning "$KEYCHAIN_PATH" \
    | awk -F'"' '/Developer ID Application/{print $2; exit}'
)"
if [[ -z "$SIGNING_IDENTITY" ]]; then
  echo "Imported certificate does not contain a valid Developer ID Application identity" >&2
  exit 1
fi

{
  echo "APPLE_SIGNING_IDENTITY=$SIGNING_IDENTITY"
  echo "PEEKNOOK_BUILD_KEYCHAIN=$KEYCHAIN_PATH"
  echo "PEEKNOOK_SIGNING_TEMP_DIR=$SIGNING_DIR"
  echo "PEEKNOOK_ORIGINAL_KEYCHAIN=$ORIGINAL_KEYCHAIN"
} >> "$GITHUB_ENV"

rm -f "$CERTIFICATE_PATH"
trap - ERR INT TERM
echo "Imported macOS signing identity: $SIGNING_IDENTITY"
