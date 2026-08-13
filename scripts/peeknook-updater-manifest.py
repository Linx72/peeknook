#!/usr/bin/env python3
"""Generate a Tauri static updater manifest for a public release channel."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def read_sig(sig_path: Path) -> str:
    return sig_path.read_text(encoding="utf-8").strip()


def add_platform(platforms: dict, key: str, artifact: Path, base_url: str) -> None:
    sig_path = Path(f"{artifact}.sig")
    if not artifact.exists() or not sig_path.exists():
        return
    signature = read_sig(sig_path)
    if not signature:
        raise ValueError(f"Updater signature is empty: {sig_path}")
    platforms[key] = {
        "url": f"{base_url}/{artifact.name}",
        "signature": signature,
    }


def scan_roots(roots: list[Path]) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for root in roots:
        if not root.exists():
            continue
        for tar in sorted(root.rglob("*.app.tar.gz")):
            if tar.name.endswith(".sig"):
                continue
            found.setdefault("darwin-aarch64", tar)
        for exe in sorted(root.rglob("*setup*.exe")):
            if exe.name.endswith(".sig"):
                continue
            found.setdefault("windows-x86_64", exe)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="Build latest.json for Tauri updater")
    parser.add_argument("--version", required=True, help="Semver without v prefix")
    parser.add_argument("--tag", required=True, help="Git tag, e.g. v0.2.0")
    parser.add_argument("--repo", required=True, help="Release owner/repository")
    parser.add_argument(
        "--release-base-url",
        default=os.getenv("PEEKNOOK_RELEASE_BASE_URL", "https://github.com"),
        help="Public HTTPS root that serves release assets",
    )
    parser.add_argument("--notes", default="PeekNook release", help="Release notes")
    parser.add_argument("--out", default="latest.json", help="Output path")
    parser.add_argument(
        "--require-platform",
        action="append",
        default=[],
        help="Platform key that must be present; may be repeated",
    )
    parser.add_argument(
        "roots", nargs="+", help="Directories to scan for updater artifacts"
    )
    args = parser.parse_args()

    version = args.version.lstrip("v")
    tag = args.tag if args.tag.startswith("v") else f"v{args.tag}"
    parsed_release_base = urlsplit(args.release_base_url.strip())
    if (
        parsed_release_base.scheme != "https"
        or not parsed_release_base.hostname
        or parsed_release_base.username
        or parsed_release_base.password
        or parsed_release_base.query
        or parsed_release_base.fragment
    ):
        print(
            "Release base URL must be HTTPS and contain no credentials", file=sys.stderr
        )
        return 1
    release_base_url = urlunsplit(
        (
            "https",
            parsed_release_base.netloc,
            parsed_release_base.path.rstrip("/"),
            "",
            "",
        )
    )
    base_url = f"{release_base_url}/{args.repo}/releases/download/{tag}"
    roots = [Path(r) for r in args.roots]

    artifacts = scan_roots(roots)
    platforms: dict[str, dict[str, str]] = {}
    try:
        for key, artifact in artifacts.items():
            add_platform(platforms, key, artifact, base_url)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    if not platforms:
        print(
            "No updater artifacts (.tar.gz/.exe + .sig) found under:",
            roots,
            file=sys.stderr,
        )
        return 1
    missing_platforms = sorted(set(args.require_platform) - platforms.keys())
    if missing_platforms:
        print(
            "Missing required updater platforms: " + ", ".join(missing_platforms),
            file=sys.stderr,
        )
        return 1

    manifest = {
        "version": version,
        "notes": args.notes,
        "pub_date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "platforms": platforms,
    }

    out = Path(args.out)
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out} with platforms: {', '.join(platforms.keys())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
