#!/usr/bin/env bash
# PeekNook Desktop dev: embedded backend + Vite UI (no Next.js required).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

export PEEKNOOK_EMBEDDED_DB=true
export API_PORT="${API_PORT:-5056}"
export PEEKNOOK_API_PORT="$API_PORT"

"$ROOT/scripts/peeknook-backend.sh"

if ! curl -sf http://127.0.0.1:5173 >/dev/null 2>&1; then
  echo "Starting PeekNook Vite UI on :5173..."
  cd "$ROOT/ui"
  exec npm run dev
else
  echo "UI already on :5173"
  exec sleep infinity
fi
