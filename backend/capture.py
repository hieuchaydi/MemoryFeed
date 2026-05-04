from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from backend.models import CaptureRequest
from backend.native_accel import normalize_text_fast

MAX_TEXT_LEN = 2000

PLATFORM_FROM_HOST = {
    "facebook.com": "facebook",
    "www.facebook.com": "facebook",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "www.youtube.com": "youtube",
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "linkedin.com": "linkedin",
    "www.linkedin.com": "linkedin",
    "instagram.com": "instagram",
    "www.instagram.com": "instagram",
    "tiktok.com": "tiktok",
    "www.tiktok.com": "tiktok",
    "m.tiktok.com": "tiktok",
}


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    return normalize_text_fast(text, MAX_TEXT_LEN)


def detect_platform(url: str, fallback: str = "unknown") -> str:
    host = urlparse(url).netloc.lower()
    for key, value in PLATFORM_FROM_HOST.items():
        if host.endswith(key):
            return value
    return fallback if fallback else "unknown"


def detect_content_type(url: str, image_urls: list[str]) -> str:
    lower_url = url.lower()
    if "youtube.com/watch" in lower_url or "youtu.be/" in lower_url:
        return "video"
    if image_urls:
        return "image"
    if lower_url.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
        return "image"
    if any(token in lower_url for token in ["/article", "/blog", "medium.com"]):
        return "article"
    return "post"


def make_dedupe_key(
    url: str,
    text: str,
    platform: str = "unknown",
    author: str | None = None,
    image_urls: list[str] | None = None,
) -> str:
    first_image = ""
    if image_urls:
        first_image = image_urls[0]
    seed = f"{url}|{platform}|{text[:140]}|{(author or '')[:80]}|{first_image}".encode("utf-8", errors="ignore")
    return hashlib.sha256(seed).hexdigest()


def normalize_capture(payload: CaptureRequest) -> dict:
    text = clean_text(payload.text_content)
    platform = detect_platform(payload.url, fallback=payload.platform)
    image_urls = [u for u in payload.image_urls if isinstance(u, str) and u.startswith(("http://", "https://"))][:6]
    content_type = payload.content_type or detect_content_type(payload.url, image_urls)
    captured_at = payload.captured_at or datetime.now(timezone.utc)

    normalized = {
        "id": str(uuid.uuid4()),
        "url": payload.url.strip(),
        "platform": platform,
        "content_type": content_type,
        "text_content": text,
        "image_urls": image_urls,
        "image_captions": [],
        "author": clean_text(payload.author)[:200] if payload.author else None,
        "captured_at": captured_at.isoformat(),
        "dwell_seconds": round(float(payload.dwell_seconds), 3),
        "embedding_done": 0,
        "vision_done": 0 if image_urls else 1,
        "image_cache_paths": [],
        "dedupe_key": make_dedupe_key(
            payload.url.strip(),
            text,
            platform=platform,
            author=payload.author,
            image_urls=image_urls,
        ),
    }
    return normalized
