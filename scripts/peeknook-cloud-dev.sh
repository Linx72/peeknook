#!/usr/bin/env bash
# Start PeekNook Cloud for local dev (SQLite, billing + sync on :8090).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/cloud"
PORT="${CLOUD_PORT:-8090}"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python3 -c "from api.database import init_db; init_db()"

echo "PeekNook Cloud dev → http://127.0.0.1:${PORT}/docs"
exec uvicorn api.main:app --reload --host 127.0.0.1 --port "$PORT"
