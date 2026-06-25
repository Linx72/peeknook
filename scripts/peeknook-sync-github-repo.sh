#!/usr/bin/env bash
# Push a clean tree to Linx72/peeknook when local main history diverged from export.
# Uses git archive + working-tree overlay (uncommitted scripts/docs included).
#
# Usage:
#   ./scripts/peeknook-sync-github-repo.sh          # dry-run summary
#   PEEKNOOK_SYNC_PUSH=1 ./scripts/peeknook-sync-github-repo.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE="${PEEKNOOK_GIT_REMOTE:-peeknook}"
BRANCH="${PEEKNOOK_SYNC_BRANCH:-main}"
EXPORT="${PEEKNOOK_SYNC_EXPORT:-/tmp/peeknook-github-sync-$$}"

cd "$ROOT"

if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
  echo "Remote '$REMOTE' not found. Set PEEKNOOK_GIT_REMOTE." >&2
  exit 1
fi

mkdir -p "$EXPORT"
trap 'rm -rf "$EXPORT"' EXIT

# Tracked files at HEAD
git archive HEAD | tar -x -C "$EXPORT"

# Overlay local changes (scripts, docs — skip dev DB/blobs)
for path in \
  README.md \
  .gitignore \
  docs/PEEKNOOK-ROADMAP.md \
  scripts/peeknook-local-release.sh \
  scripts/peeknook-publish-local-release.sh \
  scripts/peeknook-sync-github-repo.sh \
  scripts/peeknook-notarize-macos.sh \
  .github/workflows/peeknook-release.yml \
  desktop/src-tauri/binaries/.gitkeep; do
  if [[ -e "$ROOT/$path" ]]; then
    mkdir -p "$EXPORT/$(dirname "$path")"
    cp -R "$ROOT/$path" "$EXPORT/$path"
  fi
done

# Sidecar binary is built by scripts/build-backend.sh (CI + local release); keep repo small.
rm -f "$EXPORT"/desktop/src-tauri/binaries/peeknook-api-* 2>/dev/null || true
mkdir -p "$EXPORT/desktop/src-tauri/binaries"
touch "$EXPORT/desktop/src-tauri/binaries/.gitkeep"

cd "$EXPORT"
git init -q
if command -v git-lfs >/dev/null 2>&1; then
  git lfs install --local >/dev/null 2>&1 || true
fi
git checkout -b "$BRANCH" 2>/dev/null || git checkout "$BRANCH"
git add -A
git commit -q -m "PeekNook sync — local release scripts and docs ($(date +%Y-%m-%d))."

echo "Export ready: $EXPORT"
echo "Files: $(git ls-files | wc -l | tr -d ' ') tracked"
echo "Remote: $(git -C "$ROOT" remote get-url "$REMOTE")"

if [[ "${PEEKNOOK_SYNC_PUSH:-}" != "1" ]]; then
  echo ""
  echo "Dry-run. To push:"
  echo "  PEEKNOOK_SYNC_PUSH=1 $0"
  exit 0
fi

git remote add target "$(git -C "$ROOT" remote get-url "$REMOTE")"
git push target "$BRANCH" --force
echo "OK — pushed $BRANCH to $REMOTE"
