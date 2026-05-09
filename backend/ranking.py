from __future__ import annotations

from datetime import datetime, timezone


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def score_result(
    item: dict,
    base_score: float,
    duplicate_penalty: float = 0.0,
) -> tuple[float, dict[str, float]]:
    now = datetime.now(timezone.utc)
    captured = _parse_iso(str(item.get("captured_at") or "")) or now
    age_days = max(0.0, (now - captured).total_seconds() / 86400.0)
    recency = max(0.0, 1.0 - min(1.0, age_days / 365.0))
    semantic = max(0.0, min(1.0, float(base_score)))
    heat = float(item.get("heat") or 1.0)
    heat_boost = min(0.35, heat * 0.05)
    noise_penalty = min(0.4, float(item.get("noise_score") or 0.0) * 0.5)
    confidence = float(item.get("capture_confidence") or 1.0)
    confidence_penalty = 0.0 if confidence >= 0.55 else (0.55 - confidence) * 0.6
    final_score = semantic + recency * 0.25 + heat_boost - duplicate_penalty - noise_penalty - confidence_penalty
    factors = {
        "semantic_match_score": round(semantic, 6),
        "recency_contribution": round(recency * 0.25, 6),
        "duplicate_penalty": round(duplicate_penalty, 6),
        "confidence_penalty": round(confidence_penalty, 6),
        "noise_penalty": round(noise_penalty, 6),
        "heat_boost": round(heat_boost, 6),
    }
    return round(final_score, 8), factors
