#!/usr/bin/env bash
# End-to-end sync smoke test: register cloud user, push/pull, verify API health.
# Usage: ./scripts/peeknook-sync-verify.sh [API_PORT] [CLOUD_PORT]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT="${1:-5056}"
CLOUD_PORT="${2:-8090}"
API="http://127.0.0.1:${API_PORT}"
CLOUD="http://127.0.0.1:${CLOUD_PORT}"
EMAIL="sync-verify-$(date +%s)@example.com"
PASS="verify-pass-123"

echo "== PeekNook sync verify =="
echo "API: $API  Cloud: $CLOUD"

curl -sf "$API/api/peeknook/setup-status" >/dev/null || {
  echo "FAIL: PeekNook API not running on $API" >&2
  exit 1
}
curl -sf "$CLOUD/health" >/dev/null || {
  echo "FAIL: Cloud not running on $CLOUD" >&2
  exit 1
}

echo "Register cloud user…"
TOKEN=$(curl -sf -X POST "$CLOUD/auth/register" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Configure desktop cloud settings…"
curl -sf -X PUT "$API/api/peeknook/settings" \
  -H 'Content-Type: application/json' \
  -d "{\"cloud_url\":\"$CLOUD\",\"cloud_token\":\"$TOKEN\",\"auto_sync\":false}" >/dev/null

echo "Push sync…"
PUSH=$(curl -sf -X POST "$API/api/peeknook/sync/push" \
  -H 'Content-Type: application/json' \
  -d "{\"cloud_url\":\"$CLOUD\",\"token\":\"$TOKEN\"}")
echo "  push: $PUSH"

echo "Pull sync…"
PULL=$(curl -sf -X POST "$API/api/peeknook/sync/pull" \
  -H 'Content-Type: application/json' \
  -d "{\"cloud_url\":\"$CLOUD\",\"token\":\"$TOKEN\"}")
echo "  pull events: $(echo "$PULL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('events',[])))")"

STATUS=$(curl -sf "$API/api/peeknook/sync/status")
echo "Sync status: $STATUS"

echo "OK — sync verify passed"
