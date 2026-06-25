#!/usr/bin/env bash
# Validate PeekNook Cloud production compose (config + optional health).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE="$ROOT/cloud/docker-compose.prod.yml"
ENV_FILE="$ROOT/cloud/.env.prod"
PORT="${CLOUD_PORT:-8090}"

cd "$ROOT/cloud"

echo "== PeekNook cloud prod verify =="

STUB=0
if [[ ! -f "$ENV_FILE" ]]; then
  echo "WARN: $ENV_FILE missing — stub from .env.prod.example for compose validate"
  cp .env.prod.example .env.prod
  STUB=1
fi

set -a
# shellcheck disable=SC1091
source .env.prod
set +a
docker compose -f docker-compose.prod.yml config >/dev/null
echo "  compose config: OK"
[[ "$STUB" == 1 ]] && rm -f .env.prod

if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
  curl -sf "http://127.0.0.1:${PORT}/health" | python3 -m json.tool
  echo "  health: OK"
else
  echo "  health: skip (cloud not running on :${PORT})"
  echo "  start: cd cloud && cp .env.prod.example .env.prod && docker compose -f docker-compose.prod.yml up -d"
fi

echo "OK — cloud prod verify"
