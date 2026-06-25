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
copy_worktree_path() {
  local path="$1"
  if [[ ! -e "$ROOT/$path" ]]; then
    return 0
  fi
  mkdir -p "$EXPORT/$(dirname "$path")"
  cp -R "$ROOT/$path" "$EXPORT/$path"
}

for path in \
  README.md \
  .gitignore \
  desktop/src-tauri/tauri.conf.json \
  ui/package.json \
  desktop/package.json \
  docs/PEEKNOOK-ROADMAP.md \
  scripts/peeknook-local-release.sh \
  scripts/peeknook-publish-local-release.sh \
  scripts/peeknook-sync-github-repo.sh \
  scripts/peeknook-notarize-macos.sh \
  scripts/peeknook-ship-check.sh \
  scripts/peeknook-verify-release.sh \
  scripts/peeknook-ship-complete.sh \
  scripts/peeknook-ensure-sidecar.sh \
  scripts/peeknook-retry-release-ci.sh \
  scripts/peeknook-ci-local.sh \
  scripts/peeknook-cloud-prod-verify.sh \
  scripts/peeknook-cloud-prod-up.sh \
  scripts/peeknook-stripe-verify.sh \
  scripts/peeknook-stripe-webhook-test.sh \
  scripts/peeknook-apple-secrets-hints.sh \
  scripts/peeknook-pdf-sync-two-mac.sh \
  scripts/peeknook-cloud-deploy-pack.sh \
  scripts/peeknook-health-all.sh \
  scripts/peeknook-two-mac-machine-b.sh \
  scripts/peeknook-cloud-certbot-hints.sh \
  scripts/peeknook-cloud-dev.sh \
  scripts/peeknook-dev-full.sh \
  scripts/peeknook-ship-release.sh \
  scripts/peeknook-bump-version.sh \
  .github/workflows/peeknook-release.yml \
  desktop/src-tauri/binaries/.gitkeep; do
  copy_worktree_path "$path"
done

# Auto-overlay uncommitted PeekNook UI/cloud/API (prevents missing-file CI failures)
for scope in ui/src cloud/api cloud/deploy api/routers; do
  {
    git diff --name-only HEAD -- "$scope" 2>/dev/null || true
    git ls-files --others --exclude-standard "$scope" 2>/dev/null || true
  } | sort -u | while read -r path; do
    [[ -n "$path" ]] || continue
    copy_worktree_path "$path"
  done
done

for path in "$ROOT"/scripts/peeknook-*.sh; do
  [[ -e "$path" ]] || continue
  copy_worktree_path "scripts/$(basename "$path")"
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
