from __future__ import annotations

import asyncio
import logging
import time
import threading
from dataclasses import dataclass
from typing import Any

import lancedb
import pyarrow as pa
from sentence_transformers import SentenceTransformer

from backend.embeddings import build_semantic_text
from backend.logging import log_event
from backend.redaction import scan_sensitive_content
from backend.runtime_config import load_runtime_config
from backend.store import LANCEDB_DIR, Store

logger = logging.getLogger(__name__)
EMBED_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


@dataclass
class SemanticHit:
    id: str
    score: float


class IndexerService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=5000)
        self._worker_task: asyncio.Task[Any] | None = None
        self._running = False
        self._model: SentenceTransformer | None = None
        self._processed = 0
        self._failed = 0
        self._table_non_empty: bool | None = None
        self._table_check_at = 0.0
        self._query_vec_cache: dict[str, tuple[float, list[float]]] = {}
        self._query_cache_ttl_s = 30.0
        self._query_cache_max_size = 512
        self._query_cache_lock = threading.Lock()
        self._query_cache_hits = 0
        self._query_cache_misses = 0
        self._query_cache_evictions = 0

        self.db = lancedb.connect(str(LANCEDB_DIR))
        self.table = self._ensure_table()

    def _ensure_table(self):
        try:
            return self.db.open_table("items")
        except Exception:
            schema = pa.schema(
                [
                    pa.field("id", pa.string()),
                    pa.field("embedding", pa.list_(pa.float32(), 384)),
                    pa.field("captured_at", pa.string()),
                    pa.field("platform", pa.string()),
                ]
            )
            return self.db.create_table("items", data=[], schema=schema)

    def _load_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(EMBED_MODEL_NAME)
        return self._model

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker(), name="memoryfeed-indexer")
        logger.info("indexer_started")

    async def stop(self) -> None:
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task
        logger.info("indexer_stopped processed=%s failed=%s", self._processed, self._failed)

    async def enqueue(self, item_id: str) -> None:
        try:
            self.queue.put_nowait(item_id)
            logger.debug("indexer_enqueue item_id=%s queue_size=%s", item_id, self.queue.qsize())
        except asyncio.QueueFull:
            logger.warning("Indexer queue full. Dropping item_id=%s", item_id)

    async def _worker(self) -> None:
        while self._running:
            item_id = await self.queue.get()
            try:
                await self.index_item(item_id)
                self._processed += 1
            except Exception as exc:
                self._failed += 1
                logger.exception("Failed to index item %s: %s", item_id, exc)
            finally:
                self.queue.task_done()

    async def index_item(self, item_id: str) -> None:
        item = await asyncio.to_thread(self.store.get_item, item_id)
        if not item:
            return

        combined = build_semantic_text(item)
        if not combined:
            await asyncio.to_thread(self.store.mark_embedding_done, item_id)
            return

        cfg = load_runtime_config()
        sensitive_scan = scan_sensitive_content(combined)
        if cfg.memory_skip_sensitive_embedding and sensitive_scan["sensitive"]:
            reason = "sensitive:" + ",".join(sensitive_scan["reasons"])
            await asyncio.to_thread(self.store.mark_embedding_skipped, item_id, reason)
            log_event(
                logger,
                "embedding_skipped",
                platform=item.get("platform", "unknown"),
                item_id=item_id,
                embedding_skipped_reason=reason,
                suspicious_prompt_content=bool(item.get("suspicious_prompt_content", False)),
            )
            return

        model = await asyncio.to_thread(self._load_model)
        embedding = await asyncio.to_thread(model.encode, combined, normalize_embeddings=True)
        vector = [float(x) for x in embedding.tolist()]

        row = {
            "id": item_id,
            "embedding": vector,
            "captured_at": item["captured_at"],
            "platform": item["platform"],
        }

        await asyncio.to_thread(self.table.delete, f"id = '{item_id}'")
        await asyncio.to_thread(self.table.add, [row])
        self._table_non_empty = True
        self._table_check_at = time.monotonic()
        await asyncio.to_thread(self.store.mark_embedding_done, item_id)
        log_event(
            logger,
            "embedding_indexed",
            platform=item.get("platform", "unknown"),
            item_id=item_id,
            suspicious_prompt_content=bool(item.get("suspicious_prompt_content", False)),
        )

    async def semantic_search(self, query: str, limit: int = 20) -> list[SemanticHit]:
        if not query.strip():
            return []
        if not await self._has_vectors():
            return []
        vector = await self._get_query_vector(query)

        try:
            results = await asyncio.to_thread(lambda: self.table.search(vector).limit(limit).to_list())
        except Exception as exc:
            logger.warning("Semantic search unavailable: %s", exc)
            return []

        hits: list[SemanticHit] = []
        for idx, row in enumerate(results, start=1):
            row_id = row.get("id")
            if not row_id:
                continue
            score = float(row.get("_distance", idx))
            hits.append(SemanticHit(id=str(row_id), score=score))
        return hits

    async def _has_vectors(self) -> bool:
        now = time.monotonic()
        if self._table_non_empty is not None and (now - self._table_check_at) < 10:
            return self._table_non_empty
        try:
            row_count = await asyncio.to_thread(self.table.count_rows)
            self._table_non_empty = bool(row_count)
            self._table_check_at = now
            return self._table_non_empty
        except Exception:
            # If metadata lookup fails, keep semantic search available.
            return True

    def status(self) -> dict[str, int | bool]:
        return {
            "running": self._running,
            "queue_size": self.queue.qsize(),
            "processed": self._processed,
            "failed": self._failed,
            "query_cache_hits": self._query_cache_hits,
            "query_cache_misses": self._query_cache_misses,
            "query_cache_evictions": self._query_cache_evictions,
            "query_cache_size": len(self._query_vec_cache),
        }

    async def _get_query_vector(self, query: str) -> list[float]:
        normalized = " ".join(query.lower().split())
        now = time.monotonic()
        with self._query_cache_lock:
            hit = self._query_vec_cache.get(normalized)
            if hit and (now - hit[0]) <= self._query_cache_ttl_s:
                self._query_cache_hits += 1
                return list(hit[1])
            self._query_cache_misses += 1
            if hit:
                self._query_vec_cache.pop(normalized, None)

        model = await asyncio.to_thread(self._load_model)
        query_vec = await asyncio.to_thread(model.encode, query, normalize_embeddings=True)
        vector = [float(x) for x in query_vec.tolist()]

        with self._query_cache_lock:
            if len(self._query_vec_cache) >= self._query_cache_max_size:
                oldest_key = min(self._query_vec_cache, key=lambda k: self._query_vec_cache[k][0])
                self._query_vec_cache.pop(oldest_key, None)
                self._query_cache_evictions += 1
            self._query_vec_cache[normalized] = (time.monotonic(), vector)

        return vector


import contextlib
