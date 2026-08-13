#!/usr/bin/env bash
# Prevent an accidental GitHub source/release mutation after selecting RepoBase.
set -euo pipefail

if [[ "${PEEKNOOK_ALLOW_GITHUB_LEGACY_RELEASE:-0}" != "1" ]]; then
  cat >&2 <<'EOF'
GitHub mutation blocked: RepoBase is the selected PeekNook source of truth.
GitHub may be used only as a temporary native-build/public-release bridge.
For an explicitly reviewed bridge operation, set:
  PEEKNOOK_ALLOW_GITHUB_LEGACY_RELEASE=1
EOF
  exit 1
fi

echo "Legacy GitHub release bridge explicitly enabled"
