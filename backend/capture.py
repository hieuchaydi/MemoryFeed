from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from backend.memory_graph import infer_url_domain
from backend.models import CaptureRequest
from backend.native_accel import normalize_text_fast
from backend.safety import detect_prompt_injection

MAX_TEXT_LEN = 2000
TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "gclid",
    "fbclid",
    "igshid",
    "si",
}

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


def canonicalize_url(url: str, platform: str = "unknown") -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
    except Exception:
        return raw

    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    query = parse_qs(parsed.query, keep_blank_values=False)
    query = {k: v for k, v in query.items() if k.lower() not in TRACKING_QUERY_KEYS}
    path = parsed.path.rstrip("/") or "/"

    if platform == "twitter":
        match = re.search(r"/([^/]+)/status/(\d+)", path)
        if match:
            path = f"/{match.group(1)}/status/{match.group(2)}"
        query = {}
    elif platform == "youtube":
        if "youtu.be" in netloc:
            video_id = path.strip("/")
            if video_id:
                netloc = "youtube.com"
                path = "/watch"
                query = {"v": [video_id]}
        elif path == "/watch":
            if "v" in query:
                query = {"v": query["v"][:1]}
            else:
                query = {}
        elif path.startswith("/shorts/"):
            short_id = path.split("/shorts/", 1)[-1].split("/", 1)[0]
            path = f"/shorts/{short_id}" if short_id else "/shorts"
            query = {}
    elif platform == "linkedin":
        match = re.search(r"/feed/update/([^/?#]+)", path)
        if match:
            path = f"/feed/update/{match.group(1)}"
        query = {}
    elif platform == "facebook":
        if "/permalink/" in path or "/posts/" in path:
            query = {}
        else:
            allowed = {}
            if "story_fbid" in query:
                allowed["story_fbid"] = query["story_fbid"][:1]
            if "id" in query:
                allowed["id"] = query["id"][:1]
            query = allowed
    elif platform == "tiktok":
        match = re.search(r"/@([^/]+)/video/(\d+)", path)
        if match:
            path = f"/@{match.group(1)}/video/{match.group(2)}"
        query = {}

    clean_query = urlencode([(k, val) for k, values in sorted(query.items()) for val in values], doseq=True)
    return urlunparse((parsed.scheme or "https", netloc, path, "", clean_query, ""))


def extract_post_id(url: str, platform: str = "unknown") -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    path = parsed.path or ""
    query = parse_qs(parsed.query, keep_blank_values=False)

    if platform == "twitter":
        match = re.search(r"/status/(\d+)", path)
        return match.group(1) if match else None
    if platform == "youtube":
        if path == "/watch":
            values = query.get("v")
            return values[0] if values else None
        if path.startswith("/shorts/"):
            short_id = path.split("/shorts/", 1)[-1].split("/", 1)[0]
            return short_id or None
    if platform == "linkedin":
        match = re.search(r"/feed/update/([^/?#]+)", path)
        return match.group(1) if match else None
    if platform == "facebook":
        match = re.search(r"/posts/([^/?#]+)", path)
        if match:
            return match.group(1)
        match = re.search(r"/permalink/([^/?#]+)", path)
        if match:
            return match.group(1)
        story = query.get("story_fbid")
        return story[0] if story else None
    if platform == "tiktok":
        match = re.search(r"/video/(\d+)", path)
        return match.group(1) if match else None
    return None


def _time_bucket(captured_at_iso: str, minutes: int = 120) -> str:
    try:
        dt = datetime.fromisoformat(captured_at_iso.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        dt = datetime.now(timezone.utc)
    bucket = int(dt.timestamp() // max(60, minutes * 60))
    return str(bucket)


def make_dedupe_key(
    canonical_url: str,
    text: str,
    platform: str = "unknown",
    author_name: str | None = None,
    captured_at_iso: str | None = None,
) -> str:
    bucket = _time_bucket(captured_at_iso or datetime.now(timezone.utc).isoformat())
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
        "capture_debug": payload.capture_debug or {},
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
