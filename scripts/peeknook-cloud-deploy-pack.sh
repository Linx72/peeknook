#!/usr/bin/env bash
# Pack cloud production files for VPS deploy (rsync/scp).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$HOME/Library/Application Support/PeekNook/peeknook-cloud-deploy.tgz}"

mkdir -p "$(dirname "$OUT")"
tar -czf "$OUT" \
  --exclude='__pycache__' \
  --exclude='.venv' \
  -C "$ROOT/cloud" \
  docker-compose.prod.yml \
  Dockerfile \
  requirements.txt \
  .env.prod.example \
  deploy \
  api

echo "== PeekNook cloud deploy pack =="
echo "Archive: $OUT ($(du -sh "$OUT" | cut -f1))"
echo ""
echo "On VPS:"
echo "  mkdir -p ~/peeknook-cloud && cd ~/peeknook-cloud"
echo "  scp user@host:'$OUT' ."
echo "  tar -xzf $(basename "$OUT")"
echo "  cp .env.prod.example .env.prod   # edit secrets"
echo "  docker compose -f docker-compose.prod.yml up -d --build"
echo "  curl http://127.0.0.1:8090/health"
echo ""
echo "Point desktop Settings → Cloud URL to https://your-domain:8090"
