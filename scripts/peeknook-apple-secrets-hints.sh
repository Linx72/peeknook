#!/usr/bin/env bash
# Print gh secret set commands for Apple notarization (paste values locally).
set -euo pipefail

REPO="${PEEKNOOK_GITHUB_REPO:-$(bash "$(dirname "$0")/peeknook-github-repo.sh")}"

cat <<EOF
== Apple notarization secrets for $REPO ==

Set these in GitHub → Settings → Secrets → Actions (or run locally):

  gh secret set APPLE_SIGNING_IDENTITY --repo $REPO
  gh secret set APPLE_ID --repo $REPO
  gh secret set APPLE_PASSWORD --repo $REPO   # app-specific password
  gh secret set APPLE_TEAM_ID --repo $REPO

Then re-run release CI:

  ./scripts/peeknook-retry-release-ci.sh v0.2.0

Local notarize (after signed DMG build):

  export APPLE_SIGNING_IDENTITY="Developer ID Application: …"
  export APPLE_ID=… APPLE_PASSWORD=… APPLE_TEAM_ID=…
  ./scripts/peeknook-notarize-macos.sh

EOF
