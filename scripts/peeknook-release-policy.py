#!/usr/bin/env python3
"""Fail closed when a public PeekNook release lacks signing credentials."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path

PUBLIC_RELEASE_REF_PREFIX = "refs/tags/v"
REQUIRED_PUBLIC_RELEASE_SECRETS = (
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


def is_public_release_ref(ref: str) -> bool:
    return ref.startswith(PUBLIC_RELEASE_REF_PREFIX)


def missing_release_secrets(environment: Mapping[str, str]) -> list[str]:
    return [
        name
        for name in REQUIRED_PUBLIC_RELEASE_SECRETS
        if not environment.get(name, "").strip()
    ]


def expected_release_ref(config_path: Path) -> str:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        version = config["version"]
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        raise ValueError(
            f"Cannot read the Tauri version from {config_path}: {exc}"
        ) from exc
    if not isinstance(version, str) or not version.strip():
        raise ValueError(f"Invalid Tauri version in {config_path}: {version!r}")
    return f"refs/tags/v{version}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate credentials required for a public PeekNook release"
    )
    parser.add_argument(
        "--ref",
        default=os.getenv("GITHUB_REF", ""),
        help="Git ref being built, for example refs/tags/v0.3.0",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("desktop/src-tauri/tauri.conf.json"),
        help="Tauri config whose version must match a public release tag",
    )
    args = parser.parse_args()

    if not is_public_release_ref(args.ref):
        print(
            "Release policy: non-tag build; unsigned QA artifacts are allowed "
            "and cannot be published by the release workflow."
        )
        return 0

    try:
        expected_ref = expected_release_ref(args.config)
    except ValueError as exc:
        print(f"Public release blocked: {exc}", file=sys.stderr)
        return 1
    if args.ref != expected_ref:
        print(
            f"Public release blocked: tag ref {args.ref} does not match "
            f"the configured version ({expected_ref}).",
            file=sys.stderr,
        )
        return 1

    missing = missing_release_secrets(os.environ)
    if missing:
        print(
            "Public release blocked: required signing secrets are missing:",
            file=sys.stderr,
        )
        for name in missing:
            print(f"  - {name}", file=sys.stderr)
        return 1

    print(
        "Release policy: all updater, Apple, Windows, and RepoBase release "
        "credentials are present for this public tag."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
