#!/usr/bin/env bash
# Embedded SurrealDB for PeekNook (no Docker). Stores data under PeekNook app dir.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="${PEEKNOOK_BIN_DIR:-$HOME/Library/Application Support/PeekNook/bin}"
DATA_DIR="${PEEKNOOK_DATA_DIR:-$HOME/Library/Application Support/PeekNook/data}"
SURREAL_BIN="${BIN_DIR}/surreal"
DB_PATH="${DATA_DIR}/peeknook.db"
PORT="${PEEKNOOK_SURREAL_PORT:-8001}"
LOG_FILE="${DATA_DIR}/surreal.log"
SURREAL_VERSION="${PEEKNOOK_SURREAL_VERSION:-v2.3.7}"

mkdir -p "$BIN_DIR" "$DATA_DIR"

download_surreal() {
  local arch os asset url tmp
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  case "$(uname -m)" in
    arm64|aarch64) arch="arm64" ;;
    x86_64|amd64) arch="amd64" ;;
    *) echo "Unsupported arch: $(uname -m)" >&2; exit 1 ;;
  esac
  if [[ "$os" == "darwin" ]]; then
    asset="surreal-${SURREAL_VERSION}.darwin-${arch}.tgz"
  elif [[ "$os" == "linux" ]]; then
    asset="surreal-${SURREAL_VERSION}.linux-${arch}.tgz"
  else
    echo "Unsupported OS: $os" >&2; exit 1
  fi
  url="https://github.com/surrealdb/surrealdb/releases/download/${SURREAL_VERSION}/${asset}"
  echo "Downloading SurrealDB ${SURREAL_VERSION}..."
  tmp="$(mktemp -d)"
  curl -fsSL "$url" -o "$tmp/surreal.tgz"
  tar -xzf "$tmp/surreal.tgz" -C "$tmp"
  install -m 755 "$tmp/surreal" "$SURREAL_BIN"
  rm -rf "$tmp"
  echo "Installed $SURREAL_BIN"
}

if [[ ! -x "$SURREAL_BIN" ]]; then
  download_surreal
fi

if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
  echo "SurrealDB already running on :${PORT}"
  exit 0
fi

if lsof -i ":${PORT}" >/dev/null 2>&1; then
  echo "Port ${PORT} in use; set PEEKNOOK_SURREAL_PORT" >&2
  exit 1
fi

nohup "$SURREAL_BIN" start \
  --log info \
  --bind "127.0.0.1:${PORT}" \
  --user root \
  --pass root \
  "rocksdb:${DB_PATH}" >>"$LOG_FILE" 2>&1 &

for i in $(seq 1 20); do
  if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    echo "SurrealDB ready on ws://127.0.0.1:${PORT}/rpc"
    exit 0
  fi
  sleep 1
done

echo "SurrealDB failed to start; see $LOG_FILE" >&2
exit 1
