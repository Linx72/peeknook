"""
PeekNook embedded services — SurrealDB + worker without bash/uv (Tauri sidecar ready).
"""

from __future__ import annotations

import atexit
import hashlib
import os
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import IO

_surreal_process: subprocess.Popen[bytes] | None = None
_surreal_log_handle: IO[str] | None = None
_worker_process: subprocess.Popen[bytes] | None = None

DEFAULT_SURREAL_VERSION = "v2.3.7"
MAX_SURREAL_DOWNLOAD_BYTES = 200 * 1024 * 1024
SURREAL_RELEASE_SHA256 = {
    ("v2.3.7", "darwin", "amd64"): (
        "surreal-v2.3.7.darwin-amd64.tgz",
        "32e2291595b925aa438d82c02344767295ca1ee44e4c7e7fc1fe5866476847e4",
    ),
    ("v2.3.7", "darwin", "arm64"): (
        "surreal-v2.3.7.darwin-arm64.tgz",
        "0ce16f1b8275c27c10acaa375564a7dad4e0f3f6d3dfc895c3c382b8be7ade08",
    ),
    ("v2.3.7", "linux", "amd64"): (
        "surreal-v2.3.7.linux-amd64.tgz",
        "641093130b8208158fce4c6b88caee4c0a68d5fcfa39595cda8fefa4bc918c80",
    ),
    ("v2.3.7", "linux", "arm64"): (
        "surreal-v2.3.7.linux-arm64.tgz",
        "eda5d2b90728f49e111ec5edd44711c8b6db5b7945e846245c02cc2b5c788161",
    ),
    ("v2.3.7", "windows", "amd64"): (
        "surreal-v2.3.7.windows-amd64.exe",
        "e9990dddd6580bb2a45332cb8c65b11edf855d8e03303f31616d67fa4c50cc00",
    ),
}


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


def _normalize_architecture(machine: str) -> str:
    normalized = machine.lower()
    if normalized in ("arm64", "aarch64"):
        return "arm64"
    if normalized in ("x86_64", "amd64"):
        return "amd64"
    raise RuntimeError(f"Unsupported architecture for SurrealDB: {machine}")


def _surreal_release_asset() -> tuple[str, str, str]:
    version = os.getenv("PEEKNOOK_SURREAL_VERSION", DEFAULT_SURREAL_VERSION)
    system = platform.system().lower()
    arch = _normalize_architecture(platform.machine())
    if system not in ("darwin", "linux", "windows"):
        raise RuntimeError(f"Unsupported operating system for SurrealDB: {system}")
    if system == "windows" and arch == "arm64":
        raise RuntimeError(
            f"SurrealDB {version} does not provide a Windows ARM64 binary"
        )

    release = SURREAL_RELEASE_SHA256.get((version, system, arch))
    custom_sha256 = os.getenv("PEEKNOOK_SURREAL_SHA256")
    if release is None:
        if not custom_sha256:
            raise RuntimeError(
                f"SurrealDB {version} is not pinned for {system}-{arch}; "
                "set PEEKNOOK_SURREAL_SHA256 for an intentional version override"
            )
        extension = "exe" if system == "windows" else "tgz"
        asset = f"surreal-{version}.{system}-{arch}.{extension}"
        pinned_sha256 = custom_sha256
    else:
        asset, pinned_sha256 = release

    expected_sha256 = (custom_sha256 or pinned_sha256).lower()
    if len(expected_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in expected_sha256
    ):
        raise RuntimeError("PEEKNOOK_SURREAL_SHA256 must be a 64-character hex digest")
    return version, asset, expected_sha256


def _download_file(url: str, destination: Path) -> None:
    downloaded = 0
    with (
        urllib.request.urlopen(url, timeout=30) as response,
        destination.open("wb") as output,
    ):
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_SURREAL_DOWNLOAD_BYTES:
            raise RuntimeError(
                f"SurrealDB download is too large: {content_length} bytes"
            )
        while chunk := response.read(1024 * 1024):
            downloaded += len(chunk)
            if downloaded > MAX_SURREAL_DOWNLOAD_BYTES:
                raise RuntimeError("SurrealDB download exceeded the size limit")
            output.write(chunk)


def _verify_sha256(path: Path, expected_sha256: str) -> None:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    actual_sha256 = digest.hexdigest()
    if actual_sha256 != expected_sha256:
        raise RuntimeError(
            "SurrealDB checksum mismatch: "
            f"expected {expected_sha256}, received {actual_sha256}"
        )


