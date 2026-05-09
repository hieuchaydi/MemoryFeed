from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class RetrievalWeights:
    semantic: float = 0.48
    temporal: float = 0.18
    importance: float = 0.16
    context: float = 0.1
    source_reliability: float = 0.08
    duplicate_penalty: float = 0.14
    stale_penalty: float = 0.12


def score_with_trace(
    item: dict,
    semantic_score: float,
    duplicate_penalty: float,
    query: str,
    context_hint: str | None = None,
) -> tuple[float, dict[str, float]]:
    weights = _weights_for_query(query)

    temporal_score = _temporal_score(item)
    importance_score = max(0.0, min(1.0, float(item.get("importance_score") or 0.0)))
    source_reliability = max(0.0, min(1.0, float(item.get("capture_confidence") or 1.0)))
    context_score = _context_score(item, query, context_hint)
    stale_penalty = _stale_penalty(item)

    total = (
        weights.semantic * semantic_score
        + weights.temporal * temporal_score
        + weights.importance * importance_score
        + weights.context * context_score
        + weights.source_reliability * source_reliability
        - weights.duplicate_penalty * duplicate_penalty
        - weights.stale_penalty * stale_penalty
    )
    total = max(0.0, min(1.0, total))

    trace = {
        "semantic": round(weights.semantic * semantic_score, 6),
        "temporal": round(weights.temporal * temporal_score, 6),
        "importance": round(weights.importance * importance_score, 6),
        "context": round(weights.context * context_score, 6),
        "source_reliability": round(weights.source_reliability * source_reliability, 6),
        "duplicate_penalty": round(weights.duplicate_penalty * duplicate_penalty, 6),
        "stale_penalty": round(weights.stale_penalty * stale_penalty, 6),
        "final": round(total, 6),
    }
    return total, trace


def _weights_for_query(query: str) -> RetrievalWeights:
    q = (query or "").lower()
    if any(k in q for k in ["latest", "today", "recent", "new", "now"]):
        return RetrievalWeights(semantic=0.38, temporal=0.28, importance=0.12, context=0.1, source_reliability=0.12)
    if any(k in q for k in ["preference", "always", "usually", "favorite"]):
        return RetrievalWeights(semantic=0.42, temporal=0.1, importance=0.25, context=0.12, source_reliability=0.11)
    return RetrievalWeights()


def _temporal_score(item: dict) -> float:
    now = datetime.now(timezone.utc)
    raw = str(item.get("captured_at") or "")
    try:
        captured = datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return 0.5
    age_days = max(0.0, (now - captured).total_seconds() / 86400.0)
    return max(0.0, min(1.0, 1.0 - (age_days / 365.0)))


def _context_score(item: dict, query: str, context_hint: str | None) -> float:
    q = (query or "").lower()
    c = (context_hint or "").lower()
    text = str(item.get("text_content") or "").lower()
    topics = " ".join(str(v).lower() for v in (item.get("related_topics") or []))
    hay = f"{text} {topics}"
    base = 0.0
    if q and q in hay:
        base += 0.7
    if c and c in hay:
        base += 0.3
    return max(0.0, min(1.0, base))


def _stale_penalty(item: dict) -> float:
    decay = float(item.get("decay_score") or 0.0)
    archived = bool(item.get("archived_at"))
    penalty = decay
    if archived:
        penalty = min(1.0, penalty + 0.25)
    return max(0.0, min(1.0, penalty))
