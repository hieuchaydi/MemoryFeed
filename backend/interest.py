from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

from backend.searcher import Searcher
from backend.store import Store

logger = logging.getLogger(__name__)


class InterestEngine:
    """Maintains lightweight memory heat and context-aware resurfacing."""

    def __init__(self, store: Store, searcher: Searcher) -> None:
        self.store = store
        self.searcher = searcher
        self._last_decay_date: date | None = None
        self._decay_lock = asyncio.Lock()

    async def active_feed(self, limit: int = 20, mode: str = "default") -> list[dict[str, Any]]:
        await self._decay_once_per_day()
        return await asyncio.to_thread(self.store.smart_feed, limit, mode)

    async def resurface_context(
        self,
        context: str,
        limit: int = 5,
        source_item_id: str | None = None,
        bump_heat: bool = True,
    ) -> list[dict[str, Any]]:
        query = _compact_context(context)
        if not query:
            return []

        hits = await self.searcher.search(query=query, limit=min(max(limit * 3, limit + 5), 30))
        surfaced: list[dict[str, Any]] = []
        for idx, hit in enumerate(hits):
            if hit.get("id") == source_item_id or hit.get("archived_at"):
                continue

            row = dict(hit)
            row["surface_reason"] = "related_to_current_context"
            row["surface_score"] = round(float(row.get("score") or 0.0) + float(row.get("heat") or 1.0) * 0.1, 6)

            if bump_heat:
                delta = max(0.12, 0.42 - idx * 0.04)
                updated = await asyncio.to_thread(
                    self.store.bump_heat,
                    str(row["id"]),
                    delta,
                    True,
                )
                if updated:
                    row["heat"] = updated.get("heat", row.get("heat"))
                    row["last_surfaced"] = updated.get("last_surfaced")
                    row["surfaced_count"] = updated.get("surfaced_count", row.get("surfaced_count", 0))

            surfaced.append(row)
            if len(surfaced) >= limit:
                break

        return surfaced

    async def warm_related_for_item(self, item_id: str, limit: int = 5) -> int:
        item = await asyncio.to_thread(self.store.get_item, item_id)
        if not item:
            return 0
        query = _compact_context(
            "\n".join(
                [
                    str(item.get("text_content") or ""),
                    " ".join(item.get("image_captions") or []),
                ]
            )
        )
        if not query:
            return 0

        hits = await self.searcher.search(query=query, limit=max(limit + 4, 10))
        warmed = 0
        for idx, hit in enumerate(hits):
            if hit.get("id") == item_id or hit.get("archived_at"):
                continue
            delta = max(0.08, 0.28 - idx * 0.03)
            await asyncio.to_thread(self.store.bump_heat, str(hit["id"]), delta, False)
            warmed += 1
            if warmed >= limit:
                break

        if warmed:
            logger.info("interest_warmed source_id=%s count=%s", item_id, warmed)
        return warmed

    async def mark_surfaced(self, item_ids: list[str]) -> int:
        return await asyncio.to_thread(self.store.mark_items_surfaced, item_ids)

    async def archive(self, item_ids: list[str]) -> int:
        return await asyncio.to_thread(self.store.archive_items, item_ids)

    async def unarchive(self, item_ids: list[str]) -> int:
        return await asyncio.to_thread(self.store.unarchive_items, item_ids)

    async def _decay_once_per_day(self) -> None:
        today = date.today()
        if self._last_decay_date == today:
            return
        async with self._decay_lock:
            if self._last_decay_date == today:
                return
            changed = await asyncio.to_thread(self.store.apply_heat_decay)
            await asyncio.to_thread(self.store.recompute_decay_states)
            self._last_decay_date = today
            if changed:
                logger.info("interest_decay_applied rows=%s", changed)


def _compact_context(context: str) -> str:
    words = str(context or "").replace("\n", " ").split()
    if len(words) > 140:
        words = words[:140]
    return " ".join(words).strip()
