#!/usr/bin/env bash
# Run every automatable manual-gate prep step; print what still needs human action.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION=$(python3 -c "import json; print(json.load(open('desktop/src-tauri/tauri.conf.json'))['version'])")
TAG="v${VERSION}"

echo "== PeekNook manual gates wizard =="
echo "Version: $VERSION"
echo ""

run_step() {
  echo "▶ $1"
  shift
  if "$@"; then
    echo "  ✓ OK"
  else
    echo "  ○ skipped or failed (see above)"
  fi
  echo ""
}

run_step "Release verify" bash scripts/peeknook-verify-release.sh
run_step "Health (skip release)" env PEEKNOOK_HEALTH_SKIP_RELEASE=1 bash scripts/peeknook-health-all.sh
run_step "Cloud prod compose validate" bash scripts/peeknook-cloud-prod-verify.sh
run_step "Stripe billing" bash scripts/peeknook-stripe-verify.sh
run_step "Stripe webhook stub" bash scripts/peeknook-stripe-webhook-test.sh 2>/dev/null || true
run_step "Cloud deploy pack" bash scripts/peeknook-cloud-deploy-pack.sh
run_step "VPS deploy (dry-run or SSH)" bash scripts/peeknook-vps-deploy.sh
run_step "Apple secrets hints" bash scripts/peeknook-apple-secrets-hints.sh
run_step "Certbot hints" bash scripts/peeknook-cloud-certbot-hints.sh 2>/dev/null | head -15 || true

echo "== Still manual =="
echo "  1. Two-Mac: Mac A peeknook-pdf-sync-two-mac.sh push → Mac B peeknook-two-mac-machine-b.sh --record"
echo "  2. VPS: PEEKNOOK_VPS_SSH=user@host ./scripts/peeknook-vps-deploy.sh"
echo "  3. Stripe: edit cloud/.env.prod → restart cloud → peeknook-stripe-verify.sh"
echo "  4. Apple: gh secret set APPLE_* → peeknook-retry-release-ci.sh $TAG"
echo ""
echo "Settings UI → Ship checklist shows live gate status."
echo "OK — manual gates wizard complete"
