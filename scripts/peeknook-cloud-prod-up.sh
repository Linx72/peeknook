#!/usr/bin/env bash
# Start PeekNook Cloud production stack (Postgres + MinIO + API).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/cloud"

ENV_FILE=".env.prod"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Create $ENV_FILE from .env.prod.example and set secrets." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source "$ENV_FILE"
set +a

echo "== PeekNook cloud prod up =="
docker compose -f docker-compose.prod.yml up -d --build

PORT="${CLOUD_PORT:-8090}"
for _ in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    curl -sf "http://127.0.0.1:${PORT}/health" | python3 -m json.tool
    echo "OK — cloud on http://127.0.0.1:${PORT}"
    exit 0
  fi
  sleep 2
done

echo "WARN: health check timeout — docker compose -f docker-compose.prod.yml logs cloud-api" >&2
exit 1
