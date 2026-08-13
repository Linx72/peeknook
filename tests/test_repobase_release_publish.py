"""Tests for fail-closed RepoBase release publication."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts/peeknook-publish-repobase-release.py"
SPEC = importlib.util.spec_from_file_location("peeknook_repobase_publish", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _write_release_bundle(root: Path, version: str = "0.3.0") -> Path:
    artifacts = root / "artifacts"
    macos = artifacts / "macos"
    windows = artifacts / "windows"
    macos.mkdir(parents=True)
    windows.mkdir(parents=True)

    archive = macos / f"PeekNook_{version}_aarch64.app.tar.gz"
    archive.write_bytes(b"signed macOS updater")
    Path(f"{archive}.sig").write_text("mac-signature\n", encoding="utf-8")
    (macos / f"PeekNook_{version}_aarch64.dmg").write_bytes(b"signed dmg")

    setup = windows / f"PeekNook_{version}_x64-setup.exe"
    setup.write_bytes(b"signed Windows updater")
    Path(f"{setup}.sig").write_text("windows-signature\n", encoding="utf-8")
    (windows / f"PeekNook_{version}_x64_en-US.msi").write_bytes(b"signed msi")

    tag = f"v{version}"
    release_url = (
        "https://repobase.ru/releases/peeknook-releases/releases/download/" + tag
    )
    manifest = {
        "version": version,
        "notes": "test",
        "pub_date": "2026-08-13T00:00:00Z",
        "platforms": {
            "darwin-aarch64": {
                "url": f"{release_url}/{archive.name}",
                "signature": "mac-signature",
            },
            "windows-x86_64": {
                "url": f"{release_url}/{setup.name}",
                "signature": "windows-signature",
            },
        },
    }
    (artifacts / "latest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    config = root / "tauri.conf.json"
    config.write_text(json.dumps({"version": version}), encoding="utf-8")
    return config


def test_complete_signed_bundle_builds_validate_only_plan(tmp_path):
    config = _write_release_bundle(tmp_path)

    plan = MODULE.build_release_plan(tmp_path / "artifacts", "v0.3.0", config)

    assert plan.repository == "releases/peeknook-releases"
    assert plan.version == "0.3.0"
    assert {asset.name for asset in plan.assets} == {
        "PeekNook_0.3.0_aarch64.app.tar.gz",
        "PeekNook_0.3.0_aarch64.app.tar.gz.sig",
        "PeekNook_0.3.0_aarch64.dmg",
        "PeekNook_0.3.0_x64-setup.exe",
        "PeekNook_0.3.0_x64-setup.exe.sig",
        "PeekNook_0.3.0_x64_en-US.msi",
        "latest.json",
    }
    assert all(len(asset.sha256) == 64 for asset in plan.assets)


def test_cli_defaults_to_validate_only_and_needs_no_token(tmp_path):
    config = _write_release_bundle(tmp_path)
    environment = os.environ.copy()
    environment.pop("PEEKNOOK_REPOBASE_RELEASE_TOKEN", None)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--tag",
            "v0.3.0",
            "--config",
            str(config),
            str(tmp_path / "artifacts"),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout)["mode"] == "validate-only"


def test_cli_publish_requires_exact_repository_confirmation(tmp_path):
    config = _write_release_bundle(tmp_path)
    environment = os.environ.copy()
    environment["PEEKNOOK_REPOBASE_RELEASE_TOKEN"] = "test-token"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--tag",
            "v0.3.0",
            "--config",
            str(config),
            "--publish",
            str(tmp_path / "artifacts"),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 1
    assert "--confirm-repository releases/peeknook-releases" in result.stderr


def test_release_bundle_requires_windows_msi(tmp_path):
    config = _write_release_bundle(tmp_path)
    next((tmp_path / "artifacts").rglob("*.msi")).unlink()

    with pytest.raises(MODULE.ReleaseValidationError, match="Windows MSI"):
        MODULE.build_release_plan(tmp_path / "artifacts", "v0.3.0", config)


def test_release_bundle_rejects_legacy_github_manifest_url(tmp_path):
    config = _write_release_bundle(tmp_path)
    manifest_path = tmp_path / "artifacts/latest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["platforms"]["darwin-aarch64"]["url"] = (
        "https://github.com/Linx72/peeknook/releases/download/v0.3.0/file.tar.gz"
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(MODULE.ReleaseValidationError, match="URLs or signatures"):
        MODULE.build_release_plan(tmp_path / "artifacts", "v0.3.0", config)


def test_release_bundle_rejects_signature_mismatch(tmp_path):
    config = _write_release_bundle(tmp_path)
    signature = next((tmp_path / "artifacts").rglob("*.app.tar.gz.sig"))
    signature.write_text("different-signature", encoding="utf-8")

    with pytest.raises(MODULE.ReleaseValidationError, match="URLs or signatures"):
        MODULE.build_release_plan(tmp_path / "artifacts", "v0.3.0", config)


def test_release_bundle_rejects_symlinks(tmp_path):
    config = _write_release_bundle(tmp_path)
    source = next((tmp_path / "artifacts").rglob("*.dmg"))
    (tmp_path / "artifacts/linked.dmg").symlink_to(source)

    with pytest.raises(MODULE.ReleaseValidationError, match="symlink"):
        MODULE.build_release_plan(tmp_path / "artifacts", "v0.3.0", config)


class _RecordingClient:
    def __init__(self, existing: dict | None = None):
        self.existing = existing
        self.calls: list[tuple[str, object]] = []
        self.assets: list[dict] = []

    def get_release_by_tag(self, tag: str):
        self.calls.append(("get_by_tag", tag))
        return self.existing

    def verify_asset(self, remote_asset, local_asset, tag):
        self.calls.append(("verify", local_asset.name))

    def create_draft(self, plan, notes: str):
        self.calls.append(("create_draft", notes))
        return {"id": 42, "draft": True, "tag_name": plan.tag}

    def upload_asset(self, release_id: int, asset):
        self.calls.append(("upload", asset.name))
        uploaded = {"name": asset.name, "size": asset.size}
        self.assets.append(uploaded)
        return uploaded

    def get_release(self, release_id: int):
        self.calls.append(("get_release", release_id))
        return {"id": release_id, "draft": True, "assets": self.assets}

    def publish_draft(self, release_id: int):
        self.calls.append(("publish", release_id))
        return {
            "id": release_id,
            "draft": False,
            "tag_name": "v0.3.0",
            "html_url": "https://repobase.ru/releases/peeknook-releases/releases/tag/v0.3.0",
        }


def test_publication_uploads_manifest_last_and_publishes_after_inventory(tmp_path):
    config = _write_release_bundle(tmp_path)
    plan = MODULE.build_release_plan(tmp_path / "artifacts", "v0.3.0", config)
    client = _RecordingClient()

    published = MODULE.publish_release(plan, "notes", client)

    uploads = [value for call, value in client.calls if call == "upload"]
    assert uploads[-1] == "latest.json"
    assert client.calls[-2:] == [("get_release", 42), ("publish", 42)]
    assert published["draft"] is False


def test_publication_never_overwrites_mismatched_existing_release(tmp_path):
    config = _write_release_bundle(tmp_path)
    plan = MODULE.build_release_plan(tmp_path / "artifacts", "v0.3.0", config)
    client = _RecordingClient(
        existing={"id": 7, "draft": False, "tag_name": "v0.3.0", "assets": []}
    )

    with pytest.raises(MODULE.ReleasePublishError, match="different asset inventory"):
        MODULE.publish_release(plan, "notes", client)

    assert client.calls == [("get_by_tag", "v0.3.0")]


def test_publication_accepts_byte_verified_existing_release_without_mutation(tmp_path):
    config = _write_release_bundle(tmp_path)
    plan = MODULE.build_release_plan(tmp_path / "artifacts", "v0.3.0", config)
    remote_assets = [
        {
            "name": asset.name,
            "size": asset.size,
            "browser_download_url": "https://example.invalid/" + asset.name,
        }
        for asset in plan.assets
    ]
    existing = {
        "id": 7,
        "draft": False,
        "tag_name": "v0.3.0",
        "assets": remote_assets,
    }
    client = _RecordingClient(existing=existing)

    published = MODULE.publish_release(plan, "notes", client)

    assert published == existing
    assert [call for call, _ in client.calls].count("verify") == len(plan.assets)
    assert all(call not in {"create_draft", "upload", "publish"} for call, _ in client.calls)
