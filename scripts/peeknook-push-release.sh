#!/usr/bin/env bash
# Tag and push a PeekNook release (triggers peeknook-release.yml).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${1:-}"
REMOTE="${PEEKNOOK_GIT_REMOTE:-peeknook}"

if [[ -z "$TAG" ]]; then
  echo "Usage: $0 v0.2.0" >&2
  exit 1
fi

cd "$ROOT"

if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
  REMOTE=origin
fi

bash scripts/peeknook-release-tag.sh "$TAG"
git push "$REMOTE" "$TAG"
git push "$REMOTE" HEAD 2>/dev/null || true
echo "Pushed $TAG to $REMOTE — watch GitHub Actions for peeknook-release workflow"
