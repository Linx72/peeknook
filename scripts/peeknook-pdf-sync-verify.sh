#!/usr/bin/env bash
# Simulates Mac A (push PDF blob) → Mac B (pull + import) using one machine.
# Requires: PeekNook API (:5056), Cloud (:8090), sample PDF fixture.
#
# Usage: ./scripts/peeknook-pdf-sync-verify.sh [API_PORT] [CLOUD_PORT]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT="${1:-5056}"
CLOUD_PORT="${2:-8090}"
API="http://127.0.0.1:${API_PORT}"
CLOUD="http://127.0.0.1:${CLOUD_PORT}"
PDF="$ROOT/scripts/fixtures/sample.pdf"
EMAIL="pdf-sync-$(date +%s)@example.com"
PASS="verify-pass-123"

echo "== PeekNook PDF sync verify (Mac A → Mac B simulation) =="

curl -sf "$API/api/peeknook/setup-status" >/dev/null || {
  echo "FAIL: API not running on $API" >&2
  exit 1
}
curl -sf "$CLOUD/health" >/dev/null || {
  echo "FAIL: Cloud not running on $CLOUD" >&2
  exit 1
}
[[ -f "$PDF" ]] || { echo "FAIL: missing $PDF" >&2; exit 1; }

ORIG_SHA=$(shasum -a 256 "$PDF" | awk '{print $1}')

echo "[1/7] Cloud user + desktop settings…"
TOKEN=$(curl -sf -X POST "$CLOUD/auth/register" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -sf -X PUT "$API/api/peeknook/settings" \
  -H 'Content-Type: application/json' \
  -d "{\"cloud_url\":\"$CLOUD\",\"cloud_token\":\"$TOKEN\",\"auto_sync\":false}" >/dev/null

echo "[2/7] Create notebook…"
NB=$(curl -sf -X POST "$API/api/notebooks" \
  -H 'Content-Type: application/json' \
  -d '{"name":"PDF Sync Test","description":"automated verify"}')
NB_ID=$(echo "$NB" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "[3/7] Upload PDF via API (machine A)…"
SRC=$(curl -sf -X POST "$API/api/sources" \
  -F "type=upload" \
  -F "notebook_id=$NB_ID" \
  -F "notebooks=[\"$NB_ID\"]" \
  -F "title=Sync Verify PDF" \
  -F "embed=false" \
  -F "async_processing=true" \
  -F "delete_source=false" \
  -F "file=@$PDF;type=application/pdf")
SRC_ID=$(echo "$SRC" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  source_id=$SRC_ID"

echo "[4/7] Push sync + blob to cloud…"
PUSH=$(curl -sf -X POST "$API/api/peeknook/sync/push" \
  -H 'Content-Type: application/json' \
  -d "{\"cloud_url\":\"$CLOUD\",\"token\":\"$TOKEN\"}")
BLOBS=$(echo "$PUSH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('blobs',0))")
echo "  blobs uploaded: $BLOBS"
if [[ "$BLOBS" -lt 1 ]]; then
  echo "FAIL: no blob uploaded to cloud" >&2
  exit 1
fi

CLOUD_BLOBS=$(curl -sf "$CLOUD/blobs?object_id=$SRC_ID" \
  -H "Authorization: Bearer $TOKEN")
CLOUD_COUNT=$(echo "$CLOUD_BLOBS" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('items',[])))")
if [[ "$CLOUD_COUNT" -lt 1 ]]; then
  echo "FAIL: cloud has no blob for $SRC_ID" >&2
  exit 1
fi
BLOB_ID=$(echo "$CLOUD_BLOBS" | python3 -c "import sys,json; print(json.load(sys.stdin)['items'][0]['id'])")

echo "[5/7] Simulate machine B — clear import cache…"
SYNC_DB="${PEEKNOOK_SYNC_DB:-$HOME/Library/Application Support/PeekNook/sync_events.sqlite}"
if [[ -f "$SYNC_DB" ]]; then
  sqlite3 "$SYNC_DB" "DELETE FROM cloud_imports WHERE cloud_object_id='$SRC_ID';" || true
fi

echo "[6/7] Pull sync (machine B imports PDF from cloud)…"
PULL=$(curl -sf -X POST "$API/api/peeknook/sync/pull" \
  -H 'Content-Type: application/json' \
  -d "{\"cloud_url\":\"$CLOUD\",\"token\":\"$TOKEN\"}")

IMPORT_OK=$(echo "$PULL" | python3 -c "
import sys, json
data = json.load(sys.stdin)
imports = data.get('blob_imports') or []
ok = any(r.get('status') in ('imported', 'already_imported') for r in imports)
print('yes' if ok else 'no')
")

if [[ "$IMPORT_OK" != "yes" ]]; then
  echo "FAIL: blob import did not succeed" >&2
  echo "$PULL" | python3 -m json.tool | head -40 >&2
  exit 1
fi
echo "  blob import: ok"

echo "[7/7] Verify downloaded blob bytes…"
DL="$ROOT/.tmp-pdf-sync-verify.bin"
curl -sf "$CLOUD/blobs/$BLOB_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -o "$DL"
DL_SHA=$(shasum -a 256 "$DL" | awk '{print $1}')
rm -f "$DL"

if [[ "$ORIG_SHA" != "$DL_SHA" ]]; then
  echo "FAIL: blob checksum mismatch" >&2
  exit 1
fi

echo "OK — PDF sync verify passed (push blob + pull import + checksum)"
