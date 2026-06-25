#!/usr/bin/env bash
# Record completion of a physical two-Mac PDF sync field test.
#
# After running push on Mac A and pull on Mac B:
#   export PEEKNOOK_SYNC_SOURCE_ID=source:...
#   ./scripts/peeknook-two-mac-physical-record.sh
#
# Optional:
#   PEEKNOOK_CLOUD_EMAIL=you@example.com
#   PEEKNOOK_FIELD_TEST_NOTES="both Macs on same LAN"
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SIGNOFF="${PEEKNOOK_QA_SIGNOFF:-$HOME/Library/Application Support/PeekNook/qa-signoff.json}"
SOURCE_ID="${PEEKNOOK_SYNC_SOURCE_ID:-}"
EMAIL="${PEEKNOOK_CLOUD_EMAIL:-}"
NOTES="${PEEKNOOK_FIELD_TEST_NOTES:-}"

if [[ "${1:-}" == "checklist" ]]; then
  exec bash "$ROOT/scripts/peeknook-two-mac-qa.sh"
fi

if [[ -z "$SOURCE_ID" ]]; then
  echo "Set PEEKNOOK_SYNC_SOURCE_ID from machine A push output." >&2
  echo "Run checklist: $0 checklist" >&2
  exit 1
fi

mkdir -p "$(dirname "$SIGNOFF")"

python3 -c "
import json, datetime, os, pathlib

path = pathlib.Path('$SIGNOFF')
existing = {}
if path.exists():
    existing = json.loads(path.read_text())

existing.update({
  'physical_two_mac': {
    'completed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_id': '$SOURCE_ID',
    'cloud_email': os.environ.get('PEEKNOOK_CLOUD_EMAIL') or None,
    'notes': os.environ.get('PEEKNOOK_FIELD_TEST_NOTES') or None,
  },
  'signed_off_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
})

path.write_text(json.dumps(existing, indent=2))
print(json.dumps(existing['physical_two_mac'], indent=2))
"

echo ""
echo "Physical two-Mac test recorded: $SIGNOFF"
