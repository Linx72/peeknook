#!/usr/bin/env bash
# Print ship gates status from local API (requires peeknook-backend.sh).
set -euo pipefail

API="${PEEKNOOK_API_URL:-http://127.0.0.1:${API_PORT:-5056}}"

curl -sf "$API/api/peeknook/ship-status" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f\"PeekNook v{d.get('version', '?')} — gates {d.get('gates_done', 0)}/{d.get('gates_total', 0)}\")
for g in d.get('gates', []):
    mark = '✓' if g.get('done') else '○'
    cmd = g.get('command', '')
    print(f\"  {mark} {g['id']}\" + (f\"  → {cmd}\" if cmd and not g.get('done') else ''))
sw = d.get('stripe_webhook')
if sw is not None:
    print(f\"  stripe_webhook: {sw}\")
"
