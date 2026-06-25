#!/usr/bin/env bash
# Upload cloud deploy pack to VPS and start production stack (optional automation).
#
# Requires:
#   PEEKNOOK_VPS_SSH=user@host          # or PEEKNOOK_VPS_HOST + PEEKNOOK_VPS_USER
#   PEEKNOOK_VPS_DIR=~/peeknook-cloud   # remote directory (default)
#
# Usage:
#   ./scripts/peeknook-vps-deploy.sh              # dry-run hints
#   PEEKNOOK_VPS_SSH=root@1.2.3.4 ./scripts/peeknook-vps-deploy.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PACK="${PEEKNOOK_CLOUD_DEPLOY_PACK:-$HOME/Library/Application Support/PeekNook/peeknook-cloud-deploy.tgz}"
REMOTE_DIR="${PEEKNOOK_VPS_DIR:-~/peeknook-cloud}"
SSH_TARGET="${PEEKNOOK_VPS_SSH:-}"

if [[ -z "$SSH_TARGET" && -n "${PEEKNOOK_VPS_HOST:-}" ]]; then
  SSH_TARGET="${PEEKNOOK_VPS_USER:-root}@${PEEKNOOK_VPS_HOST}"
fi

echo "== PeekNook VPS deploy =="

if [[ ! -f "$PACK" ]]; then
  echo "Building deploy pack…"
  bash "$ROOT/scripts/peeknook-cloud-deploy-pack.sh"
fi

if [[ -z "$SSH_TARGET" ]]; then
  cat <<EOF
Dry-run — set SSH target to deploy:

  export PEEKNOOK_VPS_SSH=user@your-vps-ip
  $0

Steps performed remotely:
  1. mkdir -p $REMOTE_DIR
  2. scp deploy pack → $REMOTE_DIR/
  3. tar -xzf peeknook-cloud-deploy.tgz
  4. cp .env.prod.example .env.prod (if missing)
  5. docker compose -f docker-compose.prod.yml up -d --build
  6. curl http://127.0.0.1:8090/health

Then TLS: ./scripts/peeknook-cloud-certbot-hints.sh
EOF
  exit 0
fi

echo "Target: $SSH_TARGET"
echo "Pack:   $PACK"
echo "Dir:    $REMOTE_DIR"
echo ""

scp "$PACK" "${SSH_TARGET}:${REMOTE_DIR}/peeknook-cloud-deploy.tgz"
ssh "$SSH_TARGET" bash -s <<REMOTE
set -euo pipefail
mkdir -p ${REMOTE_DIR}
cd ${REMOTE_DIR}
tar -xzf peeknook-cloud-deploy.tgz
if [[ ! -f .env.prod ]]; then
  cp .env.prod.example .env.prod
  echo "WARN: created .env.prod from example — edit secrets on VPS before production use"
fi
docker compose -f docker-compose.prod.yml up -d --build
for i in \$(seq 1 30); do
  if curl -sf http://127.0.0.1:\${CLOUD_PORT:-8090}/health >/dev/null 2>&1; then
    curl -sf http://127.0.0.1:\${CLOUD_PORT:-8090}/health
    echo ""
    echo "OK — cloud API healthy on VPS"
    exit 0
  fi
  sleep 2
done
echo "WARN: health timeout — docker compose -f docker-compose.prod.yml logs cloud-api" >&2
exit 1
REMOTE

echo "OK — VPS deploy complete"
echo "Set desktop Cloud URL to https://your-domain (after certbot)"
