#!/usr/bin/env bash
# Machine B — pull PDF from cloud using two-mac-handoff.json (from machine A push).
#
#   export PEEKNOOK_CLOUD_PASSWORD=…   # or prompted
#   ./scripts/peeknook-two-mac-machine-b.sh
#   ./scripts/peeknook-two-mac-machine-b.sh --record   # also physical sign-off
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HANDOFF="${PEEKNOOK_TWO_MAC_HANDOFF:-"$HOME/Library/Application Support/PeekNook/two-mac-handoff.json"}"
RECORD=0
[[ "${1:-}" == "--record" ]] && RECORD=1

if [[ ! -f "$HANDOFF" ]]; then
  echo "Handoff not found: $HANDOFF" >&2
  echo "Run on machine A: ./scripts/peeknook-pdf-sync-two-mac.sh push" >&2
  exit 1
fi

read -r PEEKNOOK_SYNC_SOURCE_ID PEEKNOOK_CLOUD_URL PEEKNOOK_CLOUD_EMAIL < <(
  HANDOFF_PATH="$HANDOFF" python3 <<'PY'
import json, pathlib, os
d = json.loads(pathlib.Path(os.environ["HANDOFF_PATH"]).read_text())
email = d.get("cloud_email") or ""
print(d["source_id"], d.get("cloud_url", ""), email)
PY
)
export PEEKNOOK_SYNC_SOURCE_ID PEEKNOOK_CLOUD_URL PEEKNOOK_CLOUD_EMAIL

if [[ -z "${PEEKNOOK_CLOUD_PASSWORD:-}" ]]; then
  read -rsp "Cloud password for ${PEEKNOOK_CLOUD_EMAIL:-user}: " PEEKNOOK_CLOUD_PASSWORD
  echo
  export PEEKNOOK_CLOUD_PASSWORD
fi

echo "== Machine B: pull from handoff =="
echo "  source: $PEEKNOOK_SYNC_SOURCE_ID"
echo "  cloud:  $PEEKNOOK_CLOUD_URL"
bash "$ROOT/scripts/peeknook-pdf-sync-two-mac.sh" pull

if [[ "$RECORD" == 1 ]]; then
  bash "$ROOT/scripts/peeknook-two-mac-physical-record.sh"
fi

echo "OK — machine B complete"
