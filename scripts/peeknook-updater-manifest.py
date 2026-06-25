#!/usr/bin/env python3
"""Generate Tauri static updater manifest (latest.json) for GitHub Releases."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def read_sig(sig_path: Path) -> str:
    return sig_path.read_text(encoding="utf-8").strip()


def add_platform(platforms: dict, key: str, artifact: Path, base_url: str) -> None:
    sig_path = Path(f"{artifact}.sig")
    if not artifact.exists() or not sig_path.exists():
        return
    platforms[key] = {
        "url": f"{base_url}/{artifact.name}",
        "signature": read_sig(sig_path),
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
    parser.add_argument("--repo", required=True, help="GitHub owner/repo")
    parser.add_argument("--notes", default="PeekNook release", help="Release notes")
    parser.add_argument("--out", default="latest.json", help="Output path")
    parser.add_argument("roots", nargs="+", help="Directories to scan for updater artifacts")
    args = parser.parse_args()

    version = args.version.lstrip("v")
    tag = args.tag if args.tag.startswith("v") else f"v{args.tag}"
    base_url = f"https://github.com/{args.repo}/releases/download/{tag}"
    roots = [Path(r) for r in args.roots]

    artifacts = scan_roots(roots)
    platforms: dict[str, dict[str, str]] = {}
    for key, artifact in artifacts.items():
        add_platform(platforms, key, artifact, base_url)

    if not platforms:
        print("No updater artifacts (.tar.gz/.exe + .sig) found under:", roots, file=sys.stderr)
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
