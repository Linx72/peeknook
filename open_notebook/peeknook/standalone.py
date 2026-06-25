"""
PeekNook embedded services — SurrealDB + worker without bash/uv (Tauri sidecar ready).
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path


def _app_support() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home())) / "PeekNook"
    else:
        base = Path.home() / "Library/Application Support/PeekNook"
    return base


def _project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]


def _health(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _surreal_paths() -> tuple[Path, Path, str]:
    port = os.getenv("PEEKNOOK_SURREAL_PORT", "8001")
    bin_dir = Path(os.getenv("PEEKNOOK_BIN_DIR", str(_app_support() / "bin")))
    data_dir = Path(os.getenv("PEEKNOOK_DATA_DIR", str(_app_support() / "data")))
    surreal_bin = bin_dir / ("surreal.exe" if os.name == "nt" else "surreal")
    return surreal_bin, data_dir, port


def _download_surreal(surreal_bin: Path) -> None:
    version = os.getenv("PEEKNOOK_SURREAL_VERSION", "v2.3.7")
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        arch = "arm64"
    elif machine in ("x86_64", "amd64"):
        arch = "amd64"
    else:
        raise RuntimeError(f"Unsupported arch: {machine}")

    system = platform.system().lower()
    if system == "darwin":
        asset = f"surreal-{version}.darwin-{arch}.tgz"
    elif system == "linux":
        asset = f"surreal-{version}.linux-{arch}.tgz"
    else:
        raise RuntimeError(f"Unsupported OS for embedded SurrealDB: {system}")

    url = f"https://github.com/surrealdb/surrealdb/releases/download/{version}/{asset}"
    surreal_bin.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tgz = Path(tmp) / "surreal.tgz"
        urllib.request.urlretrieve(url, tgz)
        with tarfile.open(tgz, "r:gz") as tar:
            tar.extractall(tmp)
        extracted = Path(tmp) / "surreal"
        shutil.copy2(extracted, surreal_bin)
        surreal_bin.chmod(0o755)


def ensure_embedded_surreal() -> None:
    if os.getenv("PEEKNOOK_EMBEDDED_DB", "true").lower() != "true":
        return

    surreal_bin, data_dir, port = _surreal_paths()
    health_url = f"http://127.0.0.1:{port}/health"
    if _health(health_url):
        return

    if not surreal_bin.exists():
        try:
            _download_surreal(surreal_bin)
        except Exception as exc:
            script = _project_root() / "scripts" / "peeknook-surreal-embedded.sh"
            if script.exists():
                subprocess.run(["bash", str(script)], check=False)
                if _health(health_url):
                    return
            raise RuntimeError(f"Failed to install SurrealDB: {exc}") from exc

    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "peeknook.db"
    log_file = data_dir / "surreal.log"
    log_handle = open(log_file, "a", encoding="utf-8")
    subprocess.Popen(
        [
            str(surreal_bin),
            "start",
            "--log",
            "info",
            "--bind",
            f"127.0.0.1:{port}",
            "--user",
            "root",
            "--pass",
            "root",
            f"rocksdb:{db_path}",
        ],
        stdout=log_handle,
        stderr=log_handle,
        start_new_session=True,
    )

    os.environ.setdefault("SURREAL_URL", f"ws://127.0.0.1:{port}/rpc")
    os.environ.setdefault("SURREAL_USER", "root")
    os.environ.setdefault("SURREAL_PASSWORD", "root")
    os.environ.setdefault("SURREAL_NAMESPACE", "peeknook")
    os.environ.setdefault("SURREAL_DATABASE", "peeknook")

    for _ in range(40):
        if _health(health_url):
            return
        time.sleep(0.5)
    raise RuntimeError(f"SurrealDB did not start on port {port}; see {log_file}")


def ensure_worker() -> None:
    if os.getenv("PEEKNOOK_SKIP_WORKER", "").lower() in ("1", "true", "yes"):
        return

    try:
        subprocess.run(
            ["pgrep", "-f", "surreal-commands-worker"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    root = _project_root()
    env = os.environ.copy()
    env_file = root / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    fallback = shutil.which("surreal-commands-worker")
    if fallback:
        subprocess.Popen([fallback, "--import-modules", "commands"], cwd=str(root), env=env, start_new_session=True)
        return

    uv = shutil.which("uv")
    if uv and (root / "pyproject.toml").exists():
        uv_cmd = [uv, "run", "surreal-commands-worker", "--import-modules", "commands"]
        if env_file.exists():
            uv_cmd = [uv, "run", "--env-file", str(env_file), "surreal-commands-worker", "--import-modules", "commands"]
        subprocess.Popen(uv_cmd, cwd=str(root), env=env, start_new_session=True)


def bootstrap_embedded_services() -> None:
    """Start SurrealDB + worker when embedded mode is on (dev or Tauri sidecar)."""
    embedded = os.getenv("PEEKNOOK_EMBEDDED_DB", "true").lower() == "true"
    standalone = os.getenv("PEEKNOOK_STANDALONE", "").lower() in ("1", "true", "yes")
    if not embedded and not standalone:
        return

    os.environ.setdefault("PEEKNOOK_EMBEDDED_DB", "true")
    os.environ.setdefault("API_RELOAD", "false")
    ensure_embedded_surreal()
    ensure_worker()


def bootstrap_standalone() -> None:
    """Alias for Tauri sidecar entry (sets PEEKNOOK_STANDALONE)."""
    os.environ.setdefault("PEEKNOOK_STANDALONE", "true")
    bootstrap_embedded_services()
