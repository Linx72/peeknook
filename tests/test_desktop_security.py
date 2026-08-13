"""Security regression tests for the packaged desktop API transport."""

import hashlib
import io
import tarfile
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from api.auth import PasswordAuthMiddleware
from api.main import DEFAULT_CORS_ORIGINS, _parse_cors_origins
from open_notebook.peeknook import standalone
from run_api import run_frozen_import_self_test


class _DownloadResponse(io.BytesIO):
    def __init__(self, payload: bytes):
        super().__init__(payload)
        self.headers = {"Content-Length": str(len(payload))}


def _protected_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(PasswordAuthMiddleware, excluded_paths=["/health"])

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/protected")
    def protected():
        return {"status": "ok"}

    return app


def _cors_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEFAULT_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/protected")
    def protected():
        return {"status": "ok"}

    return app


def test_desktop_token_protects_local_api(monkeypatch):
    monkeypatch.setenv("OPEN_NOTEBOOK_PASSWORD", "desktop-session-token")
    client = TestClient(_protected_app())

    assert client.get("/protected").status_code == 401
    assert (
        client.get(
            "/protected", headers={"Authorization": "Bearer wrong-token"}
        ).status_code
        == 401
    )
    assert (
        client.get(
            "/protected", headers={"Authorization": "Bearer desktop-session-token"}
        ).status_code
        == 200
    )
    assert client.get("/health").status_code == 200


