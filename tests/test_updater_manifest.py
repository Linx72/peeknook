"""Tests for fail-closed Tauri updater manifest generation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

MANIFEST_SCRIPT = Path(__file__).parents[1] / "scripts/peeknook-updater-manifest.py"


def _run_manifest(
    root: Path,
    output: Path,
    *required_platforms: str,
    release_base_url: str = "https://github.com",
    repository: str = "Linx72/peeknook",
):
    command = [
        sys.executable,
        str(MANIFEST_SCRIPT),
        "--version",
        "0.3.0",
        "--tag",
        "v0.3.0",
        "--repo",
        repository,
        "--release-base-url",
        release_base_url,
        "--out",
        str(output),
    ]
    for platform in required_platforms:
        command.extend(["--require-platform", platform])
    command.append(str(root))
    return subprocess.run(command, check=False, capture_output=True, text=True)


def _write_artifact(root: Path, name: str, signature: str = "test-signature"):
    artifact = root / name
    artifact.write_bytes(b"artifact")
    Path(f"{artifact}.sig").write_text(signature, encoding="utf-8")


def test_manifest_requires_both_public_updater_platforms(tmp_path):
    _write_artifact(tmp_path, "PeekNook.app.tar.gz")
    _write_artifact(tmp_path, "PeekNook_0.3.0_x64-setup.exe")
    output = tmp_path / "latest.json"

    result = _run_manifest(
        tmp_path,
        output,
        "darwin-aarch64",
        "windows-x86_64",
    )

    assert result.returncode == 0
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert set(manifest["platforms"]) == {
        "darwin-aarch64",
        "windows-x86_64",
    }


def test_manifest_supports_repobase_release_assets(tmp_path):
    _write_artifact(tmp_path, "PeekNook.app.tar.gz")
    output = tmp_path / "latest.json"

    result = _run_manifest(
        tmp_path,
        output,
        "darwin-aarch64",
        release_base_url="https://repobase.ru",
        repository="releases/peeknook-releases",
    )

    assert result.returncode == 0
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["platforms"]["darwin-aarch64"]["url"].startswith(
        "https://repobase.ru/releases/peeknook-releases/releases/download/v0.3.0/"
    )


def test_manifest_fails_when_required_platform_is_missing(tmp_path):
    _write_artifact(tmp_path, "PeekNook.app.tar.gz")
    output = tmp_path / "latest.json"

    result = _run_manifest(
        tmp_path,
        output,
        "darwin-aarch64",
        "windows-x86_64",
    )

    assert result.returncode == 1
    assert "Missing required updater platforms: windows-x86_64" in result.stderr
    assert not output.exists()


def test_manifest_rejects_empty_updater_signature(tmp_path):
    _write_artifact(tmp_path, "PeekNook.app.tar.gz", signature="")
    output = tmp_path / "latest.json"

    result = _run_manifest(tmp_path, output, "darwin-aarch64")

    assert result.returncode == 1
    assert "Updater signature is empty" in result.stderr
    assert not output.exists()
