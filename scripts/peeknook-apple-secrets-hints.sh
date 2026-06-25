#!/usr/bin/env bash
# Print gh secret set commands for Apple notarization (paste values locally).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="${PEEKNOOK_GITHUB_REPO:-$(bash "$(dirname "$0")/peeknook-github-repo.sh")}"
VERSION=$(python3 -c "import json; print(json.load(open('$ROOT/desktop/src-tauri/tauri.conf.json'))['version'])")

cat <<EOF
== Apple notarization secrets for $REPO ==

Set these in GitHub → Settings → Secrets → Actions (or run locally):

  gh secret set APPLE_SIGNING_IDENTITY --repo $REPO
  gh secret set APPLE_ID --repo $REPO
  gh secret set APPLE_PASSWORD --repo $REPO   # app-specific password
  gh secret set APPLE_TEAM_ID --repo $REPO

Then re-run release CI:

  ./scripts/peeknook-retry-release-ci.sh v${VERSION}

Local notarize (after signed DMG build):

  export APPLE_SIGNING_IDENTITY="Developer ID Application: …"
  export APPLE_ID=… APPLE_PASSWORD=… APPLE_TEAM_ID=…
  ./scripts/peeknook-notarize-macos.sh

EOF