def _install_surreal_archive(archive: Path, destination: Path) -> None:
    with tarfile.open(archive, "r:gz") as tar:
        try:
            member = tar.getmember("surreal")
        except KeyError as exc:
            raise RuntimeError(
                "SurrealDB archive does not contain the expected binary"
            ) from exc
        if not member.isfile():
            raise RuntimeError("SurrealDB archive entry is not a regular file")
        extracted = tar.extractfile(member)
        if extracted is None:
            raise RuntimeError("SurrealDB archive binary could not be read")
        with destination.open("wb") as output:
            shutil.copyfileobj(extracted, output)


def _download_surreal(surreal_bin: Path) -> None:
    version, asset, expected_sha256 = _surreal_release_asset()
    system = platform.system().lower()
    url = f"https://github.com/surrealdb/surrealdb/releases/download/{version}/{asset}"
    surreal_bin.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=surreal_bin.parent) as tmp:
        temporary_dir = Path(tmp)
        downloaded_asset = temporary_dir / asset
        staged_binary = temporary_dir / surreal_bin.name
        _download_file(url, downloaded_asset)
        _verify_sha256(downloaded_asset, expected_sha256)

        if system == "windows":
            shutil.copyfile(downloaded_asset, staged_binary)
        else:
            _install_surreal_archive(downloaded_asset, staged_binary)

        staged_binary.chmod(0o755)
        os.replace(staged_binary, surreal_bin)


def _stop_process(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _descendant_pids(root_pid: int) -> list[int]:
    if os.name == "nt":
        return []
    try:
        output = subprocess.run(
            ["ps", "-axo", "pid=,ppid="],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return []

    process_pairs: list[tuple[int, int]] = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) == 2 and all(field.isdigit() for field in fields):
            process_pairs.append((int(fields[0]), int(fields[1])))

    descendants: list[int] = []
    parents = [root_pid]
    while parents:
        parent_pid = parents.pop()
        for pid, candidate_parent in process_pairs:
            if candidate_parent == parent_pid and pid not in descendants:
                descendants.append(pid)
                parents.append(pid)
    return descendants


def _process_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _stop_process_tree(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        return

    process_tree = [*_descendant_pids(process.pid), process.pid]
    for pid in reversed(process_tree):
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if all(not _process_is_alive(pid) for pid in process_tree):
            break
        time.sleep(0.25)

    for pid in reversed(process_tree):
        if _process_is_alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def stop_embedded_services() -> None:
    """Stop only the local services started by this API process."""
    global _surreal_log_handle, _surreal_process, _worker_process

    _stop_process_tree(_worker_process)
    _worker_process = None
    _stop_process(_surreal_process)
    _surreal_process = None

    if _surreal_log_handle is not None:
        _surreal_log_handle.close()
        _surreal_log_handle = None


def ensure_embedded_surreal() -> None:
    global _surreal_log_handle, _surreal_process

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
    _surreal_log_handle = open(log_file, "a", encoding="utf-8")
    _surreal_process = subprocess.Popen(
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
        stdout=_surreal_log_handle,
        stderr=_surreal_log_handle,
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
    global _worker_process

    if os.getenv("PEEKNOOK_SKIP_WORKER", "").lower() in ("1", "true", "yes"):
        return
    if _worker_process is not None and _worker_process.poll() is None:
        return

    root = _project_root()
    env = os.environ.copy()
    env_file = root / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    if getattr(sys, "frozen", False):
        _worker_process = subprocess.Popen(
            [sys.executable, "--worker", "--import-modules", "commands"],
            cwd=str(root),
            env=env,
            start_new_session=True,
        )
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

    fallback = shutil.which("surreal-commands-worker")
    if fallback:
        _worker_process = subprocess.Popen(
            [fallback, "--import-modules", "commands"],
            cwd=str(root),
            env=env,
            start_new_session=True,
        )
        return

    uv = shutil.which("uv")
    if uv and (root / "pyproject.toml").exists():
        uv_cmd = [uv, "run", "surreal-commands-worker", "--import-modules", "commands"]
        if env_file.exists():
            uv_cmd = [
                uv,
                "run",
                "--env-file",
                str(env_file),
                "surreal-commands-worker",
                "--import-modules",
                "commands",
            ]
        _worker_process = subprocess.Popen(
            uv_cmd, cwd=str(root), env=env, start_new_session=True
        )


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


atexit.register(stop_embedded_services)
