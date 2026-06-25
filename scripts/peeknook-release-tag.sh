#!/usr/bin/env bash
# Create a PeekNook release tag (triggers GitHub Actions peeknook-release.yml).
#
# Usage:
#   ./scripts/peeknook-release-tag.sh v0.2.0
#   ./scripts/peeknook-push-release.sh v0.2.0   # tag + push
#
# Prerequisites:
#   - gh CLI authenticated (for push script)
#   - GitHub secrets: TAURI_SIGNING_PRIVATE_KEY, optional Apple/Windows signing
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${1:-}"

if [[ -z "$TAG" ]]; then
  echo "Usage: $0 <tag>" >&2
  echo "Example: $0 v0.2.0" >&2
  exit 1
fi

if [[ ! "$TAG" =~ ^v[0-9] ]]; then
  echo "Tag must look like v0.2.0" >&2
  exit 1
fi

VERSION="${TAG#v}"
cd "$ROOT"

echo "== Pre-release checks =="
./scripts/peeknook-ui-parity-audit.sh
(cd ui && npm run build)
./scripts/peeknook-field-test.sh

CONF_VERSION=$(python3 -c "import json; print(json.load(open('desktop/src-tauri/tauri.conf.json'))['version'])")
if [[ "$CONF_VERSION" != "$VERSION" ]]; then
  echo "FAIL: desktop/src-tauri/tauri.conf.json version=$CONF_VERSION != tag $VERSION" >&2
  exit 1
fi

echo ""
echo "== Creating tag $TAG =="
if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Tag $TAG already exists" >&2
  exit 1
fi

git tag -a "$TAG" -m "PeekNook release $TAG"
echo "Created annotated tag $TAG"
echo ""
echo "Push to trigger GitHub Release:"
echo "  git push origin $TAG"
echo "  # or: ./scripts/peeknook-push-release.sh $TAG"
