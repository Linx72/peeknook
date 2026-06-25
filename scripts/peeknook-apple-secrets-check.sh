#!/usr/bin/env bash
# Exit 0 when APPLE_ID GitHub secret is set for PeekNook release repo.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="${PEEKNOOK_GITHUB_REPO:-$(bash "$ROOT/scripts/peeknook-github-repo.sh")}"

if gh secret list --repo "$REPO" 2>/dev/null | awk '{print $1}' | grep -qx 'APPLE_ID'; then
  echo "OK — APPLE_ID secret set on $REPO"
  exit 0
fi

echo "WARN — APPLE_ID not set on $REPO" >&2
echo "Run: ./scripts/peeknook-apple-secrets-hints.sh" >&2
exit 1
