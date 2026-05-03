from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import lancedb
import pyarrow as pa
from sentence_transformers import SentenceTransformer

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

    async def stop(self) -> None:
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task

    async def enqueue(self, item_id: str) -> None:
        try:
            self.queue.put_nowait(item_id)
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

        combined = _build_embedding_text(item)
        if not combined:
            await asyncio.to_thread(self.store.mark_embedding_done, item_id)
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
        await asyncio.to_thread(self.store.mark_embedding_done, item_id)

    async def semantic_search(self, query: str, limit: int = 20) -> list[SemanticHit]:
        if not query.strip():
            return []
        model = await asyncio.to_thread(self._load_model)
        query_vec = await asyncio.to_thread(model.encode, query, normalize_embeddings=True)
        vector = [float(x) for x in query_vec.tolist()]

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

    def status(self) -> dict[str, int | bool]:
        return {
            "running": self._running,
            "queue_size": self.queue.qsize(),
            "processed": self._processed,
            "failed": self._failed,
        }


import contextlib


def _build_embedding_text(item: dict[str, Any]) -> str:
    text = (item.get("text_content") or "").strip()
    captions = " ".join(item.get("image_captions") or []).strip()
    merged = (text + "\n" + captions).strip()
    if not merged:
        return ""
    words = merged.split()
    if len(words) > 512:
        words = words[:512]
    return " ".join(words)
