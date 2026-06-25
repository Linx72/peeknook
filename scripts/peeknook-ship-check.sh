#!/usr/bin/env bash
# Pre-ship checklist: version, tests, secrets hints, updater repo.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

REPO="$(bash scripts/peeknook-github-repo.sh)"
VERSION=$(python3 -c "import json; print(json.load(open('desktop/src-tauri/tauri.conf.json'))['version'])")
TAG="v${VERSION}"

echo "== PeekNook ship check =="
echo "Version: $VERSION (tag: $TAG)"
echo "GitHub repo: $REPO"
echo ""

echo "▶ UI build"
(cd ui && npm run build)
echo ""

echo "▶ Field test"
./scripts/peeknook-field-test.sh
echo ""

echo "▶ Updater endpoint (build-time)"
REPO="$REPO" TAG="$TAG" python3 -c "
import json, os
repo = os.environ['REPO']
tag = os.environ['TAG']
ep = f'https://github.com/{repo}/releases/download/{tag}/latest.json'
print(f'  {ep}')
"
echo ""

echo "▶ Git status"
if git diff --quiet && [[ -z "$(git status --porcelain)" ]]; then
  echo "  Working tree clean — OK to tag"
else
  echo "  WARN: uncommitted changes — commit before ./scripts/peeknook-push-release.sh $TAG"
fi

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "  Tag $TAG already exists locally"
else
  echo "  Tag $TAG not created yet"
fi

echo ""
echo "▶ GitHub secrets (set in repo Settings → Secrets)"
echo "  Required for in-app updates: TAURI_SIGNING_PRIVATE_KEY, TAURI_SIGNING_PRIVATE_KEY_PASSWORD"
echo "  Optional macOS: APPLE_SIGNING_IDENTITY, APPLE_ID, APPLE_PASSWORD, APPLE_TEAM_ID"
echo "  Optional Windows: WINDOWS_CERTIFICATE, WINDOWS_CERTIFICATE_PASSWORD"
echo ""
echo "▶ Ship commands"
echo "  ./scripts/peeknook-release-tag.sh $TAG"
echo "  ./scripts/peeknook-push-release.sh $TAG"
echo ""
echo "▶ Physical two-Mac (after push on A, pull on B)"
echo "  export PEEKNOOK_SYNC_SOURCE_ID=source:…"
echo "  ./scripts/peeknook-two-mac-physical-record.sh"
echo ""
echo "▶ Verify GitHub Release (optional)"
echo "  ./scripts/peeknook-verify-release.sh"
echo ""
echo "OK — automated ship check passed"
