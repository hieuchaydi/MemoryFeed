from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from backend.capture_quality import compute_capture_confidence
from backend.dedupe import dedupe_bucket
from backend.memory_graph import infer_url_domain
from backend.models import CaptureRequest
from backend.native_accel import normalize_text_fast
from backend.safety import detect_prompt_injection
from backend.url_normalization import canonicalize_url, extract_post_id

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
    if "youtube.com/watch" in lower_url or "youtu.be/" in lower_url or "tiktok.com" in lower_url:
        return "video"
    if image_urls:
        return "image"
    if lower_url.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
        return "image"
    if any(token in lower_url for token in ["/article", "/blog", "medium.com"]):
        return "article"
    return "post"


def make_dedupe_key(
    canonical_url: str,
    text: str,
    platform: str = "unknown",
    author_name: str | None = None,
    captured_at_iso: str | None = None,
) -> str:
    bucket = dedupe_bucket(captured_at_iso or datetime.now(timezone.utc).isoformat(), platform=platform)
    seed = f"{canonical_url}|{platform}|{text[:240]}|{(author_name or '')[:100]}|{bucket}".encode(
        "utf-8",
        errors="ignore",
    )
    return hashlib.sha256(seed).hexdigest()


def normalize_capture(payload: CaptureRequest) -> dict:
    text = clean_text(payload.text_content)
    platform = detect_platform(payload.url, fallback=payload.platform)
    base_url = payload.canonical_url or payload.url
    canonical_url = canonicalize_url(base_url, platform=platform)

    media_urls = payload.media_urls if payload.media_urls else payload.image_urls
    media_urls = [u for u in media_urls if isinstance(u, str) and u.startswith(("http://", "https://"))][:6]
    image_urls = [u for u in payload.image_urls if isinstance(u, str) and u.startswith(("http://", "https://"))][:6]
    if not image_urls and media_urls:
        image_urls = media_urls

    author_name = clean_text(payload.author_name or payload.author)[:200] if (payload.author_name or payload.author) else None
    content_type = payload.content_type or detect_content_type(payload.url, image_urls)
    captured_at = payload.captured_at or datetime.now(timezone.utc)
    captured_at_iso = captured_at.isoformat()
    post_id = payload.post_id or extract_post_id(canonical_url, platform=platform)

    quality_flags = list(payload.quality_flags or [])
    required_checks = {
        "platform": platform,
        "canonical_url": canonical_url,
        "author_name": author_name,
        "text": text,
        "media_urls": media_urls,
        "post_id": post_id,
        "captured_at": captured_at_iso,
    }
    missing_fields = [key for key, value in required_checks.items() if not value]
    for field in missing_fields:
        flag = f"missing_{field}"
        if flag not in quality_flags:
            quality_flags.append(flag)

    safety = detect_prompt_injection(text)
    capture_debug = dict(payload.capture_debug or {})
    if "missing_fields" not in capture_debug:
        capture_debug["missing_fields"] = missing_fields

    confidence_score, computed_reasons = compute_capture_confidence(
        {
            "url": payload.url.strip(),
            "canonical_url": canonical_url or payload.url.strip(),
            "platform": platform,
            "post_id": post_id,
            "text_content": text,
            "media_urls": media_urls,
            "image_urls": image_urls,
            "author": author_name,
            "author_name": author_name,
            "quality_flags": quality_flags,
            "capture_debug": capture_debug,
        }
    )
    capture_confidence = (
        round(float(payload.capture_confidence), 4)
        if payload.capture_confidence is not None
        else confidence_score
    )
    confidence_reasons = sorted(dict.fromkeys([*computed_reasons, *(payload.confidence_reasons or [])]))

    normalized = {
        "id": str(uuid.uuid4()),
        "url": payload.url.strip(),
        "canonical_url": canonical_url or payload.url.strip(),
        "post_id": post_id,
        "platform": platform,
        "content_type": content_type,
        "text_content": text,
        "media_urls": media_urls,
        "image_urls": image_urls,
        "image_captions": [],
        "author": author_name,
        "author_name": author_name,
        "author_handle": clean_text(payload.author_handle)[:120] if payload.author_handle else None,
        "thumbnail_url": payload.thumbnail_url,
        "source_context": payload.source_context,
        "quality_flags": quality_flags,
        "capture_debug": capture_debug,
        "capture_confidence": capture_confidence,
        "confidence_reasons": confidence_reasons,
        "capture_method": (payload.capture_method or "mutation_observer")[:80],
        "extractor_version": (payload.extractor_version or f"{platform}_v3_1")[:80],
        "capture_source": (payload.capture_source or "timeline_scroll")[:120],
        "replay_source": (payload.replay_source or None),
        "url_domain": infer_url_domain(canonical_url or payload.url.strip()),
        "suspicious_prompt_content": bool(safety["suspicious"]),
        "safety_signals": list(safety["signals"]),
        "captured_at": captured_at_iso,
        "dwell_seconds": round(float(payload.dwell_seconds), 3),
        "embedding_done": 0,
        "vision_done": 0 if image_urls else 1,
        "image_cache_paths": [],
        "dedupe_key": make_dedupe_key(
            canonical_url or payload.url.strip(),
            text,
            platform=platform,
            author_name=author_name,
            captured_at_iso=captured_at_iso,
        ),
    }
    return normalized
