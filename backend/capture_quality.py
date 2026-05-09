from __future__ import annotations

from urllib.parse import urlparse
from typing import Any


def _clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _extract_fallback_fields(capture_debug: dict[str, Any] | None) -> list[str]:
    selector_used = {}
    if isinstance(capture_debug, dict):
        selector_used = capture_debug.get("selector_used") or {}
    if not isinstance(selector_used, dict):
        return []
    out: list[str] = []
    for key, value in selector_used.items():
        if isinstance(value, str) and value.strip().lower().startswith("fallback"):
            out.append(str(key))
    return out


def compute_capture_confidence(item: dict[str, Any]) -> tuple[float, list[str]]:
    score = 1.0
    reasons: list[str] = []

    text = str(item.get("text_content") or "").strip()
    canonical_url = str(item.get("canonical_url") or item.get("url") or "").strip()
    author_name = str(item.get("author_name") or item.get("author") or "").strip()
    media_urls = item.get("media_urls") or item.get("image_urls") or []
    post_id = str(item.get("post_id") or "").strip()
    quality_flags = [str(flag) for flag in (item.get("quality_flags") or [])]

    if not text:
        score -= 0.22
        reasons.append("missing_text")
    if not canonical_url:
        score -= 0.18
        reasons.append("missing_canonical_url")
    if not author_name:
        score -= 0.14
        reasons.append("missing_author")
    if not isinstance(media_urls, list) or len(media_urls) == 0:
        score -= 0.08
        reasons.append("missing_media")
    if not post_id:
        score -= 0.08
        reasons.append("missing_post_id")

    fallback_fields = _extract_fallback_fields(item.get("capture_debug"))
    if fallback_fields:
        # Fallback selectors are useful for resilience, but reduce confidence mildly.
        score -= min(0.18, 0.06 * len(fallback_fields))
        reasons.extend([f"fallback_selector_used:{name}" for name in sorted(set(fallback_fields))])

    try:
        parsed = urlparse(canonical_url)
        if not parsed.scheme or not parsed.netloc:
            score -= 0.12
            reasons.append("weak_canonical_url")
    except Exception:
        score -= 0.12
        reasons.append("weak_canonical_url")

    if any(flag.startswith("missing_") for flag in quality_flags):
        score -= 0.05
        reasons.append("missing_required_fields")
    if "duplicate_risk" in quality_flags:
        score -= 0.1
        reasons.append("duplicate_risk")

    out_score = round(_clamp01(score), 4)
    out_reasons = sorted(dict.fromkeys(reasons))
    return out_score, out_reasons
