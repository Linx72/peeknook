#!/usr/bin/env python3
"""Validate the public PeekNook release-channel contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

DEFAULT_CONFIG = Path(__file__).parents[1] / "distribution/repobase-public/channel.json"
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
EXPECTED_KEYS = {
    "schema_version",
    "release_base_url",
    "repository",
    "visibility",
    "updater_manifest",
    "required_platforms",
    "source_repository",
    "source_visibility",
}
REQUIRED_PLATFORMS = {"darwin-aarch64", "windows-x86_64"}
EXPECTED_RELEASE_BASE_URL = "https://repobase.ru"
EXPECTED_RELEASE_REPOSITORY = "releases/peeknook-releases"
EXPECTED_SOURCE_REPOSITORY = "timeweb/peeknook"


def normalize_release_base_url(base_url: str) -> str:
    if not isinstance(base_url, str):
        raise ValueError("Release base URL must be a string")
    parsed = urlsplit(base_url.strip())
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Release base URL must be HTTPS and contain no credentials")
    return urlunsplit(("https", parsed.netloc, parsed.path.rstrip("/"), "", ""))


def validate_channel(config: dict) -> dict[str, object]:
    if not isinstance(config, dict):
        raise ValueError("Release-channel config must be a JSON object")
    missing = sorted(EXPECTED_KEYS - config.keys())
    unexpected = sorted(config.keys() - EXPECTED_KEYS)
    if missing:
        raise ValueError("Missing release-channel keys: " + ", ".join(missing))
    if unexpected:
        raise ValueError("Unexpected release-channel keys: " + ", ".join(unexpected))
    if config["schema_version"] != 1:
        raise ValueError("Unsupported release-channel schema version")

    repository = config["repository"]
    source_repository = config["source_repository"]
    if not isinstance(repository, str) or not REPOSITORY_PATTERN.fullmatch(repository):
        raise ValueError("Invalid public release repository slug")
    if not isinstance(source_repository, str) or not REPOSITORY_PATTERN.fullmatch(
        source_repository
    ):
        raise ValueError("Invalid private source repository slug")
    if repository == source_repository:
        raise ValueError("Public release repository must differ from private source")
    if repository != EXPECTED_RELEASE_REPOSITORY:
        raise ValueError("Unexpected public release repository")
    if source_repository != EXPECTED_SOURCE_REPOSITORY:
        raise ValueError("Unexpected private source repository")
    if config["visibility"] != "public":
        raise ValueError("Release repository visibility must be public")
    if config["source_visibility"] != "private":
        raise ValueError("Source repository visibility must remain private")

    manifest = config["updater_manifest"]
    if (
        not isinstance(manifest, str)
        or not manifest
        or manifest != Path(manifest).name
        or "/" in manifest
        or "\\" in manifest
        or not manifest.endswith(".json")
    ):
        raise ValueError("Updater manifest must be a JSON filename")

    platforms = config["required_platforms"]
    if (
        not isinstance(platforms, list)
        or any(not isinstance(platform, str) for platform in platforms)
        or len(platforms) != len(set(platforms))
        or set(platforms) != REQUIRED_PLATFORMS
    ):
        raise ValueError("Required platforms must be darwin-aarch64 and windows-x86_64")

    base_url = normalize_release_base_url(config["release_base_url"])
    if base_url != EXPECTED_RELEASE_BASE_URL:
        raise ValueError("Unexpected public release base URL")
    return {
        "repository": repository,
        "latest_manifest_url": (
            f"{base_url}/{repository}/releases/latest/download/{manifest}"
        ),
        "required_platforms": platforms,
        "source_repository": source_repository,
    }


def load_channel(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read release-channel config: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the public PeekNook release-channel contract"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--json", action="store_true", help="Print the validated contract as JSON"
    )
    args = parser.parse_args()

    try:
        contract = validate_channel(load_channel(args.config))
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(contract, indent=2))
    else:
        print(f"Public release channel: {contract['latest_manifest_url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
