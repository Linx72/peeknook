#!/usr/bin/env bash
# Build PeekNook backend binary with PyInstaller (Tauri sidecar).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
DIST="${PEEKNOOK_SIDECAR_DIST_DIR:-$ROOT/dist/peeknook-backend}"
TAURI_BIN="${PEEKNOOK_SIDECAR_OUTPUT_DIR:-$ROOT/desktop/src-tauri/binaries}"
TARGET="$(rustc -Vv 2>/dev/null | awk '/host:/ {print $2}')"

echo "Building PeekNook API bundle..."
uv run pip install pyinstaller >/dev/null 2>&1 || uv pip install pyinstaller

PYINSTALLER_EXTRA_ARGS=()
while IFS= read -r module_name; do
  # Windows Python writes CRLF to the Git Bash process substitution stream.
  # Remove the carriage return before passing the dynamic module to PyInstaller.
  module_name="${module_name//$'\r'/}"
  if [[ -n "$module_name" ]]; then
    echo "Including mypyc runtime module: $module_name"
    PYINSTALLER_EXTRA_ARGS+=(--hidden-import "$module_name")
  fi
done < <(uv run python - <<'PY'
from importlib.machinery import EXTENSION_SUFFIXES
from pathlib import Path
import site

modules = set()
for site_packages in map(Path, site.getsitepackages()):
    for path in site_packages.glob("*__mypyc*"):
        for suffix in EXTENSION_SUFFIXES:
            if path.name.endswith(suffix):
                modules.add(path.name[: -len(suffix)])
                break

for module in sorted(modules):
    print(module)
PY
)

uv run pyinstaller \
  --noconfirm \
  --clean \
  --onefile \
  --name peeknook-api \
  --distpath "$DIST" \
  --workpath "$ROOT/build/pyinstaller" \
  --specpath "$ROOT/scripts" \
  --copy-metadata imageio \
  --collect-data content_core \
  --collect-data podcast_creator \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.loops \
  --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.protocols \
  --hidden-import uvicorn.protocols.http \
  --hidden-import uvicorn.protocols.http.auto \
  --hidden-import uvicorn.lifespan \
  --hidden-import uvicorn.lifespan.on \
  "${PYINSTALLER_EXTRA_ARGS[@]}" \
  run_api.py

BUILT="$DIST/peeknook-api"
SUFFIX=""
if [[ -f "$DIST/peeknook-api.exe" ]]; then
  BUILT="$DIST/peeknook-api.exe"
  SUFFIX=".exe"
fi
if [[ ! -f "$BUILT" ]]; then
  echo "PeekNook sidecar output not found under $DIST" >&2
  exit 1
fi

echo "Testing frozen sidecar imports..."
SELF_TEST_DIR="$(mktemp -d "${TMPDIR:-/tmp}/peeknook-sidecar-self-test.XXXXXX")"
cleanup_self_test_dir() {
  case "$SELF_TEST_DIR" in
    "${TMPDIR:-/tmp}"/peeknook-sidecar-self-test.*)
      find "$SELF_TEST_DIR" -depth -delete
      ;;
    *)
      echo "Refusing to remove unexpected self-test directory: $SELF_TEST_DIR" >&2
      return 1
      ;;
  esac
}
trap cleanup_self_test_dir EXIT
(
  cd "$SELF_TEST_DIR"
  "$BUILT" --self-test
)
cleanup_self_test_dir
trap - EXIT

mkdir -p "$TAURI_BIN"
if [[ -n "$TARGET" ]]; then
  DESTINATION="$TAURI_BIN/peeknook-api-${TARGET}${SUFFIX}"
  cp "$BUILT" "$DESTINATION"
  chmod +x "$DESTINATION"
  echo "Sidecar: $DESTINATION"
fi

echo "Built: $BUILT"
ls -la "$BUILT"
