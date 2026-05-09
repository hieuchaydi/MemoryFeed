from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class ScoreBundle:
    importance_score: float
    resurfacing_score: float
    recency_score: float
    recurrence_score: float
    explain: dict[str, Any]


def _parse_iso(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def _clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _recency_score(captured_at: str | None) -> float:
    age_days = max(0.0, (datetime.now(timezone.utc) - _parse_iso(captured_at)).total_seconds() / 86400.0)
    return _clamp01(1.0 / (1.0 + age_days / 10.0))


def _safe_count(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except Exception:
        return 0


def _query_recurrence_signals(conn, item: dict[str, Any]) -> dict[str, int]:
    canonical_url = str(item.get("canonical_url") or item.get("url") or "")
    author = str(item.get("author_name") or item.get("author") or "")
    platform = str(item.get("platform") or "")

    same_url = 0
    same_author = 0
    cross_platform = 0

    if canonical_url:
        same_url = int(
            conn.execute(
                "SELECT COUNT(*) FROM items WHERE canonical_url = ?",
                (canonical_url,),
            ).fetchone()[0]
        )
        cross_platform = int(
            conn.execute(
                "SELECT COUNT(DISTINCT platform) FROM items WHERE canonical_url = ?",
                (canonical_url,),
            ).fetchone()[0]
        )

    if author:
        same_author = int(
            conn.execute(
                "SELECT COUNT(*) FROM items WHERE COALESCE(author_name, author) = ?",
                (author,),
            ).fetchone()[0]
        )

    same_platform = int(
        conn.execute(
            "SELECT COUNT(*) FROM items WHERE platform = ?",
            (platform,),
        ).fetchone()[0]
    )
    return {
        "same_url": same_url,
        "same_author": same_author,
        "cross_platform": cross_platform,
        "same_platform": same_platform,
    }


def compute_scores(conn, item: dict[str, Any]) -> ScoreBundle:
    recency = _recency_score(item.get("captured_at"))
    recurrence_signals = _query_recurrence_signals(conn, item)
    surfaced_count = _safe_count(item.get("surfaced_count"))
    starred = 1.0 if item.get("starred") else 0.0
    dwell = float(item.get("dwell_seconds") or 0.0)
    capture_confidence = float(item.get("capture_confidence", 1.0) or 0.0)
    quality_flags = [str(flag) for flag in (item.get("quality_flags") or [])]

    recurrence_raw = (
        min(1.0, recurrence_signals["same_url"] / 5.0) * 0.45
        + min(1.0, recurrence_signals["same_author"] / 10.0) * 0.3
        + min(1.0, recurrence_signals["cross_platform"] / 3.0) * 0.25
    )
    recurrence = _clamp01(recurrence_raw)

    interaction = _clamp01(min(1.0, surfaced_count / 6.0) * 0.6 + starred * 0.4)
    dwell_component = _clamp01(dwell / 120.0)

    missing_penalty = min(0.2, 0.05 * sum(1 for flag in quality_flags if flag.startswith("missing_")))
    confidence_penalty = max(0.0, 0.7 - capture_confidence) * 0.3
    duplicate_penalty = 0.1 if "duplicate_risk" in quality_flags else 0.0
    quality_penalty = missing_penalty + confidence_penalty + duplicate_penalty

    importance = _clamp01(recurrence * 0.45 + interaction * 0.35 + recency * 0.1 + dwell_component * 0.1 - quality_penalty)

    age_days = max(0.0, (datetime.now(timezone.utc) - _parse_iso(item.get("captured_at"))).total_seconds() / 86400.0)
    stale_bonus = 0.25 if age_days >= 10 else 0.0
    resurfacing = _clamp01(
        (importance * 0.5) + stale_bonus + (1.0 - recency) * 0.3 - min(0.25, surfaced_count * 0.03) - quality_penalty * 0.5
    )

    explain = {
        "recurrence_signals": recurrence_signals,
        "interaction": {
            "starred": bool(item.get("starred")),
            "surfaced_count": surfaced_count,
            "dwell_seconds": round(dwell, 3),
        },
        "quality": {
            "capture_confidence": round(capture_confidence, 4),
            "quality_flags": quality_flags,
            "quality_penalty": round(quality_penalty, 4),
        },
        "age_days": round(age_days, 3),
    }
    return ScoreBundle(
        importance_score=round(importance, 6),
        resurfacing_score=round(resurfacing, 6),
        recency_score=round(recency, 6),
        recurrence_score=round(recurrence, 6),
        explain=explain,
    )


def update_item_scores(conn, item_id: str, item: dict[str, Any]) -> ScoreBundle:
    scores = compute_scores(conn, item)
    conn.execute(
        """
        UPDATE items
        SET importance_score = ?,
            resurfacing_score = ?,
            recency_score = ?,
            recurrence_score = ?,
            ranking_debug = ?
        WHERE id = ?
        """,
        (
            float(scores.importance_score),
            float(scores.resurfacing_score),
            float(scores.recency_score),
            float(scores.recurrence_score),
            json.dumps(scores.explain, ensure_ascii=False),
            item_id,
        ),
    )
    return scores
