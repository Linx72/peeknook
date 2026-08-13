#!/usr/bin/env python3
"""Create the temporary Tauri config used for PeekNook release builds."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
THUMBPRINT_PATTERN = re.compile(r"^[A-Fa-f0-9]{40,64}$")
DEFAULT_WINDOWS_TIMESTAMP_URL = "http://timestamp.digicert.com"
DEFAULT_RELEASE_BASE_URL = "https://github.com"


def normalize_release_base_url(base_url: str) -> str:
    parsed = urlsplit(base_url.strip())
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"Invalid HTTPS release base URL: {base_url}")
    normalized_path = parsed.path.rstrip("/")
    return urlunsplit(("https", parsed.netloc, normalized_path, "", ""))


def updater_endpoint(release_base_url: str, repository: str, tag: str) -> str:
    if not REPOSITORY_PATTERN.fullmatch(repository):
        raise ValueError(f"Invalid release repository slug: {repository}")
    normalized_base_url = normalize_release_base_url(release_base_url)
    normalized_tag = tag.strip()
    if not normalized_tag or "/" in normalized_tag:
        raise ValueError(f"Invalid release tag: {tag}")
    if normalized_tag == "latest":
        return (
            f"{normalized_base_url}/{repository}/releases/latest/download/latest.json"
        )
    return (
        f"{normalized_base_url}/{repository}/releases/download/"
        f"{normalized_tag}/latest.json"
    )


def build_config(
    repository: str,
    tag: str,
    windows_thumbprint: str = "",
    windows_timestamp_url: str = "",
    release_base_url: str = DEFAULT_RELEASE_BASE_URL,
) -> dict:
    config: dict = {
        "plugins": {
            "updater": {
                "endpoints": [updater_endpoint(release_base_url, repository, tag)]
            },
        }
    }
    if windows_thumbprint:
        if not THUMBPRINT_PATTERN.fullmatch(windows_thumbprint):
            raise ValueError("Windows certificate thumbprint must be 40-64 hex digits")
        config["bundle"] = {
            "windows": {
                "certificateThumbprint": windows_thumbprint.upper(),
                "digestAlgorithm": "sha256",
                "timestampUrl": (
                    windows_timestamp_url.strip() or DEFAULT_WINDOWS_TIMESTAMP_URL
                ),
            }
        }
    return config


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a PeekNook Tauri config")
    parser.add_argument("--repo", required=True, help="Release owner/repository")
    parser.add_argument("--tag", required=True, help="Release tag or latest")
    parser.add_argument("--out", required=True, help="Destination JSON file")
    parser.add_argument(
        "--release-base-url",
        default=os.getenv("PEEKNOOK_RELEASE_BASE_URL", DEFAULT_RELEASE_BASE_URL),
        help="Public HTTPS root that serves release assets",
    )
    parser.add_argument(
        "--windows-thumbprint",
        default=os.getenv("WINDOWS_CERTIFICATE_THUMBPRINT", ""),
        help="Optional Windows certificate thumbprint",
    )
    parser.add_argument(
        "--windows-timestamp-url",
        default=os.getenv("WINDOWS_SIGNING_TIMESTAMP_URL", ""),
        help="Optional Windows RFC 3161 timestamp server",
    )
    args = parser.parse_args()

    try:
        config = build_config(
            args.repo,
            args.tag,
            args.windows_thumbprint,
            args.windows_timestamp_url,
            args.release_base_url,
        )
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    output = Path(args.out)
    output.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote Tauri release config: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
