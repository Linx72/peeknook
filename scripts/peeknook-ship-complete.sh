#!/usr/bin/env bash
# Run all automatable ship gates; print manual checklist for the rest.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== PeekNook ship complete (automated) =="
bash scripts/peeknook-ship-check.sh
bash scripts/peeknook-verify-release.sh

SIGNOFF="${PEEKNOOK_QA_SIGNOFF:-$HOME/Library/Application Support/PeekNook/qa-signoff.json}"
PHYSICAL=""
if [[ -f "$SIGNOFF" ]]; then
  PHYSICAL=$(python3 -c "
import json, pathlib
p = pathlib.Path('$SIGNOFF')
if p.exists():
    d = json.loads(p.read_text())
    pt = d.get('physical_two_mac')
    print('yes' if isinstance(pt, dict) and pt.get('completed_at') else 'no')
" 2>/dev/null || echo "no")
fi

echo ""
echo "▶ Cloud / Stripe (when prod configured)"
if [[ -f cloud/.env.prod ]]; then
  echo "  ✓ cloud/.env.prod exists"
  bash scripts/peeknook-stripe-verify.sh 2>/dev/null && echo "  ✓ Stripe verify" || echo "  ○ Stripe verify failed — check STRIPE_* in .env.prod"
else
  echo "  ○ cloud/.env.prod missing — copy from cloud/.env.prod.example for VPS"
fi
if [[ -f cloud/deploy/peeknook-cloud-deploy.tar.gz ]]; then
  echo "  ✓ deploy pack exists (peeknook-cloud-deploy-pack.sh)"
else
  echo "  ○ Run: ./scripts/peeknook-cloud-deploy-pack.sh"
fi

echo ""
echo "== Manual gates =="
if [[ "$PHYSICAL" == "yes" ]]; then
  echo "  ✓ Physical two-Mac recorded in qa-signoff.json"
else
  echo "  ○ Physical two-Mac — machine A: peeknook-pdf-sync-two-mac.sh push"
  echo "      machine B: ./scripts/peeknook-two-mac-machine-b.sh --record"
fi

SECRETS=$(gh secret list --repo "$(bash scripts/peeknook-github-repo.sh)" 2>/dev/null | awk '{print $1}' || true)
VERSION=$(python3 -c "import json; print(json.load(open('desktop/src-tauri/tauri.conf.json'))['version'])")
if echo "$SECRETS" | grep -q '^APPLE_ID$'; then
  echo "  ✓ APPLE_ID secret set — notarization can run on next CI release"
else
  echo "  ○ Apple notarization — set APPLE_SIGNING_IDENTITY, APPLE_ID, APPLE_PASSWORD, APPLE_TEAM_ID in repo secrets"
  echo "      then: ./scripts/peeknook-retry-release-ci.sh v${VERSION}"
fi

echo ""
echo "OK — automated ship complete"
