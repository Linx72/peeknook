#!/usr/bin/env bash
# PeekNook backend: embedded SurrealDB (default) or Docker fallback + API + worker.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

# A packaged desktop launch token must take precedence over values from .env.
if [[ -n "${PEEKNOOK_RUNTIME_TOKEN:-}" ]]; then
  export API_PORT="${PEEKNOOK_RUNTIME_API_PORT:?desktop runtime API port is missing}"
  export OPEN_NOTEBOOK_PASSWORD="$PEEKNOOK_RUNTIME_TOKEN"
  export CORS_ORIGINS="${PEEKNOOK_RUNTIME_CORS_ORIGINS:-tauri://localhost,http://tauri.localhost,https://tauri.localhost}"
fi

API_PORT="${API_PORT:-5056}"
EMBEDDED="${PEEKNOOK_EMBEDDED_DB:-true}"
SURREAL_PORT="${PEEKNOOK_SURREAL_PORT:-8001}"

if [[ "$EMBEDDED" == "true" ]]; then
  export SURREAL_URL="ws://127.0.0.1:${SURREAL_PORT}/rpc"
  export SURREAL_USER="${SURREAL_USER:-root}"
  export SURREAL_PASSWORD="${SURREAL_PASSWORD:-root}"
  export SURREAL_NAMESPACE="${SURREAL_NAMESPACE:-peeknook}"
  export SURREAL_DATABASE="${SURREAL_DATABASE:-peeknook}"
  bash "$ROOT/scripts/peeknook-surreal-embedded.sh"
else
  if ! docker compose ps surrealdb 2>/dev/null | grep -q Up; then
    docker compose up -d surrealdb 2>/dev/null || true
    sleep 3
  fi
  export SURREAL_URL="${SURREAL_URL:-ws://localhost:8000/rpc}"
fi

if ! curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
  API_PORT="$API_PORT" uv run run_api.py &
  sleep 4
fi

if ! pgrep -f "surreal-commands-worker" >/dev/null 2>&1; then
  uv run --env-file .env surreal-commands-worker --import-modules commands &
fi

for _ in $(seq 1 40); do
  if curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
    exit 0
  fi
  sleep 1
done
echo "PeekNook backend failed on port ${API_PORT}" >&2
exit 1
