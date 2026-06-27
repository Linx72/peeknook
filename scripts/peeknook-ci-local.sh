#!/usr/bin/env bash
# Local mirror of .github/workflows/peeknook-ci.yml (UI + extension + cloud import).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== PeekNook CI (local) =="

echo "▶ Vite UI"
(cd ui && npm ci && npm run build)

echo "▶ TermitPro extension"
(cd integrations/termitpro-vscode && npm ci && npm run compile)

echo "▶ Cloud API import"
(
  cd cloud
  if [[ -d .venv ]]; then source .venv/bin/activate; fi
  python3 -m pip install -q -r requirements.txt 2>/dev/null || pip3 install -q -r requirements.txt
  python3 -c "from api.database import init_db; init_db(); print('cloud ok')"
)

echo "▶ Sidecar"
bash scripts/peeknook-ensure-sidecar.sh

echo "OK — local CI passed"
