from __future__ import annotations

import math
from datetime import datetime, timezone


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def compute_decay(
    item: dict,
    half_life_days: int = 90,
    now: datetime | None = None,
) -> tuple[float, str]:
    now_dt = now or datetime.now(timezone.utc)
    captured = _parse_iso(str(item.get("captured_at") or "")) or now_dt
    age_days = max(0.0, (now_dt - captured).total_seconds() / 86400.0)

    surfaced_count = int(item.get("surfaced_count") or 0)
    starred = bool(item.get("starred"))
    important = float(item.get("heat") or 1.0) >= 2.5 or starred
    memory_type = str(item.get("memory_type") or _infer_memory_type(item)).lower()

    adjustment = 1.0 + min(1.5, surfaced_count * 0.06)
    if important:
        adjustment += 0.7
    adjustment *= _type_half_life_multiplier(memory_type)
    adjusted_half_life = max(7.0, float(half_life_days) * adjustment)

    decay_score = 1.0 - math.exp(-math.log(2.0) * (age_days / adjusted_half_life))
    decay_score = max(0.0, min(1.0, decay_score))

    if item.get("archived_at"):
        state = "archived"
    elif decay_score >= 0.85:
        state = "stale"
    elif decay_score >= 0.45:
        state = "cooling"
    else:
        state = "active"
    return float(round(decay_score, 6)), state


def _type_half_life_multiplier(memory_type: str) -> float:
    if memory_type == "fact":
        return 1.8
    if memory_type == "preference":
        return 1.4
    if memory_type == "task":
        return 1.1
    if memory_type == "intent":
        return 1.0
    if memory_type == "episode":
        return 0.85
    return 0.75


def _infer_memory_type(item: dict) -> str:
    tags = [str(v).lower() for v in (item.get("tags") or [])]
    text = str(item.get("text_content") or "").lower()
    content_type = str(item.get("content_type") or "").lower()
    if "fact" in tags:
        return "fact"
    if "preference" in tags:
        return "preference"
    if "task" in tags or "todo" in text:
        return "task"
    if "intent" in tags:
        return "intent"
    if content_type in {"video", "image"}:
        return "episode"
    return "ephemeral"
