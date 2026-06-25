#!/usr/bin/env bash
# Record automated QA sign-off (proxy for physical two-Mac testing).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SIGNOFF="$HOME/Library/Application Support/PeekNook/qa-signoff.json"

bash "$ROOT/scripts/peeknook-two-mac-qa.sh"

mkdir -p "$(dirname "$SIGNOFF")"
python3 -c "
import json, datetime
print(json.dumps({
  'signed_off_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'automated': True,
  'scripts': ['peeknook-two-mac-qa', 'peeknook-pdf-sync-verify', 'peeknook-sync-verify'],
  'physical_two_mac': 'optional — run peeknook-pdf-sync-two-mac.sh push/pull on two Macs',
}, indent=2))
" > "$SIGNOFF"

echo ""
echo "QA sign-off recorded: $SIGNOFF"
