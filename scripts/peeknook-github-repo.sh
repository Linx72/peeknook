#!/usr/bin/env bash
# Resolve GitHub owner/repo for updater endpoints and release manifests.
# Override: PEEKNOOK_GITHUB_REPO=owner/repo
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ -n "${PEEKNOOK_GITHUB_REPO:-}" ]]; then
  echo "$PEEKNOOK_GITHUB_REPO"
  exit 0
fi

for remote in peeknook origin; do
  url="$(git -C "$ROOT" remote get-url "$remote" 2>/dev/null || true)"
  if [[ -n "$url" ]]; then
    repo="$(python3 -c "
import re, sys
url = sys.argv[1].strip().removesuffix('.git')
m = re.search(r'github\.com[:/]([^/]+/[^/]+)$', url)
print(m.group(1) if m else '')
" "$url")"
    if [[ -n "$repo" ]]; then
      echo "$repo"
      exit 0
    fi
  fi
done

echo "Linx72/peeknook"
