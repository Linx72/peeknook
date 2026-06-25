#!/usr/bin/env bash
# Two-Mac PDF sync: run on machine A (push) then machine B (pull).
#
# Machine A — upload PDF, push to cloud:
#   export PEEKNOOK_CLOUD_EMAIL=you@example.com
#   export PEEKNOOK_CLOUD_PASSWORD=your-password
#   export PEEKNOOK_CLOUD_URL=http://your-cloud:8090
#   ./scripts/peeknook-pdf-sync-two-mac.sh push
#
# Machine B — pull PDF from cloud (same account):
#   export PEEKNOOK_CLOUD_EMAIL=you@example.com
#   export PEEKNOOK_CLOUD_PASSWORD=your-password
#   export PEEKNOOK_CLOUD_URL=http://your-cloud:8090
#   ./scripts/peeknook-pdf-sync-two-mac.sh pull
#
# Optional: API_PORT=5056 CLOUD_PORT=8090
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROLE="${1:-}"
API_PORT="${API_PORT:-5056}"
CLOUD_PORT="${CLOUD_PORT:-8090}"
API="http://127.0.0.1:${API_PORT}"
CLOUD="${PEEKNOOK_CLOUD_URL:-http://127.0.0.1:${CLOUD_PORT}}"
PDF="${PEEKNOOK_SYNC_PDF:-$ROOT/scripts/fixtures/sample.pdf}"

if [[ "$ROLE" != "push" && "$ROLE" != "pull" && "$ROLE" != "auto" ]]; then
  echo "Usage: $0 push|pull|auto" >&2
  echo "  auto — push then pull on this machine (field-test simulation)" >&2
  echo "Set PEEKNOOK_CLOUD_EMAIL and PEEKNOOK_CLOUD_PASSWORD (optional for auto)" >&2
  exit 1
fi

if [[ "$ROLE" == "auto" ]]; then
  export PEEKNOOK_CLOUD_EMAIL="${PEEKNOOK_CLOUD_EMAIL:-auto-$(date +%s)@example.com}"
  export PEEKNOOK_CLOUD_PASSWORD="${PEEKNOOK_CLOUD_PASSWORD:-verify-pass-123}"
  echo "== Auto field test (push + pull) =="
  PUSH_OUT=$(bash "$0" push)
  echo "$PUSH_OUT"
  export PEEKNOOK_SYNC_SOURCE_ID
  PEEKNOOK_SYNC_SOURCE_ID=$(echo "$PUSH_OUT" | grep '^source_id=' | cut -d= -f2-)
  export PEEKNOOK_SYNC_SOURCE_ID
  bash "$0" pull
  echo "OK — auto field test passed"
  exit 0
fi

for var in PEEKNOOK_CLOUD_EMAIL PEEKNOOK_CLOUD_PASSWORD; do
  if [[ -z "${!var:-}" ]]; then
    echo "Set $var" >&2
    exit 1
  fi
done

curl -sf "$API/api/peeknook/setup-status" >/dev/null || {
  echo "FAIL: start API — ./scripts/peeknook-backend.sh" >&2
  exit 1
}
curl -sf "$CLOUD/health" >/dev/null || {
  echo "FAIL: cloud unreachable at $CLOUD" >&2
  exit 1
}

echo "Login cloud as ${PEEKNOOK_CLOUD_EMAIL}..."
TOKEN=$(curl -sf -X POST "$CLOUD/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$PEEKNOOK_CLOUD_EMAIL\",\"password\":\"$PEEKNOOK_CLOUD_PASSWORD\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null) || true

if [[ -z "${TOKEN:-}" ]]; then
  TOKEN=$(curl -sf -X POST "$CLOUD/auth/register" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$PEEKNOOK_CLOUD_EMAIL\",\"password\":\"$PEEKNOOK_CLOUD_PASSWORD\"}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
fi

curl -sf -X PUT "$API/api/peeknook/settings" \
  -H 'Content-Type: application/json' \
  -d "{\"cloud_url\":\"$CLOUD\",\"cloud_token\":\"$TOKEN\",\"auto_sync\":false}" >/dev/null

if [[ "$ROLE" == "push" ]]; then
  echo "== Machine A: upload + push =="
  NB=$(curl -sf -X POST "$API/api/notebooks" \
    -H 'Content-Type: application/json' \
    -d '{"name":"Two-Mac Sync","description":"machine A"}')
  NB_ID=$(echo "$NB" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

  SRC=$(curl -sf -X POST "$API/api/sources" \
    -F "type=upload" \
    -F "notebook_id=$NB_ID" \
    -F "notebooks=[\"$NB_ID\"]" \
    -F "title=Two-Mac PDF" \
    -F "embed=false" \
    -F "async_processing=true" \
    -F "delete_source=false" \
    -F "file=@$PDF;type=application/pdf")
  SRC_ID=$(echo "$SRC" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

  PUSH=$(curl -sf -X POST "$API/api/peeknook/sync/push" \
    -H 'Content-Type: application/json' \
    -d "{\"cloud_url\":\"$CLOUD\",\"token\":\"$TOKEN\"}")
  BLOBS=$(echo "$PUSH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('blobs',0))")

  echo "notebook_id=$NB_ID"
  echo "source_id=$SRC_ID"
  echo "blobs_pushed=$BLOBS"
  echo ""
  echo "On machine B run:"
  echo "  export PEEKNOOK_CLOUD_EMAIL=$PEEKNOOK_CLOUD_EMAIL"
  echo "  export PEEKNOOK_CLOUD_PASSWORD=…"
  echo "  export PEEKNOOK_CLOUD_URL=$CLOUD"
  echo "  export PEEKNOOK_SYNC_SOURCE_ID=$SRC_ID"
  echo "  ./scripts/peeknook-pdf-sync-two-mac.sh pull"

  [[ "$BLOBS" -ge 1 ]] || { echo "FAIL: blob not pushed" >&2; exit 1; }
  echo "OK — machine A done"
  exit 0
fi

echo "== Machine B: pull + import =="
SRC_ID="${PEEKNOOK_SYNC_SOURCE_ID:-}"
if [[ -n "$SRC_ID" ]]; then
  SYNC_DB="${PEEKNOOK_SYNC_DB:-$HOME/Library/Application Support/PeekNook/sync_events.sqlite}"
  if [[ -f "$SYNC_DB" ]]; then
    sqlite3 "$SYNC_DB" "DELETE FROM cloud_imports WHERE cloud_object_id='$SRC_ID';" || true
  fi
fi

PULL=$(curl -sf -X POST "$API/api/peeknook/sync/pull" \
  -H 'Content-Type: application/json' \
  -d "{\"cloud_url\":\"$CLOUD\",\"token\":\"$TOKEN\"}")

IMPORT_OK=$(echo "$PULL" | python3 -c "
import sys, json
data = json.load(sys.stdin)
imports = data.get('blob_imports') or []
print('yes' if any(r.get('status') in ('imported', 'already_imported') for r in imports) else 'no')
")

if [[ "$IMPORT_OK" != "yes" ]]; then
  echo "FAIL: no blob imported on machine B" >&2
  echo "$PULL" | python3 -m json.tool | head -30 >&2
  exit 1
fi

echo "blob_imports:"
echo "$PULL" | python3 -c "import sys,json; [print(' ', r) for r in json.load(sys.stdin).get('blob_imports',[])]"
echo "OK — machine B done"
