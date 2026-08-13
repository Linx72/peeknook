#!/usr/bin/env bash
# Tag and push a PeekNook source release to the selected RepoBase remote.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${1:-}"
REMOTE="${PEEKNOOK_GIT_REMOTE:-repobase}"

if [[ -z "$TAG" ]]; then
  echo "Usage: $0 v0.2.0" >&2
  exit 1
fi

cd "$ROOT"

if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
  echo "Release remote '$REMOTE' is not configured." >&2
  echo "Run scripts/peeknook-repobase-preflight.sh before publishing." >&2
  exit 1
fi

REMOTE_URL="$(git remote get-url "$REMOTE")"
if [[ "$REMOTE_URL" != *"repobase.ru"* ]]; then
  bash scripts/peeknook-legacy-github-guard.sh
fi

bash scripts/peeknook-release-tag.sh "$TAG"
BRANCH="$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
if [[ -z "$BRANCH" ]]; then
  echo "Release push blocked: detached HEAD has no source branch." >&2
  exit 1
fi

git push --atomic "$REMOTE" "HEAD:refs/heads/$BRANCH" "refs/tags/$TAG"
echo "Pushed $BRANCH and $TAG atomically to $REMOTE — verify the RepoBase tag and Forgejo Actions state"
