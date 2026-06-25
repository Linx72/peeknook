#!/usr/bin/env bash
# Full local stack: Cloud (:8090) + desktop API (:5056) + Vite UI (:5173).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env — set OPEN_NOTEBOOK_ENCRYPTION_KEY"
fi

export PEEKNOOK_EMBEDDED_DB=true
export API_PORT="${API_PORT:-5056}"
export CLOUD_PORT="${CLOUD_PORT:-8090}"

cleanup() {
  echo "Stopping PeekNook stack…"
  pkill -f "uvicorn api.main:app" 2>/dev/null || true
  pkill -f "run_api.py" 2>/dev/null || true
  pkill -f "surreal-commands-worker" 2>/dev/null || true
  pkill -f "vite" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if ! curl -sf "http://127.0.0.1:${CLOUD_PORT}/health" >/dev/null 2>&1; then
  echo "Starting PeekNook Cloud…"
  CLOUD_PORT="$CLOUD_PORT" bash "$ROOT/scripts/peeknook-cloud-dev.sh" &
  for _ in $(seq 1 30); do
    curl -sf "http://127.0.0.1:${CLOUD_PORT}/health" >/dev/null 2>&1 && break
    sleep 1
  done
fi

bash "$ROOT/scripts/peeknook-backend.sh"

if [[ ! -d "$ROOT/ui/node_modules" ]]; then
  (cd "$ROOT/ui" && npm install)
fi

echo "✅ Cloud: http://127.0.0.1:${CLOUD_PORT}/docs"
echo "✅ API:   http://127.0.0.1:${API_PORT}/docs"
echo "✅ UI:    http://127.0.0.1:5173"

cd "$ROOT/ui"
exec npm run dev
