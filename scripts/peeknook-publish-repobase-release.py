#!/usr/bin/env python3
"""Validate and publish a complete PeekNook release to RepoBase."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

EXPECTED_API_BASE_URL = "https://repobase.ru/api/v1"
EXPECTED_DOWNLOAD_BASE_URL = "https://repobase.ru"
EXPECTED_REPOSITORY = "releases/peeknook-releases"
EXPECTED_TARGET = "main"
DEFAULT_TOKEN_ENV = "PEEKNOOK_REPOBASE_RELEASE_TOKEN"
REQUIRED_PLATFORMS = {"darwin-aarch64", "windows-x86_64"}
TAG_PATTERN = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+(?:[.-][0-9A-Za-z.-]+)?$")
TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
ASSET_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._+-]+$")


class ReleaseValidationError(ValueError):
    """Raised when a local release bundle is not safe to publish."""


class ReleasePublishError(RuntimeError):
    """Raised when RepoBase does not accept an exact release operation."""


@dataclass(frozen=True)
class ReleaseAsset:
    path: Path
    name: str
    size: int
    sha256: str


@dataclass(frozen=True)
class ReleasePlan:
    tag: str
    version: str
    repository: str
    assets: tuple[ReleaseAsset, ...]
    prerelease: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "repository": self.repository,
            "tag": self.tag,
            "version": self.version,
            "prerelease": self.prerelease,
            "assets": [
                {
                    "name": asset.name,
                    "size": asset.size,
                    "sha256": asset.sha256,
                }
                for asset in self.assets
            ],
        }


class ReleaseClient(Protocol):
    def get_release_by_tag(self, tag: str) -> dict | None: ...

    def verify_asset(
        self, remote_asset: dict, local_asset: ReleaseAsset, tag: str
    ) -> None: ...

    def create_draft(self, plan: ReleasePlan, notes: str) -> dict: ...

    def upload_asset(self, release_id: int, asset: ReleaseAsset) -> dict: ...

    def get_release(self, release_id: int) -> dict: ...

    def publish_draft(self, release_id: int) -> dict: ...


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_release_asset(path: Path) -> bool:
    lower_name = path.name.lower()
    return (
        lower_name == "latest.json"
        or lower_name.endswith(".dmg")
        or lower_name.endswith(".app.tar.gz")
        or lower_name.endswith(".app.tar.gz.sig")
        or lower_name.endswith(".msi")
        or lower_name.endswith(".exe")
        or lower_name.endswith(".exe.sig")
    )


def discover_assets(root: Path) -> tuple[ReleaseAsset, ...]:
    if not root.is_dir():
        raise ReleaseValidationError(f"Release artifact root not found: {root}")

    paths: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ReleaseValidationError(f"Release bundle contains a symlink: {path}")
        if path.is_file() and _is_release_asset(path):
            paths.append(path)

    if not paths:
        raise ReleaseValidationError(f"No release assets found under: {root}")

    names: set[str] = set()
    assets: list[ReleaseAsset] = []
    for path in paths:
        normalized_name = path.name.casefold()
        if not ASSET_NAME_PATTERN.fullmatch(path.name):
            raise ReleaseValidationError(
                f"Release asset name contains unsupported characters: {path.name}"
            )
        if normalized_name in names:
            raise ReleaseValidationError(f"Duplicate release asset name: {path.name}")
        names.add(normalized_name)
        size = path.stat().st_size
        if size <= 0:
            raise ReleaseValidationError(f"Release asset is empty: {path}")
        assets.append(
            ReleaseAsset(
                path=path,
                name=path.name,
                size=size,
                sha256=sha256_file(path),
            )
        )
    return tuple(sorted(assets, key=lambda asset: asset.name.casefold()))


def _select_assets(assets: tuple[ReleaseAsset, ...], suffix: str) -> list[ReleaseAsset]:
    normalized_suffix = suffix.casefold()
    return [
        asset for asset in assets if asset.name.casefold().endswith(normalized_suffix)
    ]


def _one_asset(assets: list[ReleaseAsset], description: str) -> ReleaseAsset:
    if len(assets) != 1:
        raise ReleaseValidationError(
            f"Release requires exactly one {description}; found {len(assets)}"
        )
    return assets[0]


def _read_signature(asset: ReleaseAsset) -> str:
    signature = asset.path.read_text(encoding="utf-8").strip()
    if not signature:
        raise ReleaseValidationError(f"Updater signature is empty: {asset.path}")
    return signature


def _load_json(path: Path, description: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseValidationError(f"Cannot read {description}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleaseValidationError(f"{description} must be a JSON object")
    return value


def build_release_plan(
    artifact_root: Path,
    tag: str,
    config_path: Path,
) -> ReleasePlan:
    if not TAG_PATTERN.fullmatch(tag):
        raise ReleaseValidationError(
            "Release tag must be a semantic version such as v0.3.0"
        )
    version = tag.removeprefix("v")
    config = _load_json(config_path, "Tauri config")
    if config.get("version") != version:
        raise ReleaseValidationError(
            f"Tauri version {config.get('version')!r} does not match tag {tag}"
        )

    assets = discover_assets(artifact_root)
    manifest_asset = _one_asset(
        [asset for asset in assets if asset.name.casefold() == "latest.json"],
        "latest.json updater manifest",
    )
    dmg_assets = _select_assets(assets, ".dmg")
    msi_assets = _select_assets(assets, ".msi")
    updater_archives = _select_assets(assets, ".app.tar.gz")
    updater_archive = _one_asset(updater_archives, "macOS updater archive")
    archive_signature = _one_asset(
        [
            asset
            for asset in assets
            if asset.name.casefold() == f"{updater_archive.name}.sig".casefold()
        ],
        "macOS updater signature",
    )
    setup_installers = [
        asset
        for asset in _select_assets(assets, ".exe")
        if "setup" in asset.name.casefold()
    ]
    setup_installer = _one_asset(setup_installers, "Windows updater installer")
    setup_signature = _one_asset(
        [
            asset
            for asset in assets
            if asset.name.casefold() == f"{setup_installer.name}.sig".casefold()
        ],
        "Windows updater signature",
    )
    if not dmg_assets:
        raise ReleaseValidationError("Release requires at least one macOS DMG")
    if not msi_assets:
        raise ReleaseValidationError("Release requires at least one Windows MSI")

    manifest = _load_json(manifest_asset.path, "updater manifest")
    if manifest.get("version") != version:
        raise ReleaseValidationError(
            f"Updater manifest version {manifest.get('version')!r} does not match {tag}"
        )
    platforms = manifest.get("platforms")
    if not isinstance(platforms, dict) or set(platforms) != REQUIRED_PLATFORMS:
        raise ReleaseValidationError(
            "Updater manifest must contain exactly darwin-aarch64 and windows-x86_64"
        )

    release_url = (
        f"{EXPECTED_DOWNLOAD_BASE_URL}/{EXPECTED_REPOSITORY}/releases/download/{tag}"
    )
    expected_platforms = {
        "darwin-aarch64": {
            "url": f"{release_url}/{updater_archive.name}",
            "signature": _read_signature(archive_signature),
        },
        "windows-x86_64": {
            "url": f"{release_url}/{setup_installer.name}",
            "signature": _read_signature(setup_signature),
        },
    }
    if platforms != expected_platforms:
        raise ReleaseValidationError(
            "Updater manifest URLs or signatures do not match the staged RepoBase assets"
        )

    return ReleasePlan(
        tag=tag,
        version=version,
        repository=EXPECTED_REPOSITORY,
        assets=assets,
        prerelease="-" in version,
    )


class ForgejoReleaseClient:
    def __init__(self, token: str):
        if not token or not TOKEN_PATTERN.fullmatch(token):
            raise ReleasePublishError("RepoBase release token has an invalid format")
        self._token = token
        self._repo_path = "/repos/" + "/".join(
            quote(part, safe="") for part in EXPECTED_REPOSITORY.split("/")
        )

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        expected_status: int = 200,
        allow_not_found: bool = False,
    ) -> dict | None:
        body = None
        headers = {
            "Accept": "application/json",
            "Authorization": f"token {self._token}",
        }
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(
            f"{EXPECTED_API_BASE_URL}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=30) as response:
                status = response.status
                response_body = response.read()
        except HTTPError as exc:
            if allow_not_found and exc.code == 404:
                return None
            detail = exc.read(2048).decode("utf-8", errors="replace")
            raise ReleasePublishError(
                f"RepoBase API {method} {path} failed with HTTP {exc.code}: {detail}"
            ) from exc
        except URLError as exc:
            raise ReleasePublishError(
                f"RepoBase API {method} {path} failed: {exc.reason}"
            ) from exc
        if status != expected_status:
            raise ReleasePublishError(
                f"RepoBase API {method} {path} returned HTTP {status}; "
                f"expected {expected_status}"
            )
        try:
            value = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise ReleasePublishError(
                f"RepoBase API {method} {path} returned invalid JSON"
            ) from exc
        if not isinstance(value, dict):
            raise ReleasePublishError(
                f"RepoBase API {method} {path} returned a non-object response"
            )
        return value

    def get_release_by_tag(self, tag: str) -> dict | None:
        return self._request_json(
            "GET",
            f"{self._repo_path}/releases/tags/{quote(tag, safe='')}",
            allow_not_found=True,
        )

    def create_draft(self, plan: ReleasePlan, notes: str) -> dict:
        response = self._request_json(
            "POST",
            f"{self._repo_path}/releases",
            {
                "tag_name": plan.tag,
                "target_commitish": EXPECTED_TARGET,
                "name": f"PeekNook {plan.tag}",
                "body": notes,
                "draft": True,
                "prerelease": plan.prerelease,
                "hide_archive_links": True,
            },
            expected_status=201,
        )
        assert response is not None
        return response

    def verify_asset(
        self, remote_asset: dict, local_asset: ReleaseAsset, tag: str
    ) -> None:
        download_url = remote_asset.get("browser_download_url")
        expected_url = (
            f"{EXPECTED_DOWNLOAD_BASE_URL}/{EXPECTED_REPOSITORY}/releases/download/"
            f"{quote(tag, safe='')}/{quote(local_asset.name, safe='._+-')}"
        )
        if not isinstance(download_url, str):
            raise ReleasePublishError(
                f"RepoBase asset has no download URL: {local_asset.name}"
            )
        if download_url != expected_url:
            raise ReleasePublishError(
                f"RepoBase asset URL is outside the public release channel: {local_asset.name}"
            )

        request = Request(download_url, headers={"Accept": "application/octet-stream"})
        digest = hashlib.sha256()
        downloaded_size = 0
        try:
            with urlopen(request, timeout=180) as response:
                while chunk := response.read(1024 * 1024):
                    downloaded_size += len(chunk)
                    digest.update(chunk)
        except (HTTPError, URLError) as exc:
            raise ReleasePublishError(
                f"Cannot verify existing RepoBase asset {local_asset.name}: {exc}"
            ) from exc
        if downloaded_size != local_asset.size or digest.hexdigest() != local_asset.sha256:
            raise ReleasePublishError(
                f"Existing RepoBase asset differs from local file: {local_asset.name}"
            )

    def upload_asset(self, release_id: int, asset: ReleaseAsset) -> dict:
        query = urlencode({"name": asset.name})
        url = (
            f"{EXPECTED_API_BASE_URL}{self._repo_path}/releases/"
            f"{release_id}/assets?{query}"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix="peeknook-curl-", delete=True
        ) as config:
            os.chmod(config.name, 0o600)
            config.write(f'header = "Authorization: token {self._token}"\n')
            config.flush()
            result = subprocess.run(
                [
                    "curl",
                    "--silent",
                    "--show-error",
                    "--fail-with-body",
                    "--request",
                    "POST",
                    "--config",
                    config.name,
                    "--header",
                    "Accept: application/json",
                    "--form",
                    f"attachment=@{asset.path}",
                    url,
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()[:2048]
            raise ReleasePublishError(
                f"RepoBase rejected asset {asset.name}: {detail}"
            )
        try:
            value = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ReleasePublishError(
                f"RepoBase returned invalid JSON for asset {asset.name}"
            ) from exc
        if not isinstance(value, dict):
            raise ReleasePublishError(
                f"RepoBase returned a non-object response for asset {asset.name}"
            )
        return value

    def get_release(self, release_id: int) -> dict:
        response = self._request_json(
            "GET", f"{self._repo_path}/releases/{release_id}"
        )
        assert response is not None
        return response

    def publish_draft(self, release_id: int) -> dict:
        response = self._request_json(
            "PATCH",
            f"{self._repo_path}/releases/{release_id}",
            {"draft": False},
        )
        assert response is not None
        return response


def publish_release(plan: ReleasePlan, notes: str, client: ReleaseClient) -> dict:
    existing = client.get_release_by_tag(plan.tag)
    if existing is not None:
        if existing.get("draft"):
            raise ReleasePublishError(
                f"RepoBase draft {plan.tag} already exists; refusing to resume or overwrite it"
            )
        remote_assets = existing.get("assets")
        if existing.get("tag_name") != plan.tag or not isinstance(remote_assets, list):
            raise ReleasePublishError(
                f"Existing RepoBase release {plan.tag} has unexpected metadata"
            )
        remote_by_name = {
            asset.get("name"): asset for asset in remote_assets if isinstance(asset, dict)
        }
        local_inventory = {(asset.name, asset.size) for asset in plan.assets}
        remote_inventory = {
            (name, asset.get("size")) for name, asset in remote_by_name.items()
        }
        if local_inventory != remote_inventory:
            raise ReleasePublishError(
                f"Existing RepoBase release {plan.tag} has a different asset inventory"
            )
        for asset in plan.assets:
            client.verify_asset(remote_by_name[asset.name], asset, plan.tag)
        return existing

    draft = client.create_draft(plan, notes)
    release_id = draft.get("id")
    if not isinstance(release_id, int) or not draft.get("draft"):
        raise ReleasePublishError("RepoBase did not create the expected draft release")

    try:
        for asset in sorted(
            plan.assets, key=lambda item: (item.name == "latest.json", item.name)
        ):
            uploaded = client.upload_asset(release_id, asset)
            if uploaded.get("name") != asset.name or uploaded.get("size") != asset.size:
                raise ReleasePublishError(
                    f"RepoBase asset response does not match local file: {asset.name}"
                )

        staged = client.get_release(release_id)
        remote_assets = staged.get("assets")
        if not isinstance(remote_assets, list):
            raise ReleasePublishError("RepoBase draft has no asset list")
        remote_inventory = {
            (asset.get("name"), asset.get("size"))
            for asset in remote_assets
            if isinstance(asset, dict)
        }
        local_inventory = {(asset.name, asset.size) for asset in plan.assets}
        if remote_inventory != local_inventory:
            raise ReleasePublishError(
                "RepoBase draft asset inventory does not match the validated local bundle"
            )

        published = client.publish_draft(release_id)
    except Exception as exc:
        raise ReleasePublishError(
            f"RepoBase draft release {release_id} remains unpublished after an error: {exc}"
        ) from exc

    if published.get("draft") or published.get("tag_name") != plan.tag:
        raise ReleasePublishError("RepoBase did not publish the expected release")
    return published


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate or publish signed PeekNook artifacts to RepoBase"
    )
    parser.add_argument("artifact_root", type=Path)
    parser.add_argument("--tag", required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("desktop/src-tauri/tauri.conf.json"),
        help="Tauri config whose version must match the release tag",
    )
    parser.add_argument(
        "--notes", default="Signed PeekNook desktop release", help="Release notes"
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Create a draft, upload every asset, then publish it",
    )
    parser.add_argument(
        "--confirm-repository",
        default="",
        help="Required exact repository slug when --publish is used",
    )
    parser.add_argument(
        "--token-env",
        default=DEFAULT_TOKEN_ENV,
        help="Environment variable containing the scoped RepoBase token",
    )
    args = parser.parse_args()

    try:
        plan = build_release_plan(args.artifact_root, args.tag, args.config)
        if not args.publish:
            print(json.dumps({"mode": "validate-only", **plan.as_dict()}, indent=2))
            return 0
        if args.confirm_repository != EXPECTED_REPOSITORY:
            raise ReleasePublishError(
                f"Publishing requires --confirm-repository {EXPECTED_REPOSITORY}"
            )
        token = os.getenv(args.token_env, "").strip()
        if not token:
            raise ReleasePublishError(
                f"Publishing requires a scoped token in {args.token_env}"
            )
        published = publish_release(plan, args.notes, ForgejoReleaseClient(token))
    except (ReleaseValidationError, ReleasePublishError) as exc:
        print(f"RepoBase release blocked: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "mode": "published",
                "repository": EXPECTED_REPOSITORY,
                "tag": plan.tag,
                "release_id": published.get("id"),
                "html_url": published.get("html_url"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
