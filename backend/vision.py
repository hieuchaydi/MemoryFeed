from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from pathlib import Path
from typing import Any

import httpx

from backend.indexer import IndexerService
from backend.llm_clients import caption_image_with_gemini, rewrite_or_summarize_with_groq
from backend.resilience import backoff_seconds
from backend.runtime_config import load_runtime_config
from backend.store import IMAGE_CACHE_DIR, Store

logger = logging.getLogger(__name__)
VISION_PROMPT = (
    "Hãy mô tả chi tiết ảnh này. Nếu là meme, nêu rõ chữ trong ảnh và ý gây cười. "
    "Nếu là ảnh chụp, mô tả bối cảnh và hành động chính thật cụ thể. "
    "Giữ nguyên ngôn ngữ đang xuất hiện trong ảnh; nếu không có chữ thì trả lời bằng tiếng Việt."
)
ENABLE_GROQ_CAPTION_REWRITE = os.getenv("MEMORYFEED_GROQ_REWRITE_CAPTIONS", "1") not in {"0", "false", "False"}


class VisionService:
    def __init__(self, store: Store, indexer: IndexerService) -> None:
        self.store = store
        self.indexer = indexer
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=3000)
        self._task: asyncio.Task[Any] | None = None
        self._running = False
        self._processed = 0
        self._failed = 0
        self._retried = 0
        self._dead_letter = 0
        self._attempts: dict[str, int] = {}

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._worker(), name="memoryfeed-vision")
        logger.info("vision_started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("vision_stopped processed=%s failed=%s", self._processed, self._failed)

    async def enqueue(self, item_id: str) -> None:
        try:
            self.queue.put_nowait(item_id)
            logger.debug("vision_enqueue item_id=%s queue_size=%s", item_id, self.queue.qsize())
        except asyncio.QueueFull:
            logger.warning("Vision queue full. Dropping item_id=%s", item_id)

    async def _worker(self) -> None:
        cfg = load_runtime_config()
        while self._running:
            item_id = await self.queue.get()
            try:
                await self.process_item(item_id)
                self._processed += 1
                self._attempts.pop(item_id, None)
            except Exception as exc:
                self._failed += 1
                attempt = int(self._attempts.get(item_id, 0)) + 1
                self._attempts[item_id] = attempt
                if attempt < cfg.queue_retry_max_attempts:
                    self._retried += 1
                    delay = backoff_seconds(
                        attempt=attempt,
                        base=cfg.queue_retry_base_delay_seconds,
                        cap=cfg.queue_retry_max_delay_seconds,
                    )
                    logger.warning("vision_retry item_id=%s attempt=%s delay_s=%.3f error=%s", item_id, attempt, delay, exc)
                    asyncio.create_task(self._requeue_after(item_id, delay))
                else:
                    self._dead_letter += 1
                    self._attempts.pop(item_id, None)
                    logger.exception("vision_dead_letter item_id=%s attempts=%s error=%s", item_id, attempt, exc)
            finally:
                self.queue.task_done()

    async def _requeue_after(self, item_id: str, delay_seconds: float) -> None:
        await asyncio.sleep(max(0.0, delay_seconds))
        await self.enqueue(item_id)

    async def process_item(self, item_id: str) -> None:
        item = await asyncio.to_thread(self.store.get_item, item_id)
        if not item:
            return

        image_urls = item.get("image_urls") or []
        if not image_urls:
            await asyncio.to_thread(self.store.update_vision_result, item_id, [], [])
            await self.indexer.enqueue(item_id)
            return

        captions: list[str] = []
        cache_paths: list[str] = []

        async with httpx.AsyncClient(timeout=10.0) as client:
            for image_url in image_urls:
                cached = await self._cache_image(client, image_url)
                if not cached:
                    continue
                cache_paths.append(str(cached))
                caption = await self._caption_image(cached)
                if caption:
                    captions.append(caption)

        await asyncio.to_thread(self.store.update_vision_result, item_id, captions, cache_paths)
        await self.indexer.enqueue(item_id)

    async def _cache_image(self, client: httpx.AsyncClient, image_url: str) -> Path | None:
        digest = hashlib.sha256(image_url.encode("utf-8", errors="ignore")).hexdigest()[:24]
        suffix = _guess_suffix(image_url)
        target = IMAGE_CACHE_DIR / f"{digest}{suffix}"
        if target.exists() and target.stat().st_size > 0:
            return target

        try:
            resp = await client.get(image_url, follow_redirects=True)
            resp.raise_for_status()
            target.write_bytes(resp.content)
            return target
        except Exception as exc:
            logger.debug("Failed to download image %s: %s", image_url, exc)
            return None

    async def _caption_image(self, image_path: Path) -> str:
        try:
            image_bytes = image_path.read_bytes()
        except Exception as exc:
            logger.debug("Cannot read cached image %s: %s", image_path, exc)
            return ""

        caption = await asyncio.to_thread(caption_image_with_gemini, image_bytes, VISION_PROMPT)
        if not caption:
            logger.debug("Gemini caption unavailable for %s", image_path)
            return ""

        if ENABLE_GROQ_CAPTION_REWRITE:
            rewritten = await asyncio.to_thread(rewrite_or_summarize_with_groq, caption)
            if rewritten:
                caption = rewritten

        return caption

    def status(self) -> dict[str, int | bool]:
        return {
            "running": self._running,
            "queue_size": self.queue.qsize(),
            "processed": self._processed,
            "failed": self._failed,
            "retried": self._retried,
            "dead_letter": self._dead_letter,
        }


import contextlib


def _guess_suffix(url: str) -> str:
    lowered = url.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if ext in lowered:
            return ext
    return ".jpg"
