#!/usr/bin/env bash
# Bump PeekNook semver across Tauri, UI, desktop package, cloud API, releaseAssets fallback.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NEW="${1:-}"

if [[ -z "$NEW" ]]; then
  python3 -c "import json; print(json.load(open('$ROOT/desktop/src-tauri/tauri.conf.json'))['version'])"
  echo "Usage: $0 0.2.1" >&2
  exit 1
fi

python3 <<PY
import json, pathlib, re
root = pathlib.Path("$ROOT")
ver = "$NEW"
tag = f"v{ver}"

def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")

write_json(root / "desktop/src-tauri/tauri.conf.json", {
    **json.loads((root / "desktop/src-tauri/tauri.conf.json").read_text()),
    "version": ver,
})

for pkg in ("ui/package.json", "desktop/package.json"):
    p = root / pkg
    d = json.loads(p.read_text())
    d["version"] = ver
    write_json(p, d)

main_py = root / "cloud/api/main.py"
text = main_py.read_text()
text = re.sub(
    r'FastAPI\(title="PeekNook Cloud API", version="[\d.]+"\)',
    f'FastAPI(title="PeekNook Cloud API", version="{ver}")',
    text,
)
text = re.sub(
    r'("service": "peeknook-cloud", "version": )"[\d.]+"',
    rf'\1"{ver}"',
    text,
    count=1,
)
main_py.write_text(text)

assets = root / "ui/src/lib/releaseAssets.ts"
assets.write_text(re.sub(
    r"fallbackAssets\(version = '[\d.]+'\)",
    f"fallbackAssets(version = '{ver}')",
    assets.read_text(),
))

print(f"OK — bumped to {ver} ({tag})")
print("Next:")
print(f"  ./scripts/peeknook-ship-complete.sh")
print(f"  ./scripts/peeknook-local-release.sh  # or ./scripts/peeknook-retry-release-ci.sh {tag}")
PY
