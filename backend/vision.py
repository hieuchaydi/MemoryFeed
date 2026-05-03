from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
from pathlib import Path
from typing import Any

import httpx

from backend.indexer import IndexerService
from backend.store import IMAGE_CACHE_DIR, Store

logger = logging.getLogger(__name__)
OLLAMA_URL = "http://localhost:11434/api/generate"
VISION_MODEL = "llava:7b"
VISION_PROMPT = (
    "Describe this image in detail. If it's a meme, describe the text and humor. "
    "If it's a photo, describe what's happening. Be specific. "
    "Answer in the same language as any text in the image."
)


class VisionService:
    def __init__(self, store: Store, indexer: IndexerService) -> None:
        self.store = store
        self.indexer = indexer
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=3000)
        self._task: asyncio.Task[Any] | None = None
        self._running = False
        self._processed = 0
        self._failed = 0

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
        while self._running:
            item_id = await self.queue.get()
            try:
                await self.process_item(item_id)
                self._processed += 1
            except Exception as exc:
                self._failed += 1
                logger.exception("Vision processing failed for %s: %s", item_id, exc)
            finally:
                self.queue.task_done()

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
                caption = await self._caption_image(client, cached)
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

    async def _caption_image(self, client: httpx.AsyncClient, image_path: Path) -> str:
        try:
            img_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        except Exception as exc:
            logger.debug("Cannot read cached image %s: %s", image_path, exc)
            return ""

        payload = {
            "model": VISION_MODEL,
            "prompt": VISION_PROMPT,
            "images": [img_b64],
            "stream": False,
        }
        try:
            resp = await client.post(OLLAMA_URL, json=payload, timeout=120.0)
            resp.raise_for_status()
            body = resp.json()
            return str(body.get("response", "")).strip()
        except Exception as exc:
            logger.debug("Vision model unavailable or failed for %s: %s", image_path, exc)
            return ""

    def status(self) -> dict[str, int | bool]:
        return {
            "running": self._running,
            "queue_size": self.queue.qsize(),
            "processed": self._processed,
            "failed": self._failed,
        }


import contextlib


def _guess_suffix(url: str) -> str:
    lowered = url.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if ext in lowered:
            return ext
    return ".jpg"
