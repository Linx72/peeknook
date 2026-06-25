#!/usr/bin/env bash
# Verify GitHub Release assets and updater manifest are publicly reachable.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

REPO="${PEEKNOOK_GITHUB_REPO:-$(bash scripts/peeknook-github-repo.sh)}"
VERSION=$(python3 -c "import json; print(json.load(open('desktop/src-tauri/tauri.conf.json'))['version'])")
TAG="${PEEKNOOK_RELEASE_TAG:-v${VERSION}}"

echo "== PeekNook release verify =="
echo "Repo: $REPO  Tag: $TAG"
echo ""

MANIFEST_URL="https://github.com/${REPO}/releases/download/${TAG}/latest.json"
echo "▶ Manifest: $MANIFEST_URL"
curl -sfL "$MANIFEST_URL" -o /tmp/peeknook-latest.json
python3 -c "
import json, sys
d = json.load(open('/tmp/peeknook-latest.json'))
assert d.get('version') == '${VERSION}', d
platforms = d.get('platforms') or {}
print(f'  version={d[\"version\"]} platforms={list(platforms.keys())}')
for name, p in platforms.items():
    url = p.get('url', '')
    sig = p.get('signature', '')
    assert url, f'missing url for {name}'
    assert sig, f'missing signature for {name}'
    print(f'  {name}: ok')
"

echo ""
echo "▶ Release assets (gh)"
ASSETS=$(gh release view "$TAG" --repo "$REPO" --json assets -q '.assets[].name' 2>/dev/null || true)
if [[ -z "$ASSETS" ]]; then
  echo "  WARN: gh release view failed or no assets" >&2
  exit 1
fi
echo "$ASSETS" | while read -r name; do
  [[ -z "$name" ]] && continue
  url="https://github.com/${REPO}/releases/download/${TAG}/${name}"
  curl -sfL -o /dev/null "$url" || { echo "  ✗ $name" >&2; exit 1; }
  echo "  ✓ $name"
done

echo ""
echo "OK — release $TAG verified"
