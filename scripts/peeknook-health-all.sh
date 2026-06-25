#!/usr/bin/env bash
# One-shot health: desktop API, cloud, Ollama, optional release manifest.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="${PEEKNOOK_API_URL:-http://127.0.0.1:${API_PORT:-5056}}"
CLOUD="${PEEKNOOK_CLOUD_URL:-http://127.0.0.1:${CLOUD_PORT:-8090}}"

echo "== PeekNook health all =="

echo "▶ Desktop API"
curl -sf "$API/api/peeknook/setup-status" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"  product={d['product']} notebooks={d['notebook_count']} sync_pending={d['sync_pending']} cloud={d.get('cloud_configured')}\")
"

echo "▶ Cloud"
curl -sf "$CLOUD/health" | python3 -m json.tool
if curl -sf "$CLOUD/openapi.json" | python3 -c "
import sys, json
paths = json.load(sys.stdin).get('paths', {})
ok = '/billing/webhook/stripe' in paths
print('  billing webhook route:', 'OK' if ok else 'MISSING — restart: ./scripts/peeknook-cloud-dev.sh')
sys.exit(0 if ok else 1)
" 2>/dev/null; then true; else true; fi

echo "▶ Two-Mac handoff"
curl -sf "$API/api/peeknook/two-mac-handoff" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('  available:', d.get('available'), 'source:', d.get('source_id') or '—')
"

echo "▶ Ollama"
curl -sf "$API/api/peeknook/ollama/status" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('  reachable:', d.get('reachable'), 'models:', d.get('model_count'))
"

if [[ "${PEEKNOOK_HEALTH_SKIP_RELEASE:-}" != "1" ]]; then
  bash "$ROOT/scripts/peeknook-verify-release.sh" 2>&1 | tail -3
fi

echo "OK — health all"
