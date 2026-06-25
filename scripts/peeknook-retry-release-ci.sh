#!/usr/bin/env bash
# Re-point release tag to main and re-run PeekNook Release CI (after APPLE_* secrets added).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

REPO="${PEEKNOOK_GITHUB_REPO:-$(bash scripts/peeknook-github-repo.sh)}"
TAG="${1:-v0.2.0}"

SHA=$(gh api "repos/${REPO}/git/ref/heads/main" -q .object.sha)
echo "Retag $TAG → main ($SHA)"
gh api --method PATCH "repos/${REPO}/git/refs/tags/${TAG}" -f sha="$SHA" -F force=true >/dev/null

RUN=$(gh workflow run "PeekNook Release" --repo "$REPO" --ref "$TAG" 2>&1)
echo "$RUN"
echo "Watch: gh run list --repo $REPO --workflow peeknook-release.yml --limit 1"
