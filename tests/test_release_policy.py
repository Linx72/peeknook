"""Tests for the public release credential policy."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

POLICY_SCRIPT = Path(__file__).parents[1] / "scripts/peeknook-release-policy.py"
PUSH_SCRIPT = Path(__file__).parents[1] / "scripts/peeknook-push-release.sh"
WORKFLOW_PATH = Path(__file__).parents[1] / ".github/workflows/peeknook-release.yml"
REQUIRED_SECRETS = (
    "TAURI_SIGNING_PRIVATE_KEY",
    "TAURI_SIGNING_PRIVATE_KEY_PASSWORD",
    "APPLE_CERTIFICATE",
    "APPLE_CERTIFICATE_PASSWORD",
    "KEYCHAIN_PASSWORD",
    "APPLE_ID",
    "APPLE_PASSWORD",
    "APPLE_TEAM_ID",
    "WINDOWS_CERTIFICATE",
    "WINDOWS_CERTIFICATE_PASSWORD",
    "REPOBASE_RELEASE_TOKEN",
)


def _policy_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in REQUIRED_SECRETS:
        environment.pop(name, None)
    return environment


def _configured_tag_ref() -> str:
    config_path = Path(__file__).parents[1] / "desktop/src-tauri/tauri.conf.json"
    version = json.loads(config_path.read_text(encoding="utf-8"))["version"]
    return f"refs/tags/v{version}"


def test_non_tag_build_allows_unsigned_qa_artifacts():
    result = subprocess.run(
        [sys.executable, str(POLICY_SCRIPT), "--ref", "refs/heads/main"],
        check=False,
        capture_output=True,
        text=True,
        env=_policy_environment(),
    )

    assert result.returncode == 0
    assert "unsigned QA artifacts are allowed" in result.stdout


def test_public_tag_fails_when_signing_secrets_are_missing():
    result = subprocess.run(
        [sys.executable, str(POLICY_SCRIPT), "--ref", _configured_tag_ref()],
        check=False,
        capture_output=True,
        text=True,
        env=_policy_environment(),
    )

    assert result.returncode == 1
    for name in REQUIRED_SECRETS:
        assert name in result.stderr


def test_public_tag_passes_when_all_signing_secrets_are_present():
    environment = _policy_environment()
    environment.update({name: "configured-for-test" for name in REQUIRED_SECRETS})

    result = subprocess.run(
        [sys.executable, str(POLICY_SCRIPT), "--ref", _configured_tag_ref()],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0
    assert "all updater, Apple, Windows, and RepoBase release credentials" in result.stdout


def test_public_tag_must_match_tauri_version():
    environment = _policy_environment()
    environment.update({name: "configured-for-test" for name in REQUIRED_SECRETS})

    result = subprocess.run(
        [sys.executable, str(POLICY_SCRIPT), "--ref", "refs/tags/v999.0.0"],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 1
    assert "does not match the configured version" in result.stderr


def test_release_push_updates_source_branch_and_tag_atomically():
    script = PUSH_SCRIPT.read_text(encoding="utf-8")

    assert 'git push --atomic "$REMOTE"' in script
    assert '"HEAD:refs/heads/$BRANCH"' in script
    assert '"refs/tags/$TAG"' in script
    assert 'git push "$REMOTE" HEAD 2>/dev/null || true' not in script


def test_native_bridge_publishes_repobase_before_github():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "--repo releases/peeknook-releases" in workflow
    assert "--release-base-url https://repobase.ru" in workflow
    assert "--tag latest" in workflow
    assert "runs-on: macos-15" in workflow
    assert 'test "$(uname -m)" = arm64' in workflow
    assert "runs-on: windows-2025" in workflow
    assert '$env:PROCESSOR_ARCHITECTURE -ne "AMD64"' in workflow
    assert "needs: [build-macos, build-windows, publish-repobase]" in workflow
    assert workflow.index("publish-repobase:") < workflow.index("publish-release:")
