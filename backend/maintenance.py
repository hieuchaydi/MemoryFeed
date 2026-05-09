from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from backend.indexing import collect_dirty_items
from backend.runtime_config import load_runtime_config
from backend.store import Store

logger = logging.getLogger(__name__)


class MaintenanceScheduler:
    def __init__(self, store: Store) -> None:
        self.store = store
        self._task: asyncio.Task[Any] | None = None
        self._running = False

    async def start(self) -> None:
        cfg = load_runtime_config()
        if not cfg.background_maintenance or self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="memoryfeed-maintenance")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def run_once(self) -> dict[str, int]:
        rebuilt = await asyncio.to_thread(self.store.rebuild_all_fingerprints)
        compacted = await asyncio.to_thread(self.store.compact_indexes)
        cleaned = await asyncio.to_thread(self.store.cleanup_old_logs, 7)
        decayed = await asyncio.to_thread(self.store.recompute_decay_states)
        dirty = await asyncio.to_thread(collect_dirty_items, self.store, 1000)
        return {
            "rebuilt_fingerprints": int(rebuilt),
            "compacted_indexes": int(compacted),
            "logs_cleaned": int(cleaned),
            "recomputed_rankings": int(decayed),
            "dirty_items": len(dirty),
        }

    async def _loop(self) -> None:
        while self._running:
            cfg = load_runtime_config()
            try:
                summary = await self.run_once()
                logger.info(
                    "maintenance_run timestamp=%s rebuilt=%s compacted=%s logs_cleaned=%s recomputed_rankings=%s dirty_items=%s",
                    datetime.now(timezone.utc).isoformat(),
                    summary["rebuilt_fingerprints"],
                    summary["compacted_indexes"],
                    summary["logs_cleaned"],
                    summary["recomputed_rankings"],
                    summary["dirty_items"],
                )
            except Exception:
                logger.exception("maintenance_run_failed")
            await asyncio.sleep(cfg.maintenance_interval_seconds)


import contextlib
