#!/usr/bin/env bash
# POST a stub checkout.session.completed to local cloud Stripe webhook.
set -euo pipefail

CLOUD="${PEEKNOOK_CLOUD_URL:-http://127.0.0.1:${CLOUD_PORT:-8090}}"
USER_ID="${1:-demo-user-id}"
PLAN="${2:-pro}"

PAYLOAD=$(python3 -c "
import json
print(json.dumps({
  'type': 'checkout.session.completed',
  'data': {'object': {
    'client_reference_id': '$USER_ID',
    'metadata': {'plan_id': '$PLAN', 'user_id': '$USER_ID'},
    'customer': 'cus_test',
  }},
}))
")

echo "== Stripe webhook test =="
echo "POST $CLOUD/billing/webhook/stripe (plan=$PLAN user=$USER_ID)"
RESP=$(curl -sf -X POST "$CLOUD/billing/webhook/stripe" \
  -H 'Content-Type: application/json' \
  -d "$PAYLOAD" 2>&1) || {
  echo "FAIL: $RESP" >&2
  echo "Ensure cloud API includes billing router (restart: cd cloud && uvicorn api.main:app --port 8090)" >&2
  exit 1
}
echo "$RESP" | python3 -m json.tool
echo "OK — webhook stub accepted (dev mode without STRIPE_WEBHOOK_SECRET)"
