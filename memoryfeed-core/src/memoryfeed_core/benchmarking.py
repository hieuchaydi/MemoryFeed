from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from memoryfeed.__version__ import __version__

BENCHMARK_DIR = Path(__file__).resolve().parent / "benchmarks"
BENCHMARK_SCENARIO_DIR = BENCHMARK_DIR / "scenarios"


def _safe_rate(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def build_benchmark_rows(capture_metrics: dict[str, dict[str, int]], version: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    ver = version or __version__
    for platform, row in sorted(capture_metrics.items(), key=lambda x: x[0]):
        attempts = int(row.get("attempts", 0) or 0)
        stored = int(row.get("stored", 0) or 0)
        duplicates = int(row.get("duplicates", 0) or 0)
        missing = int(row.get("missing", 0) or 0)
        out.append(
            {
                "version": ver,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "platform": platform,
                "attempts": attempts,
                "stored": stored,
                "success_rate": round(_safe_rate(stored, attempts), 4),
                "duplicate_rate": round(_safe_rate(duplicates, attempts), 4),
                "missing_field_rate": round(_safe_rate(missing, attempts), 4),
            }
        )
    return out


def write_benchmark_snapshot(capture_metrics: dict[str, dict[str, int]], version: str | None = None) -> Path:
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    rows = build_benchmark_rows(capture_metrics, version=version)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    target = BENCHMARK_DIR / f"benchmark-{stamp}.json"
    target.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def load_default_benchmark_dataset() -> list[dict[str, Any]]:
    default = [
        {"query": "docker", "must_include_any": ["docker", "container", "compose"], "horizon_days": 30, "type": "long_term_recall"},
        {"query": "latest update", "must_include_any": ["latest", "update", "today"], "horizon_days": 7, "type": "stale_handling"},
        {"query": "preference", "must_include_any": ["prefer", "favorite", "usually"], "horizon_days": 90, "type": "consistency"},
    ]
    path = BENCHMARK_SCENARIO_DIR / "default_memory_eval.json"
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return payload if isinstance(payload, list) else default


def evaluate_memory_retrieval(
    dataset: list[dict[str, Any]],
    retrieved_items: list[dict[str, Any]],
) -> dict[str, Any]:
    total = len(dataset)
    if total <= 0:
        return {
            "total_cases": 0,
            "metrics": {
                "recall_at_k": 0.0,
                "consistency_score": 0.0,
                "hallucination_reduction_proxy": 0.0,
                "stale_memory_handling_score": 0.0,
                "contradiction_handling_score": 0.0,
            },
            "cases": [],
        }

    results: list[dict[str, Any]] = []
    hit = 0
    stale = 0
    consistent = 0
    contrad = 0
    grounded = 0
    for case in dataset:
        tokens = [str(t).lower() for t in (case.get("must_include_any") or [])]
        matched = []
        for row in retrieved_items:
            text = str(row.get("text_content") or row.get("text_excerpt") or "").lower()
            if any(token in text for token in tokens):
                matched.append(str(row.get("id")))
        case_hit = bool(matched)
        if case_hit:
            hit += 1
            grounded += 1
        if str(case.get("type") or "") == "stale_handling":
            stale += 1 if case_hit else 0
        if str(case.get("type") or "") == "consistency":
            consistent += 1 if case_hit else 0
        if str(case.get("type") or "") == "contradiction":
            contrad += 1 if case_hit else 0
        results.append(
            {
                "query": case.get("query"),
                "type": case.get("type"),
                "matched_ids": matched[:10],
                "pass": case_hit,
            }
        )

    recall = round(hit / total, 6)
    return {
        "total_cases": total,
        "metrics": {
            "recall_at_k": recall,
            "consistency_score": round(consistent / max(1, sum(1 for c in dataset if c.get("type") == "consistency")), 6),
            "hallucination_reduction_proxy": round(grounded / total, 6),
            "stale_memory_handling_score": round(stale / max(1, sum(1 for c in dataset if c.get("type") == "stale_handling")), 6),
            "contradiction_handling_score": round(contrad / max(1, sum(1 for c in dataset if c.get("type") == "contradiction")), 6),
        },
        "cases": results,
    }
