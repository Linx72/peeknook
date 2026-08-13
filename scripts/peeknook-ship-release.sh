#!/usr/bin/env bash
# Bump version, run ship gates, sync GitHub, tag, and trigger Release CI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
bash scripts/peeknook-legacy-github-guard.sh

VER="${1:-}"
LOCAL="${PEEKNOOK_SHIP_LOCAL:-0}"

if [[ -z "$VER" ]]; then
  VER=$(bash scripts/peeknook-bump-version.sh 2>/dev/null | head -1)
  echo "Current: $VER — pass explicit version: $0 0.2.1" >&2
  exit 1
fi

TAG="v${VER#v}"
bash scripts/peeknook-bump-version.sh "$VER"

echo "== Ship gates =="
PEEKNOOK_HEALTH_SKIP_RELEASE=1 bash scripts/peeknook-ship-check.sh

REPO="${PEEKNOOK_GITHUB_REPO:-$(bash scripts/peeknook-github-repo.sh)}"
echo "== Sync $REPO main =="
PEEKNOOK_SYNC_PUSH=1 bash scripts/peeknook-sync-github-repo.sh

SHA=$(gh api "repos/${REPO}/git/ref/heads/main" -q .object.sha)
echo "== Tag $TAG @ $SHA =="
gh api --method PATCH "repos/${REPO}/git/refs/tags/${TAG}" -f sha="$SHA" -F force=true 2>/dev/null \
  || gh api -X POST "repos/${REPO}/git/refs" -f ref="refs/tags/${TAG}" -f sha="$SHA"

if [[ "$LOCAL" == "1" ]]; then
  PEEKNOOK_RELEASE_TAG="$TAG" bash scripts/peeknook-local-release.sh
  bash scripts/peeknook-publish-local-release.sh "$TAG"
else
  echo "== Trigger Release CI =="
  bash scripts/peeknook-retry-release-ci.sh "$TAG"
fi

echo "OK — $TAG ship pipeline started"
