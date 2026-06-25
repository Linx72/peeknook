#!/usr/bin/env bash
# Run all automatable PeekNook gates in one shot (verify, health, field test, manual prep).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== PeekNook do-all =="
echo ""

bash scripts/peeknook-verify-release.sh
echo ""

PEEKNOOK_HEALTH_SKIP_RELEASE=1 bash scripts/peeknook-health-all.sh
echo ""

bash scripts/peeknook-ship-check.sh
echo ""

bash scripts/peeknook-manual-gates.sh
echo ""

bash scripts/peeknook-ship-complete.sh
echo ""
echo "OK — do-all complete"
