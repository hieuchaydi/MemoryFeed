from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.indexer import IndexerService
from backend.native_accel import rrf_fuse_fast
from backend.store import IMAGE_CACHE_DIR, Store


class Searcher:
    def __init__(self, store: Store, indexer: IndexerService) -> None:
        self.store = store
        self.indexer = indexer

    async def search(self, query: str, limit: int = 10, days_back: int | None = None) -> list[dict[str, Any]]:
        q = (query or "").strip()
        if not q:
            return []

        fts_task = asyncio.to_thread(self.store.search_fts, q, 20, days_back)
        sem_task = self.indexer.semantic_search(q, 20)
        fts_hits, sem_hits = await asyncio.gather(fts_task, sem_task)

        fts_ids = [item["id"] for item in fts_hits]
        sem_ids = [item.id for item in sem_hits]
        score_map = rrf_fuse_fast(fts_ids, sem_ids, k=60)
        all_ids = list(dict.fromkeys([*fts_ids, *sem_ids]))

        items_by_id = await asyncio.to_thread(self.store.get_items_by_ids, all_ids)

        cutoff: datetime | None = None
        if days_back is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        merged: list[dict[str, Any]] = []
        for item_id, score in sorted(score_map.items(), key=lambda kv: kv[1], reverse=True):
            item = items_by_id.get(item_id)
            if not item:
                continue
            captured_dt = _parse_iso(item.get("captured_at"))
            if cutoff and captured_dt and captured_dt < cutoff:
                continue

            image_urls = item.get("image_urls") or []
            cache_paths = item.get("image_cache_paths") or []
            thumbnail = cache_paths[0] if cache_paths else (image_urls[0] if image_urls else None)
            thumbnail = _normalize_thumbnail(thumbnail)
            text_excerpt = (item.get("text_content") or "").strip()[:200]

            merged.append(
                {
                    "id": item_id,
                    "url": item.get("url"),
                    "platform": item.get("platform", "unknown"),
                    "text_content": item.get("text_content") or "",
                    "text_excerpt": text_excerpt,
                    "thumbnail": thumbnail,
                    "author": item.get("author"),
                    "captured_at": item.get("captured_at"),
                    "score": round(float(score), 8),
                    "starred": bool(item.get("starred", False)),
                    "note": item.get("note"),
                    "tags": item.get("tags", []),
                }
            )
            if len(merged) >= limit:
                break

        return merged


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _normalize_thumbnail(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith(("http://", "https://", "/images/")):
        return value
    p = Path(value)
    try:
        if p.exists() and p.parent.resolve() == IMAGE_CACHE_DIR.resolve():
            return f"/images/{p.name}"
    except Exception:
        return None
    return None
