from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def mode_bonus(item: dict[str, Any], mode: str) -> float:
    content_type = str(item.get("content_type") or "")
    text = str(item.get("text_content") or "").lower()
    if mode == "focus":
        technical_tokens = ("api", "docker", "kubernetes", "database", "architecture", "python", "typescript")
        return 0.2 if content_type in {"article", "post"} and any(t in text for t in technical_tokens) else 0.05
    if mode == "light":
        return 0.18 if content_type in {"video", "image"} else 0.0
    if mode == "explore":
        surfaced_count = int(item.get("surfaced_count") or 0)
        return max(0.0, 0.16 - math.log1p(surfaced_count) * 0.04)
    return 0.0


def score_item(item: dict[str, Any], mode: str = "default") -> tuple[float, str, bool]:
    now = datetime.now(timezone.utc)
    captured_at = _parse_iso(item.get("captured_at")) or now
    last_surfaced = _parse_iso(item.get("last_surfaced"))
    age_days = max(0.0, (now - captured_at).total_seconds() / 86400.0)
    untouched_days = max(0.0, (now - (last_surfaced or captured_at)).total_seconds() / 86400.0)

    heat = max(0.05, float(item.get("heat") or 1.0))
    importance = float(item.get("importance_score") or 0.0)
    resurfacing = float(item.get("resurfacing_score") or 0.0)
    recency = float(item.get("recency_score") or (1.0 / (1.0 + age_days / 14.0)))
    dwell_bonus = min(0.25, float(item.get("dwell_seconds") or 0.0) / 120.0)
    star_bonus = 0.45 if item.get("starred") else 0.0
    stale_gap = 0.18 if age_days >= 3 and untouched_days >= 14 else 0.0

    score = (
        heat * 0.45
        + importance * 0.35
        + resurfacing * 0.25
        + recency * 0.15
        + dwell_bonus
        + star_bonus
        + stale_gap
        + mode_bonus(item, mode)
    )

    reason = "important_memory"
    if item.get("starred"):
        reason = "starred_memory"
    elif stale_gap:
        reason = "worth_resurfacing"
    elif recency >= 0.85:
        reason = "recent_capture"

    needs_review = age_days >= 30 and untouched_days >= 30 and importance < 0.35
    return score, reason, needs_review
