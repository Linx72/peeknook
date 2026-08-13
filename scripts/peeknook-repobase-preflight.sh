#!/usr/bin/env bash
# Read-only source-of-truth preflight for the future RepoBase repository.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE_HOST="${PEEKNOOK_SOURCE_FORGE_HOST:-repobase.ru}"
SOURCE_REPO="${PEEKNOOK_SOURCE_FORGE_REPO:-timeweb/peeknook}"
SOURCE_REMOTE="${PEEKNOOK_SOURCE_GIT_REMOTE:-repobase}"
TARGET_URL="git@${SOURCE_HOST}:${SOURCE_REPO}.git"
FAILURES=0

if [[ ! "$SOURCE_HOST" =~ ^[A-Za-z0-9.-]+$ ]]; then
  echo "FAIL invalid RepoBase host: $SOURCE_HOST" >&2
  exit 2
fi
if [[ ! "$SOURCE_REPO" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
  echo "FAIL invalid RepoBase repository slug: $SOURCE_REPO" >&2
  exit 2
fi

echo "== PeekNook RepoBase preflight =="
echo "Source of truth: https://${SOURCE_HOST}/${SOURCE_REPO}"
echo "SSH target: $TARGET_URL"

if [[ -n "$(git -C "$ROOT" status --porcelain)" ]]; then
  echo "FAIL working tree is dirty; do not publish a partial checkout"
  FAILURES=$((FAILURES + 1))
else
  echo "OK working tree is clean"
fi

BRANCH="$(git -C "$ROOT" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
if [[ -z "$BRANCH" ]]; then
  echo "FAIL detached HEAD cannot be used as the RepoBase source branch"
  FAILURES=$((FAILURES + 1))
else
  echo "OK branch: $BRANCH"
fi

REMOTE_URL="$(git -C "$ROOT" remote get-url "$SOURCE_REMOTE" 2>/dev/null || true)"
if [[ -z "$REMOTE_URL" ]]; then
  echo "PENDING remote '$SOURCE_REMOTE' is not configured"
  echo "  after the private repository exists:"
  echo "  git remote add $SOURCE_REMOTE $TARGET_URL"
  FAILURES=$((FAILURES + 1))
elif [[ "$REMOTE_URL" != "$TARGET_URL" ]]; then
  echo "FAIL remote '$SOURCE_REMOTE' points to an unexpected URL: $REMOTE_URL"
  FAILURES=$((FAILURES + 1))
else
  echo "OK remote '$SOURCE_REMOTE': $REMOTE_URL"
fi

LS_REMOTE_OUTPUT="$(mktemp "${TMPDIR:-/tmp}/peeknook-repobase-ls-remote.XXXXXX")"
LS_REMOTE_ERROR="$(mktemp "${TMPDIR:-/tmp}/peeknook-repobase-ls-remote-error.XXXXXX")"
cleanup() {
  rm -f "$LS_REMOTE_OUTPUT" "$LS_REMOTE_ERROR"
}
trap cleanup EXIT

if GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=8" \
  git ls-remote "$TARGET_URL" HEAD >"$LS_REMOTE_OUTPUT" 2>"$LS_REMOTE_ERROR"; then
  if [[ -s "$LS_REMOTE_OUTPUT" ]]; then
    echo "OK RepoBase repository exists and has a HEAD"
  else
    echo "OK RepoBase repository exists and is empty"
  fi
else
  if grep -q 'Cannot find repository' "$LS_REMOTE_ERROR"; then
    echo "PENDING RepoBase repository does not exist: $SOURCE_REPO"
  else
    echo "FAIL RepoBase repository lookup failed"
  fi
  FAILURES=$((FAILURES + 1))
fi

if [[ "$FAILURES" -ne 0 ]]; then
  echo "RepoBase preflight failed with $FAILURES unresolved gate(s)"
  exit 1
fi

echo "RepoBase source preflight passed; this command did not push anything"
