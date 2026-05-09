from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.benchmarking import BENCHMARK_DIR, build_benchmark_rows


def capture_reliability_rows(capture_metrics: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for platform, stats in sorted(capture_metrics.items(), key=lambda item: item[0]):
        attempts = int(stats.get("attempts", 0) or 0)
        stored = int(stats.get("stored", 0) or 0)
        duplicates = int(stats.get("duplicates", 0) or 0)
        missing = int(stats.get("missing", 0) or 0)
        success_rate = (stored / attempts) if attempts else 0.0
        rows.append(
            {
                "platform": platform,
                "attempts": attempts,
                "stored": stored,
                "duplicates": duplicates,
                "missing_required": missing,
                "success_rate": round(success_rate, 4),
                "fail_rate": round(1 - success_rate, 4) if attempts else 0.0,
                "duplicate_rate": round((duplicates / attempts), 4) if attempts else 0.0,
                "missing_rate": round((missing / attempts), 4) if attempts else 0.0,
            }
        )
    return rows


def benchmark_history(limit: int = 20) -> list[dict[str, Any]]:
    if not BENCHMARK_DIR.exists():
        return []
    files = sorted(BENCHMARK_DIR.glob("benchmark-*.json"), reverse=True)[:limit]
    history: list[dict[str, Any]] = []
    for file_path in files:
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, list):
            history.extend(payload)
    return history


def current_benchmark(capture_metrics: dict[str, dict[str, int]], version: str) -> list[dict[str, Any]]:
    return build_benchmark_rows(capture_metrics, version=version)
