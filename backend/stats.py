from __future__ import annotations

from typing import Any


def build_reliability_dashboard(
    items: list[dict[str, Any]],
    capture_reliability: list[dict[str, Any]] | None = None,
    replay_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    total = max(1, len(items))
    duplicate_rate = sum(1 for i in items if i.get("duplicate_of")) / total
    confidence_values = [float(i.get("capture_confidence") or 1.0) for i in items]
    confidence_avg = (sum(confidence_values) / len(confidence_values)) if confidence_values else 0.0
    fallback_usage = sum(1 for i in items if (i.get("capture_debug") or {}).get("fallback_selector_used")) / total
    missing_trend = sum(1 for i in items if any(str(f).startswith("missing_") for f in (i.get("quality_flags") or []))) / total
    return {
        "per_platform_success_rate": capture_reliability or [],
        "duplicate_rate": round(duplicate_rate, 6),
        "capture_confidence_avg": round(confidence_avg, 6),
        "selector_fallback_usage": round(fallback_usage, 6),
        "missing_field_trend": round(missing_trend, 6),
        "replay_benchmark_history": replay_history or [],
    }
