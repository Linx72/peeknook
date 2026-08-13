#!/usr/bin/env bash
# Build locally and publish to GitHub Releases (when CI billing is blocked).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
bash scripts/peeknook-legacy-github-guard.sh

TAG="${1:-${PEEKNOOK_RELEASE_TAG:-v0.2.0}}"
REPO="${PEEKNOOK_GITHUB_REPO:-Linx72/peeknook}"
export PEEKNOOK_RELEASE_TAG="$TAG"
export PEEKNOOK_GITHUB_REPO="$REPO"

PEEKNOOK_ALLOW_UNSIGNED_LOCAL_RELEASE=0 bash scripts/peeknook-local-release.sh

OUT="$HOME/Library/Application Support/PeekNook/releases"
if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  echo "Uploading to existing release $TAG..."
  gh release upload "$TAG" "$OUT"/* --repo "$REPO" --clobber
else
  echo "Creating release $TAG..."
  gh release create "$TAG" \
    --repo "$REPO" \
    --title "PeekNook ${TAG#v}" \
    --notes "PeekNook ${TAG#v} — local build (CI fallback)." \
    "$OUT"/*
fi

echo "OK — https://github.com/$REPO/releases/tag/$TAG"
