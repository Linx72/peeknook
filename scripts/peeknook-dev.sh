#!/usr/bin/env bash
# PeekNook default dev stack: embedded SurrealDB + API + worker + Vite UI (:5173).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env — set OPEN_NOTEBOOK_ENCRYPTION_KEY before using credentials."
fi

export PEEKNOOK_EMBEDDED_DB=true
export API_PORT="${API_PORT:-5056}"

cleanup() {
  echo "Stopping PeekNook dev processes..."
  pkill -f "run_api.py" 2>/dev/null || true
  pkill -f "surreal-commands-worker" 2>/dev/null || true
  pkill -f "vite" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "🚀 PeekNook dev (embedded DB + Vite UI)..."
bash "$ROOT/scripts/peeknook-backend.sh"

if [[ ! -d "$ROOT/ui/node_modules" ]]; then
  echo "Installing UI dependencies..."
  (cd "$ROOT/ui" && npm install)
fi

echo "✅ API:  http://127.0.0.1:${API_PORT}/docs"
echo "✅ UI:   http://127.0.0.1:5173"

cd "$ROOT/ui"
exec npm run dev
