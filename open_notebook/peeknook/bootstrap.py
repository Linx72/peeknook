"""
PeekNook first-run bootstrap.

When enabled, probes local Ollama, creates a credential if missing, registers
common models, and auto-assigns defaults so the app works out of the box.
"""

from __future__ import annotations

import os
import re
from typing import Iterable, List, Optional, Tuple

import httpx
from loguru import logger

from api.credentials_service import discover_with_config, register_models, require_encryption_key
from api.models import RegisterModelData
from open_notebook.ai.model_discovery import classify_model_type
from open_notebook.domain.credential import Credential

DEFAULT_OLLAMA_URLS = (
    "http://127.0.0.1:11434",
    "http://localhost:11434",
    "http://host.docker.internal:11434",
)

LANGUAGE_PREFERENCES = (
    re.compile(r"qwen3\.?6", re.I),
    re.compile(r"qwen3", re.I),
    re.compile(r"qwen2\.5-coder", re.I),
    re.compile(r"qwen2\.5", re.I),
    re.compile(r"mistral", re.I),
    re.compile(r"llama3", re.I),
)

EMBEDDING_PREFERENCES = (
    re.compile(r"nomic-embed", re.I),
    re.compile(r"embed", re.I),
)


def _enabled() -> bool:
    return os.getenv("PEEKNOOK_AUTO_OLLAMA", "true").lower() in ("1", "true", "yes", "on")


def _candidate_urls() -> List[str]:
    raw = os.getenv("PEEKNOOK_OLLAMA_URLS") or os.getenv("OLLAMA_API_BASE")
    if raw and not raw.startswith("http"):
        raw = f"http://{raw}"
    urls: List[str] = []
    if raw:
        for part in raw.split(","):
            part = part.strip()
            if part:
                urls.append(part.rstrip("/"))
    for url in DEFAULT_OLLAMA_URLS:
        if url not in urls:
            urls.append(url)
    return urls


async def _probe_ollama(base_url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{base_url.rstrip('/')}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


def _pick_models(names: Iterable[str]) -> List[Tuple[str, str]]:
    """Return (name, model_type) pairs to register."""
    names_list = list(names)
    selected: List[Tuple[str, str]] = []
    used: set[str] = set()

    def add(name: str, model_type: str) -> None:
        key = (name.lower(), model_type)
        if key not in used:
            used.add(key)
            selected.append((name, model_type))

    for pattern in LANGUAGE_PREFERENCES:
        for name in names_list:
            if pattern.search(name):
                add(name, classify_model_type(name, "ollama") or "language")
                break

    for pattern in EMBEDDING_PREFERENCES:
        for name in names_list:
            if pattern.search(name):
                model_type = classify_model_type(name, "ollama") or "embedding"
                if model_type == "embedding":
                    add(name, "embedding")
                    break

    if not any(t == "language" for _, t in selected) and names_list:
        add(names_list[0], classify_model_type(names_list[0], "ollama") or "language")

    return selected


async def _auto_assign_defaults() -> None:
    from open_notebook.database.repository import repo_query
    from open_notebook.ai.models import DefaultModels

    defaults = await DefaultModels.get_instance()
    if defaults.default_chat_model:
        return

    all_models = await repo_query("SELECT * FROM model ORDER BY provider, name", {})
    if not all_models:
        return

    def pick(model_type: str, prefer: re.Pattern[str]) -> Optional[str]:
        typed = [m for m in all_models if m.get("type") == model_type]
        for model in typed:
            if prefer.search(model.get("name", "")):
                return model.get("id")
        return typed[0].get("id") if typed else None

    chat = pick("language", re.compile(r"qwen3", re.I)) or pick(
        "language", re.compile(r".", re.I)
    )
    embed = pick("embedding", re.compile(r"nomic", re.I))
    large = pick("language", re.compile(r"32b|large", re.I)) or chat

    if chat:
        defaults.default_chat_model = chat
        defaults.default_transformation_model = chat
        defaults.default_tools_model = chat
    if embed:
        defaults.default_embedding_model = embed
    if large:
        defaults.large_context_model = large

    if chat or embed:
        await defaults.update()
        logger.info("PeekNook: default models assigned")


async def bootstrap_peeknook() -> None:
    if not _enabled():
        logger.info("PeekNook bootstrap: auto Ollama disabled")
        return

    try:
        require_encryption_key()
    except ValueError as exc:
        logger.warning(f"PeekNook bootstrap skipped: {exc}")
        return

    existing = await Credential.get_by_provider("ollama")
    if existing:
        logger.info("PeekNook bootstrap: Ollama credential already exists")
        return

    base_url: Optional[str] = None
    for url in _candidate_urls():
        if await _probe_ollama(url):
            base_url = url
            break

    if not base_url:
        logger.info("PeekNook bootstrap: Ollama not reachable")
        return

    logger.info(f"PeekNook bootstrap: connecting Ollama at {base_url}")

    credential = Credential(
        name="PeekNook Local Ollama",
        provider="ollama",
        modalities=["language", "embedding"],
        base_url=base_url,
    )
    await credential.save()

    discovered = await discover_with_config("ollama", {"base_url": base_url})
    names = [m.get("name", "") for m in discovered if m.get("name")]
    to_register = _pick_models(names)

    if to_register and credential.id:
        models_data = [
            RegisterModelData(name=name, provider="ollama", model_type=model_type)
            for name, model_type in to_register
        ]
        result = await register_models(credential.id, models_data)
        logger.info(f"PeekNook bootstrap: registered models {result}")

    await _auto_assign_defaults()
    logger.success("PeekNook bootstrap completed")
