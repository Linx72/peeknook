#!/usr/bin/env bash
# Check Stripe billing configuration on running PeekNook Cloud.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${CLOUD_PORT:-8090}"
CLOUD="${PEEKNOOK_CLOUD_URL:-http://127.0.0.1:${PORT}}"

echo "== PeekNook Stripe verify =="
echo "Cloud: $CLOUD"

curl -sf "$CLOUD/health" >/dev/null || {
  echo "FAIL: cloud not reachable — ./scripts/peeknook-cloud-prod-up.sh or uvicorn" >&2
  exit 1
}

PLANS=$(curl -sf "$CLOUD/billing/plans")
echo "$PLANS" | python3 -m json.tool | head -20

ENV_FILE="$ROOT/cloud/.env.prod"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ENV_FILE"
  set +a
fi

if [[ -n "${STRIPE_SECRET_KEY:-}" && -n "${STRIPE_PRICE_PRO:-}" ]]; then
  echo "  STRIPE_SECRET_KEY: set"
  echo "  STRIPE_PRICE_PRO: set"
  echo "  Live checkout: enabled (open Billing in UI after cloud login)"
else
  echo "  WARN: STRIPE_SECRET_KEY or STRIPE_PRICE_PRO unset — dev-mode plan upgrade only"
  echo "  Set in cloud/.env.prod and restart cloud-api"
fi

echo "OK — stripe verify"
