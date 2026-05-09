from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from memoryfeed.__version__ import __version__

BENCHMARK_DIR = Path(__file__).resolve().parent / "benchmarks"


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
