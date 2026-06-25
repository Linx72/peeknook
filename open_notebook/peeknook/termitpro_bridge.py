"""Local TermitPro IDE bridge — expose PeekNook data to TermitPro via REST."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from open_notebook.database.repository import repo_query


async def termitpro_status() -> Dict[str, Any]:
    notebooks = await repo_query("SELECT count() AS c FROM notebook GROUP ALL", {})
    sources = await repo_query("SELECT count() AS c FROM source GROUP ALL", {})
    return {
        "service": "peeknook-desktop",
        "bridge": "termitpro/local",
        "notebook_count": notebooks[0]["c"] if notebooks else 0,
        "source_count": sources[0]["c"] if sources else 0,
    }


async def termitpro_list_notebooks(limit: int = 50) -> List[Dict[str, Any]]:
    rows = await repo_query(
        "SELECT id, name, description, updated FROM notebook ORDER BY updated DESC LIMIT $limit",
        {"limit": limit},
    )
    return [
        {
            "id": str(r.get("id", "")),
            "name": r.get("name"),
            "description": r.get("description"),
            "updated": str(r.get("updated", "")),
        }
        for r in (rows or [])
    ]


async def termitpro_search(q: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Simple search across notebook names and source titles."""
    needle = q.lower()
    hits: List[Dict[str, Any]] = []
    notebooks = await termitpro_list_notebooks(limit=100)
    for nb in notebooks:
        hay = f"{nb.get('name', '')} {nb.get('description', '')}".lower()
        if needle in hay:
            hits.append({"type": "notebook", **nb})
    src_rows = await repo_query(
        "SELECT id, title, updated FROM source ORDER BY updated DESC LIMIT 200",
        {},
    )
    for s in src_rows or []:
        title = (s.get("title") or "").lower()
        if needle in title:
            hits.append(
                {
                    "type": "source",
                    "id": str(s.get("id", "")),
                    "title": s.get("title"),
                    "updated": str(s.get("updated", "")),
                }
            )
        if len(hits) >= limit:
            break
    return hits[:limit]
