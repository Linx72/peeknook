"""Tests for the shared PeekNook Tauri build config."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parents[1] / "scripts/peeknook-build-config.py"
SPEC = importlib.util.spec_from_file_location("peeknook_build_config", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_tagged_updater_endpoint_uses_github_download_order():
    config = MODULE.build_config("Linx72/peeknook", "v0.3.0")

    assert config["plugins"]["updater"]["endpoints"] == [
        "https://github.com/Linx72/peeknook/releases/download/v0.3.0/latest.json"
    ]


def test_latest_updater_endpoint_uses_latest_alias():
    config = MODULE.build_config("Linx72/peeknook", "latest")

    assert config["plugins"]["updater"]["endpoints"] == [
        "https://github.com/Linx72/peeknook/releases/latest/download/latest.json"
    ]


def test_repobase_release_endpoint_is_supported_explicitly():
    config = MODULE.build_config(
        "releases/peeknook-releases",
        "v0.3.0",
        release_base_url="https://repobase.ru",
    )

    assert config["plugins"]["updater"]["endpoints"] == [
        "https://repobase.ru/releases/peeknook-releases/"
        "releases/download/v0.3.0/latest.json"
    ]


def test_windows_signing_config_uses_safe_defaults():
    thumbprint = "ab" * 20

    config = MODULE.build_config("Linx72/peeknook", "v0.3.0", thumbprint)

    assert config["bundle"]["windows"] == {
        "certificateThumbprint": thumbprint.upper(),
        "digestAlgorithm": "sha256",
        "timestampUrl": "http://timestamp.digicert.com",
    }


def test_invalid_windows_thumbprint_fails_closed():
    with pytest.raises(ValueError, match="thumbprint"):
        MODULE.build_config("Linx72/peeknook", "v0.3.0", "not-a-thumbprint")


def test_release_base_url_rejects_credentials_and_plain_http():
    with pytest.raises(ValueError, match="HTTPS release base URL"):
        MODULE.build_config(
            "timeweb/peeknook",
            "v0.3.0",
            release_base_url="https://token@repobase.ru",
        )
    with pytest.raises(ValueError, match="HTTPS release base URL"):
        MODULE.build_config(
            "timeweb/peeknook",
            "v0.3.0",
            release_base_url="http://repobase.ru",
        )
