"""PeekNook sync + setup API routes."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from open_notebook.peeknook.auto_sync import run_sync_cycle, start_auto_sync
from open_notebook.peeknook.cloud_sync import pull_from_cloud, push_to_cloud
from open_notebook.peeknook.settings_store import get_settings, list_conflicts, set_setting
from open_notebook.peeknook.sync_store import init_sync_store, list_pending, record_event

router = APIRouter(prefix="/peeknook", tags=["peeknook"])


def _app_version() -> str:
    root = Path(__file__).resolve().parents[2]
    conf = root / "desktop/src-tauri/tauri.conf.json"
    if conf.is_file():
        try:
            return str(json.loads(conf.read_text(encoding="utf-8")).get("version", "?"))
        except (json.JSONDecodeError, OSError):
            pass
    return "?"


def _github_apple_secrets_set() -> bool:
    import subprocess

    repo = os.environ.get("PEEKNOOK_GITHUB_REPO", "Linx72/peeknook")
    try:
        r = subprocess.run(
            ["gh", "secret", "list", "--repo", repo],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if r.returncode != 0:
            return False
        return any(line.split()[0] == "APPLE_ID" for line in r.stdout.splitlines() if line.strip())
    except Exception:
        return False


def _env_prod_stripe_ready() -> bool:
    env = Path(__file__).resolve().parents[2] / "cloud/.env.prod"
    if not env.is_file():
        return False

    def has_key(key: str) -> bool:
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                return bool(line.split("=", 1)[1].strip())
        return False

    return has_key("STRIPE_SECRET_KEY") and has_key("STRIPE_PRICE_PRO")


GATE_COMMANDS: Dict[str, str] = {
    "physical_two_mac": "./scripts/peeknook-pdf-sync-two-mac.sh push  # Mac A → peeknook-two-mac-machine-b.sh --record on B",
    "env_prod_ready": "./scripts/peeknook-env-prod-init.sh",
    "vps_deploy": "PEEKNOOK_VPS_SSH=user@host ./scripts/peeknook-vps-deploy.sh",
    "apple_notarize": "./scripts/peeknook-apple-secrets-hints.sh",
}


class CloudSyncRequest(BaseModel):
    cloud_url: str = Field(..., description="PeekNook Cloud base URL")
    token: str = Field(..., description="Bearer JWT from cloud auth")


class SyncSettingsBody(BaseModel):
    cloud_url: Optional[str] = None
    cloud_token: Optional[str] = None
    auto_sync: Optional[bool] = None
    auto_sync_interval_sec: Optional[int] = Field(default=None, ge=60, le=86400)
    e2e_sync: Optional[bool] = None


@router.get("/setup-status")
async def setup_status() -> Dict[str, Any]:
    from open_notebook.domain.credential import Credential
    from open_notebook.database.repository import repo_query

    init_sync_store()
    ollama = await Credential.get_by_provider("ollama")
    model_count = await repo_query("SELECT count() AS c FROM model GROUP ALL", {})
    notebooks = await repo_query("SELECT count() AS c FROM notebook GROUP ALL", {})

    settings = get_settings()
    return {
        "product": "PeekNook",
        "ollama_configured": len(ollama) > 0,
        "ollama_url": ollama[0].base_url if ollama else None,
        "model_count": model_count[0]["c"] if model_count else 0,
        "notebook_count": notebooks[0]["c"] if notebooks else 0,
        "sync_pending": len(list_pending()),
        "auto_sync": settings.get("auto_sync", False),
        "e2e_sync": settings.get("e2e_sync", False),
        "cloud_configured": bool(settings.get("cloud_url") and settings.get("cloud_token")),
        "cloud_url": settings.get("cloud_url") or None,
    }


@router.get("/settings")
async def peeknook_settings() -> Dict[str, Any]:
    init_sync_store()
    s = get_settings()
    return {
        "cloud_url": s.get("cloud_url"),
        "auto_sync": s.get("auto_sync", False),
        "auto_sync_interval_sec": int(s.get("auto_sync_interval_sec", 300) or 300),
        "e2e_sync": s.get("e2e_sync", False),
        "has_token": bool(s.get("cloud_token")),
        "last_sync_at": s.get("last_sync_at"),
        "last_sync_status": s.get("last_sync_status"),
    }


@router.put("/settings")
async def update_settings(body: SyncSettingsBody) -> Dict[str, Any]:
    init_sync_store()
    if body.cloud_url is not None:
        set_setting("cloud_url", body.cloud_url)
    if body.cloud_token is not None:
        set_setting("cloud_token", body.cloud_token)
    if body.auto_sync is not None:
        set_setting("auto_sync", "true" if body.auto_sync else "false")
        if body.auto_sync:
            start_auto_sync()
    if body.auto_sync_interval_sec is not None:
        set_setting("auto_sync_interval_sec", str(body.auto_sync_interval_sec))
    if body.e2e_sync is not None:
        set_setting("e2e_sync", "true" if body.e2e_sync else "false")
    return await peeknook_settings()


@router.get("/sync/pending")
async def sync_pending(limit: int = 50) -> List[Dict[str, Any]]:
    init_sync_store()
    return list_pending(limit=limit)


@router.get("/sync/conflicts")
async def sync_conflicts(limit: int = 50) -> List[Dict[str, Any]]:
    init_sync_store()
    return list_conflicts(limit=limit)


@router.post("/sync/push")
async def sync_push(body: CloudSyncRequest) -> Dict[str, Any]:
    init_sync_store()
    set_setting("cloud_url", body.cloud_url)
    set_setting("cloud_token", body.token)
    return await push_to_cloud(body.cloud_url, body.token)


@router.post("/sync/pull")
async def sync_pull(body: CloudSyncRequest, since: Optional[str] = None) -> Dict[str, Any]:
    init_sync_store()
    set_setting("cloud_url", body.cloud_url)
    set_setting("cloud_token", body.token)
    return await pull_from_cloud(body.cloud_url, body.token, since=since)


@router.post("/sync/run")
async def sync_run_now() -> Dict[str, Any]:
    init_sync_store()
    return await run_sync_cycle()


@router.post("/sync/test-event")
async def sync_test_event() -> Dict[str, str]:
    init_sync_store()
    eid = record_event("system", "peeknook", "ping", {"source": "api"})
    return {"event_id": eid}


@router.get("/two-mac-handoff")
async def two_mac_handoff() -> Dict[str, Any]:
    """Read machine-A handoff file for physical two-Mac PDF sync (if present)."""
    default = Path.home() / "Library/Application Support/PeekNook/two-mac-handoff.json"
    path = Path(os.environ.get("PEEKNOOK_TWO_MAC_HANDOFF", str(default)))
    if not path.is_file():
        return {"available": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"available": False}
    return {"available": True, **data}


@router.get("/termitpro/status")
async def termitpro_local_status() -> Dict[str, Any]:
    from open_notebook.peeknook.termitpro_bridge import termitpro_status

    return await termitpro_status()


@router.get("/termitpro/notebooks")
async def termitpro_local_notebooks(limit: int = 50) -> Dict[str, Any]:
    from open_notebook.peeknook.termitpro_bridge import termitpro_list_notebooks

    return {"notebooks": await termitpro_list_notebooks(limit=limit)}


@router.get("/termitpro/search")
async def termitpro_local_search(q: str, limit: int = 20) -> Dict[str, Any]:
    from open_notebook.peeknook.termitpro_bridge import termitpro_search

    return {"query": q, "results": await termitpro_search(q, limit=limit)}


@router.get("/ollama/status")
async def ollama_status() -> Dict[str, Any]:
    import httpx

    from open_notebook.domain.credential import Credential

    creds = await Credential.get_by_provider("ollama")
    url = creds[0].base_url if creds else "http://127.0.0.1:11434"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{url.rstrip('/')}/api/tags")
            tags = r.json().get("models", []) if r.status_code == 200 else []
        return {
            "reachable": True,
            "url": url,
            "model_count": len(tags),
            "models": [m.get("name") for m in tags[:10]],
        }
    except Exception as exc:
        return {"reachable": False, "url": url, "error": str(exc), "hint": "Start Ollama: ollama serve"}


@router.get("/cloud-health")
async def cloud_health() -> Dict[str, Any]:
    """Probe configured PeekNook Cloud /health (server-side; avoids browser CORS)."""
    import httpx

    s = get_settings()
    base = (s.get("cloud_url") or "").rstrip("/")
    if not base:
        return {"configured": False, "ok": False}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{base}/health")
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        return {
            "configured": True,
            "ok": r.status_code == 200,
            "url": base,
            "version": data.get("version"),
            "status": data.get("status"),
        }
    except Exception as exc:
        return {"configured": True, "ok": False, "url": base, "error": str(exc)}


@router.get("/ship-status")
async def ship_status() -> Dict[str, Any]:
    """Automated ship gate status for Settings checklist (local machine)."""
    signoff = Path.home() / "Library/Application Support/PeekNook/qa-signoff.json"
    physical: Dict[str, Any] = {"done": False}
    if signoff.is_file():
        try:
            data = json.loads(signoff.read_text(encoding="utf-8"))
            pt = data.get("physical_two_mac") or {}
            if isinstance(pt, dict) and pt.get("completed_at"):
                physical = {"done": True, **pt}
        except (json.JSONDecodeError, OSError):
            pass

    handoff = await two_mac_handoff()
    cloud = await cloud_health()
    s = get_settings()
    cloud_url = (s.get("cloud_url") or "").strip()

    stripe_live = False
    if cloud.get("configured") and cloud.get("ok") and cloud.get("url"):
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{cloud['url'].rstrip('/')}/billing/config")
            if r.status_code == 200:
                stripe_live = bool(r.json().get("stripe_live"))
        except Exception:
            pass

    deploy_pack = Path.home() / "Library/Application Support/PeekNook/peeknook-cloud-deploy.tgz"
    vps_prod = bool(
        cloud.get("ok")
        and cloud_url.startswith("https://")
        and "127.0.0.1" not in cloud_url
        and "localhost" not in cloud_url
    )
    apple_secrets = _github_apple_secrets_set()
    env_prod_ready = _env_prod_stripe_ready()

    raw_gates = [
        ("physical_two_mac", physical.get("done", False)),
        ("cloud_configured", bool(cloud.get("configured") and cloud.get("ok"))),
        ("handoff_ready", handoff.get("available", False)),
        ("env_prod_ready", env_prod_ready),
        ("stripe_live", stripe_live),
        ("vps_deploy", vps_prod),
        ("apple_notarize", apple_secrets),
    ]
    gates = [
        {
            "id": gid,
            "done": done,
            "automated": True,
            **({"command": GATE_COMMANDS[gid]} if gid in GATE_COMMANDS else {}),
        }
        for gid, done in raw_gates
    ]
    done_count = sum(1 for g in gates if g["done"])

    return {
        "version": _app_version(),
        "physical_two_mac": physical,
        "handoff": {"available": handoff.get("available", False), "source_id": handoff.get("source_id")},
        "cloud_health": cloud,
        "stripe_live": stripe_live,
        "deploy_pack_ready": deploy_pack.is_file(),
        "vps_prod": vps_prod,
        "env_prod_ready": env_prod_ready,
        "apple_secrets": apple_secrets,
        "gates_done": done_count,
        "gates_total": len(gates),
        "gates": gates,
    }


@router.get("/sync/status")
async def sync_status() -> Dict[str, Any]:
    init_sync_store()
    s = get_settings()
    return {
        "pending": len(list_pending()),
        "auto_sync": s.get("auto_sync", False),
        "last_sync_at": s.get("last_sync_at"),
        "last_sync_status": s.get("last_sync_status"),
        "cloud_configured": bool(s.get("cloud_url") and s.get("cloud_token")),
    }
