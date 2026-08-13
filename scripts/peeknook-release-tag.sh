#!/usr/bin/env bash
# Create a local PeekNook release tag after source and runtime gates pass.
#
# Usage:
#   ./scripts/peeknook-release-tag.sh v0.2.0
#   ./scripts/peeknook-push-release.sh v0.2.0   # tag + push
#
# Prerequisites:
#   - RepoBase remote configured for the push script
#   - native release bridge credentials configured separately when used
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${1:-}"

if [[ -z "$TAG" ]]; then
  echo "Usage: $0 <tag>" >&2
  echo "Example: $0 v0.2.0" >&2
  exit 1
fi

if [[ ! "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]]; then
  echo "Tag must be a semantic version such as v0.2.0 or v0.2.0-rc.1" >&2
  exit 1
fi

VERSION="${TAG#v}"
cd "$ROOT"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Release tag blocked: the working tree contains uncommitted or untracked files." >&2
  echo "Commit the intended release tree before creating $TAG." >&2
  exit 1
fi

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
echo "Push the reviewed tag to RepoBase:"
echo "  ./scripts/peeknook-push-release.sh $TAG"
