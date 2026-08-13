#!/usr/bin/env bash
# Bootstrap cloud/.env.prod from example with a short Stripe/VPS checklist.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV="$ROOT/cloud/.env.prod"
EXAMPLE="$ROOT/cloud/.env.prod.example"

echo "== PeekNook cloud .env.prod init =="

if [[ -f "$ENV" ]]; then
  echo "Exists: $ENV"
else
  cp "$EXAMPLE" "$ENV"
  echo "Created $ENV from example — edit secrets before VPS deploy."
fi

missing=()
for key in POSTGRES_PASSWORD JWT_SECRET MINIO_SECRET_KEY STRIPE_SECRET_KEY STRIPE_PRICE_PRO; do
  if ! grep -q "^${key}=.\+" "$ENV" 2>/dev/null || grep -q "^${key}=$" "$ENV"; then
    missing+=("$key")
  fi
done

if ((${#missing[@]})); then
  echo ""
  echo "Unset or empty keys:"
  printf '  - %s\n' "${missing[@]}"
  echo ""
  echo "After edit: ./scripts/peeknook-cloud-prod-up.sh"
  echo "Verify:     ./scripts/peeknook-stripe-verify.sh"
else
  echo "All required keys appear set."
fi

echo "OK — env prod init"
