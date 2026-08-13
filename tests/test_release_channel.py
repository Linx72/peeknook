"""Tests for the separate public RepoBase release-channel contract."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts/peeknook-release-channel.py"
CONFIG_PATH = PROJECT_ROOT / "distribution/repobase-public/channel.json"
SPEC = importlib.util.spec_from_file_location("peeknook_release_channel", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _valid_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_public_repobase_channel_resolves_latest_manifest():
    contract = MODULE.validate_channel(_valid_config())

    assert contract["latest_manifest_url"] == (
        "https://repobase.ru/releases/peeknook-releases/"
        "releases/latest/download/latest.json"
    )
    assert contract["required_platforms"] == [
        "darwin-aarch64",
        "windows-x86_64",
    ]


def test_public_release_channel_must_differ_from_private_source():
    config = _valid_config()
    config["repository"] = config["source_repository"]

    with pytest.raises(ValueError, match="must differ"):
        MODULE.validate_channel(config)


def test_public_release_channel_is_pinned_to_canonical_repositories():
    config = _valid_config()
    config["repository"] = "timeweb/other-releases"

    with pytest.raises(ValueError, match="Unexpected public release repository"):
        MODULE.validate_channel(config)

    config = _valid_config()
    config["source_repository"] = "timeweb/other-source"

    with pytest.raises(ValueError, match="Unexpected private source repository"):
        MODULE.validate_channel(config)


@pytest.mark.parametrize(
    "base_url",
    ["http://repobase.ru", "https://token@repobase.ru", "https://repobase.ru?q=1"],
)
def test_public_release_channel_rejects_unsafe_base_url(base_url):
    config = _valid_config()
    config["release_base_url"] = base_url

    with pytest.raises(ValueError, match="must be HTTPS"):
        MODULE.validate_channel(config)


def test_public_release_channel_requires_both_native_platforms():
    config = _valid_config()
    config["required_platforms"] = ["darwin-aarch64"]

    with pytest.raises(ValueError, match="Required platforms"):
        MODULE.validate_channel(config)


def test_public_release_channel_rejects_manifest_paths():
    config = _valid_config()
    config["updater_manifest"] = "nested/latest.json"

    with pytest.raises(ValueError, match="JSON filename"):
        MODULE.validate_channel(config)


def test_release_channel_cli_prints_validated_json():
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--config", str(CONFIG_PATH), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout)["repository"] == "releases/peeknook-releases"
