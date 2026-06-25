#!/usr/bin/env bash
# Open Notebook upstream dev (Docker SurrealDB + API + legacy removed).
# Use PeekNook: ./scripts/peeknook-dev.sh
set -e
echo "Legacy dev-init.sh — use ./scripts/peeknook-dev.sh for PeekNook (Vite UI)."
exec "$(dirname "$0")/peeknook-dev.sh"
