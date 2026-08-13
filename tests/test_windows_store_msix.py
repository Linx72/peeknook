"""Contract tests for the certificate-free Microsoft Store MSIX path."""

import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/peeknook-build-windows-store-msix.ps1"
BACKEND_SCRIPT = ROOT / "scripts/build-backend.sh"
WORKFLOW = ROOT / ".github/workflows/peeknook-windows-store-msix.yml"
STORE_CONFIG = ROOT / "desktop/src-tauri/tauri.microsoft-store.conf.json"


def test_store_config_disables_external_updater_artifacts():
    config = json.loads(STORE_CONFIG.read_text(encoding="utf-8"))

    assert config["bundle"]["active"] is False
    assert config["bundle"]["createUpdaterArtifacts"] is False
    assert config["plugins"]["updater"]["endpoints"] == []


def test_msix_builder_is_unsigned_and_fail_closed():
    script = SCRIPT.read_text(encoding="utf-8")

    assert 'ValidateSet("Qa", "PartnerCenter")' in script
    assert "-ConfirmPartnerCenterIdentity" in script
    assert 'directDistributionAllowed = $false' in script
    assert 'signed = $false' in script
    assert 'rescap:Capability Name="runFullTrust"' in script
    assert 'uap10:RuntimeBehavior="packagedClassicApp"' in script
    assert "MakeAppx.exe" in script
    assert "SignTool" not in script


def test_windows_sidecar_hidden_import_strips_crlf():
    script = BACKEND_SCRIPT.read_text(encoding="utf-8")

    assert 'module_name="${module_name//$\'\\r\'/}"' in script


def test_store_workflow_is_manual_qa_only():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "push:" not in workflow
    assert "pull_request:" not in workflow
    assert "runs-on: windows-2025" in workflow
    assert "VITE_PEEKNOOK_DISTRIBUTION: windows-store" in workflow
    assert "peeknook-build-windows-store-msix.ps1 -Mode Qa" in workflow
    assert "upload-artifact@v4" in workflow
    assert "Microsoft Store submission" not in workflow