def test_default_cors_allows_tauri_but_rejects_untrusted_origins():
    client = TestClient(_cors_app())
    preflight_headers = {
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    }

    allowed = client.options(
        "/protected",
        headers={"Origin": "tauri://localhost", **preflight_headers},
    )
    rejected = client.options(
        "/protected",
        headers={"Origin": "https://attacker.example", **preflight_headers},
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "tauri://localhost"
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers


def test_cors_origin_parser_preserves_explicit_wildcard_support():
    assert _parse_cors_origins("https://one.example, https://two.example") == [
        "https://one.example",
        "https://two.example",
    ]
    assert _parse_cors_origins("*") == ["*"]


def test_frozen_import_self_test_does_not_start_services(capsys):
    with patch(
        "open_notebook.peeknook.standalone.bootstrap_embedded_services"
    ) as bootstrap:
        run_frozen_import_self_test()

    bootstrap.assert_not_called()
    assert "PEEKNOOK_SIDECAR_IMPORTS_OK" in capsys.readouterr().out


def test_stop_embedded_services_terminates_only_owned_processes(monkeypatch):
    surreal_process = MagicMock()
    surreal_process.poll.return_value = None
    worker_process = MagicMock()
    worker_process.poll.return_value = None
    log_handle = MagicMock()
    monkeypatch.setattr(standalone, "_surreal_process", surreal_process)
    monkeypatch.setattr(standalone, "_worker_process", worker_process)
    monkeypatch.setattr(standalone, "_surreal_log_handle", log_handle)

    with patch.object(standalone, "_stop_process_tree") as stop_process_tree:
        standalone.stop_embedded_services()

    surreal_process.terminate.assert_called_once_with()
    surreal_process.wait.assert_called_once_with(timeout=10)
    stop_process_tree.assert_called_once_with(worker_process)
    log_handle.close.assert_called_once_with()
    assert standalone._surreal_process is None
    assert standalone._worker_process is None
    assert standalone._surreal_log_handle is None


def test_surreal_paths_use_desktop_session_port(monkeypatch, tmp_path):
    monkeypatch.setenv("PEEKNOOK_SURREAL_PORT", "54321")
    monkeypatch.setenv("PEEKNOOK_BIN_DIR", str(tmp_path / "bin"))
    monkeypatch.setenv("PEEKNOOK_DATA_DIR", str(tmp_path / "data"))

    surreal_bin, data_dir, port = standalone._surreal_paths()

    assert surreal_bin.parent == tmp_path / "bin"
    assert data_dir == tmp_path / "data"
    assert port == "54321"


def test_frozen_runtime_starts_worker_from_same_sidecar(monkeypatch, tmp_path):
    worker_process = MagicMock()
    worker_process.poll.return_value = None
    monkeypatch.delenv("PEEKNOOK_SKIP_WORKER", raising=False)
    monkeypatch.setattr(standalone.sys, "frozen", True, raising=False)
    monkeypatch.setattr(standalone, "_project_root", lambda: tmp_path)

    with patch.object(
        standalone.subprocess, "Popen", return_value=worker_process
    ) as popen:
        standalone.ensure_worker()
        standalone.ensure_worker()

    command = popen.call_args.args[0]
    popen.assert_called_once()
    assert command == [
        standalone.sys.executable,
        "--worker",
        "--import-modules",
        "commands",
    ]
    assert standalone._worker_process is worker_process
    standalone._worker_process = None


def test_windows_surreal_release_uses_pinned_executable(monkeypatch):
    monkeypatch.delenv("PEEKNOOK_SURREAL_VERSION", raising=False)
    monkeypatch.delenv("PEEKNOOK_SURREAL_SHA256", raising=False)
    monkeypatch.setattr(standalone.platform, "system", lambda: "Windows")
    monkeypatch.setattr(standalone.platform, "machine", lambda: "AMD64")

    version, asset, digest = standalone._surreal_release_asset()

    assert version == "v2.3.7"
    assert asset == "surreal-v2.3.7.windows-amd64.exe"
    assert digest == "e9990dddd6580bb2a45332cb8c65b11edf855d8e03303f31616d67fa4c50cc00"


def test_windows_arm64_surreal_release_fails_closed(monkeypatch):
    monkeypatch.setattr(standalone.platform, "system", lambda: "Windows")
    monkeypatch.setattr(standalone.platform, "machine", lambda: "ARM64")

    with pytest.raises(RuntimeError, match="does not provide a Windows ARM64"):
        standalone._surreal_release_asset()


def test_unpinned_surreal_version_requires_explicit_checksum(monkeypatch):
    monkeypatch.setenv("PEEKNOOK_SURREAL_VERSION", "v9.9.9")
    monkeypatch.delenv("PEEKNOOK_SURREAL_SHA256", raising=False)
    monkeypatch.setattr(standalone.platform, "system", lambda: "Windows")
    monkeypatch.setattr(standalone.platform, "machine", lambda: "AMD64")

    with pytest.raises(RuntimeError, match="is not pinned"):
        standalone._surreal_release_asset()


def test_windows_surreal_download_verifies_and_installs_atomically(
    monkeypatch, tmp_path
):
    payload = b"MZ\x00peeknook-surreal-test"
    expected_sha256 = hashlib.sha256(payload).hexdigest()
    monkeypatch.setenv("PEEKNOOK_SURREAL_VERSION", "v9.9.9")
    monkeypatch.setenv("PEEKNOOK_SURREAL_SHA256", expected_sha256)
    monkeypatch.setattr(standalone.platform, "system", lambda: "Windows")
    monkeypatch.setattr(standalone.platform, "machine", lambda: "AMD64")
    requested_urls = []

    def fake_urlopen(url, timeout):
        requested_urls.append((url, timeout))
        return _DownloadResponse(payload)

    monkeypatch.setattr(standalone.urllib.request, "urlopen", fake_urlopen)
    destination = tmp_path / "bin" / "surreal.exe"

    standalone._download_surreal(destination)

    assert destination.read_bytes() == payload
    assert requested_urls == [
        (
            "https://github.com/surrealdb/surrealdb/releases/download/"
            "v9.9.9/surreal-v9.9.9.windows-amd64.exe",
            30,
        )
    ]


def test_surreal_checksum_mismatch_preserves_existing_binary(monkeypatch, tmp_path):
    monkeypatch.setenv("PEEKNOOK_SURREAL_VERSION", "v9.9.9")
    monkeypatch.setenv("PEEKNOOK_SURREAL_SHA256", "0" * 64)
    monkeypatch.setattr(standalone.platform, "system", lambda: "Windows")
    monkeypatch.setattr(standalone.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(
        standalone.urllib.request,
        "urlopen",
        lambda _url, timeout: _DownloadResponse(b"unexpected"),
    )
    destination = tmp_path / "bin" / "surreal.exe"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"existing")

    with pytest.raises(RuntimeError, match="checksum mismatch"):
        standalone._download_surreal(destination)

    assert destination.read_bytes() == b"existing"


def test_surreal_archive_rejects_unexpected_member_path(tmp_path):
    archive = tmp_path / "surreal.tgz"
    with tarfile.open(archive, "w:gz") as tar:
        member = tarfile.TarInfo("../surreal")
        payload = b"binary"
        member.size = len(payload)
        tar.addfile(member, io.BytesIO(payload))

    destination = tmp_path / "surreal"
    with pytest.raises(RuntimeError, match="expected binary"):
        standalone._install_surreal_archive(archive, destination)

    assert not destination.exists()
