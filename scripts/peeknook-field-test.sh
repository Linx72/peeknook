#!/usr/bin/env bash
# One-machine field test: sync verify + PDF auto push/pull + QA sign-off.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== PeekNook field test =="

./scripts/peeknook-sync-verify.sh
./scripts/peeknook-pdf-sync-verify.sh
./scripts/peeknook-pdf-sync-two-mac.sh auto
./scripts/peeknook-two-mac-qa.sh
./scripts/peeknook-qa-signoff.sh

echo "OK — field test complete"
