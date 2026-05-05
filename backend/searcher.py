from __future__ import annotations

import asyncio
import time
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.indexer import IndexerService
from backend.native_accel import rrf_topk_fast
from backend.store import IMAGE_CACHE_DIR, Store


class Searcher:
    def __init__(self, store: Store, indexer: IndexerService) -> None:
        self.store = store
        self.indexer = indexer
        self._cache_ttl_s = 8.0
        self._cache_max_size = 256
        self._cache: dict[tuple[str, int, int | None, int], tuple[float, list[dict[str, Any]]]] = {}
        self._cache_lock = threading.Lock()
        self._data_epoch = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_evictions = 0
        self._search_calls = 0
        self._search_total_ms = 0.0
        self._search_last_ms = 0.0
        self._search_last_stage_ms: dict[str, float] = {
            "fts_sem_fetch": 0.0,
            "item_lookup": 0.0,
            "merge": 0.0,
        }

    async def search(self, query: str, limit: int = 10, days_back: int | None = None) -> list[dict[str, Any]]:
        started = time.perf_counter()
        q = (query or "").strip()
        if not q:
            return []
        cache_key = (q.lower(), int(limit), days_back, self._data_epoch)
        cached = self._cache_get(cache_key)
        if cached is not None:
            self._record_timing(started, {"fts_sem_fetch": 0.0, "item_lookup": 0.0, "merge": 0.0})
            return cached

        stage_started = time.perf_counter()
        fts_task = asyncio.to_thread(self.store.search_fts, q, 20, days_back)
        sem_task = self.indexer.semantic_search(q, 20)
        fts_hits, sem_hits = await asyncio.gather(fts_task, sem_task)
        stage_fetch_ms = (time.perf_counter() - stage_started) * 1000.0

        fts_ids = [item["id"] for item in fts_hits]
        sem_ids = [item.id for item in sem_hits]
        ranked = rrf_topk_fast(fts_ids, sem_ids, k=60, limit=max(limit * 4, 40))
        all_ids = [item_id for item_id, _ in ranked]

        stage_started = time.perf_counter()
        items_by_id = await asyncio.to_thread(self.store.get_items_by_ids, all_ids)
        stage_lookup_ms = (time.perf_counter() - stage_started) * 1000.0

        cutoff: datetime | None = None
        if days_back is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        stage_started = time.perf_counter()
        merged: list[dict[str, Any]] = []
        for item_id, score in ranked:
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
                    "heat": float(item.get("heat", 1.0) or 1.0),
                    "last_surfaced": item.get("last_surfaced"),
                    "surfaced_count": int(item.get("surfaced_count", 0) or 0),
                    "archived_at": item.get("archived_at"),
                }
            )
            if len(merged) >= limit:
                break
        stage_merge_ms = (time.perf_counter() - stage_started) * 1000.0

        self._cache_put(cache_key, merged)
        self._record_timing(
            started,
            {
                "fts_sem_fetch": stage_fetch_ms,
                "item_lookup": stage_lookup_ms,
                "merge": stage_merge_ms,
            },
        )
        return merged

    def bump_data_epoch(self) -> None:
        with self._cache_lock:
            self._data_epoch += 1
            self._cache.clear()

    def perf_stats(self) -> dict[str, int | float]:
        with self._cache_lock:
            return {
                "cache_entries": len(self._cache),
                "cache_ttl_seconds": self._cache_ttl_s,
                "cache_max_size": self._cache_max_size,
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "cache_evictions": self._cache_evictions,
                "data_epoch": self._data_epoch,
                "search_calls": self._search_calls,
                "search_last_ms": round(self._search_last_ms, 3),
                "search_avg_ms": round(self._search_total_ms / self._search_calls, 3) if self._search_calls else 0.0,
                "search_last_stage_ms": {k: round(v, 3) for k, v in self._search_last_stage_ms.items()},
            }

    def _cache_get(self, key: tuple[str, int, int | None, int]) -> list[dict[str, Any]] | None:
        now = time.monotonic()
        with self._cache_lock:
            row = self._cache.get(key)
            if not row:
                self._cache_misses += 1
                return None
            created_at, payload = row
            if now - created_at > self._cache_ttl_s:
                self._cache.pop(key, None)
                self._cache_misses += 1
                return None
            self._cache_hits += 1
            return [dict(item) for item in payload]

    def _cache_put(self, key: tuple[str, int, int | None, int], payload: list[dict[str, Any]]) -> None:
        with self._cache_lock:
            if len(self._cache) >= self._cache_max_size:
                oldest_key = min(self._cache, key=lambda k: self._cache[k][0])
                self._cache.pop(oldest_key, None)
                self._cache_evictions += 1
            self._cache[key] = (time.monotonic(), [dict(item) for item in payload])

    def _record_timing(self, started: float, stage_ms: dict[str, float]) -> None:
        elapsed = (time.perf_counter() - started) * 1000.0
        with self._cache_lock:
            self._search_calls += 1
            self._search_total_ms += elapsed
            self._search_last_ms = elapsed
            self._search_last_stage_ms = dict(stage_ms)


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
