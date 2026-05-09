from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.indexer import IndexerService
from backend.searcher import Searcher
from backend.store import Store


RUNS_DIR = Path(__file__).resolve().parent / "benchmarks" / "runs"
SCENARIO_PATH = Path(__file__).resolve().parent / "benchmarks" / "scenarios" / "default_memory_eval.json"
FAILURE_PATH = Path(__file__).resolve().parent / "benchmarks" / "scenarios" / "failure_cases.json"


@dataclass(frozen=True)
class Scenario:
    query: str
    must_include_any: list[str]
    type: str


def load_scenarios(path: Path | None = None) -> list[Scenario]:
    target = path or SCENARIO_PATH
    if not target.exists():
        return []
    raw = json.loads(target.read_text(encoding="utf-8"))
    out: list[Scenario] = []
    for row in raw:
        out.append(
            Scenario(
                query=str(row.get("query") or "").strip(),
                must_include_any=[str(v).lower() for v in (row.get("must_include_any") or []) if str(v).strip()],
                type=str(row.get("type") or "long_term_recall"),
            )
        )
    return [s for s in out if s.query]


def load_failure_cases(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or FAILURE_PATH
    if not target.exists():
        return []
    data = json.loads(target.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def _token_estimate(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def _precision_at_k(results: list[dict[str, Any]], tokens: list[str], k: int = 5) -> float:
    if k <= 0:
        return 0.0
    top = results[:k]
    if not top:
        return 0.0
    good = 0
    for row in top:
        text = str(row.get("text_content") or row.get("text_excerpt") or "").lower()
        if any(token in text for token in tokens):
            good += 1
    return good / len(top)


def _hit_quality(results: list[dict[str, Any]], tokens: list[str]) -> float:
    if not results:
        return 0.0
    score_sum = 0.0
    weight_sum = 0.0
    for rank, row in enumerate(results[:10], start=1):
        text = str(row.get("text_content") or row.get("text_excerpt") or "").lower()
        gain = 1.0 if any(token in text for token in tokens) else 0.0
        weight = 1.0 / rank
        score_sum += gain * weight
        weight_sum += weight
    if weight_sum <= 0:
        return 0.0
    return score_sum / weight_sum


def _token_reduction_percent(results: list[dict[str, Any]]) -> float:
    if not results:
        return 0.0
    baseline = 0
    compressed = 0
    for row in results[:10]:
        full = str(row.get("text_content") or "")
        excerpt = str(row.get("text_excerpt") or full[:200])
        baseline += _token_estimate(full)
        compressed += _token_estimate(excerpt)
    if baseline <= 0:
        return 0.0
    return max(0.0, min(100.0, (1.0 - (compressed / baseline)) * 100.0))


def _run_single(searcher: Searcher, scenario: Scenario, limit: int) -> dict[str, Any]:
    started = time.perf_counter()
    results = _run_async(searcher.search(query=scenario.query, limit=limit, debug=True))
    latency_ms = (time.perf_counter() - started) * 1000.0
    precision = _precision_at_k(results, scenario.must_include_any, k=min(5, limit))
    quality = _hit_quality(results, scenario.must_include_any)
    token_reduction = _token_reduction_percent(results)
    passed = quality >= 0.35 or precision >= 0.4
    return {
        "query": scenario.query,
        "type": scenario.type,
        "latency_ms": round(latency_ms, 3),
        "precision_at_5": round(precision, 6),
        "memory_hit_quality": round(quality, 6),
        "token_reduction_percent": round(token_reduction, 3),
        "result_count": len(results),
        "pass": passed,
    }


def run_evaluation_suite(limit: int = 10, iterations: int = 1) -> dict[str, Any]:
    scenarios = load_scenarios()
    failures = load_failure_cases()
    store = Store()
    indexer = IndexerService(store)
    searcher = Searcher(store, indexer)

    cases: list[dict[str, Any]] = []
    latency_samples: list[float] = []
    precision_samples: list[float] = []
    quality_samples: list[float] = []
    token_samples: list[float] = []

    for _ in range(max(1, int(iterations))):
        for scenario in scenarios:
            row = _run_single(searcher, scenario, limit=limit)
            cases.append(row)
            latency_samples.append(float(row["latency_ms"]))
            precision_samples.append(float(row["precision_at_5"]))
            quality_samples.append(float(row["memory_hit_quality"]))
            token_samples.append(float(row["token_reduction_percent"]))

    failure_results = evaluate_failure_cases(searcher, failures, limit=limit)

    total = len(cases)
    passed = sum(1 for row in cases if row["pass"])
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "suite_version": "research-v1",
        "metrics": {
            "latency_ms_p50": round(statistics.median(latency_samples), 3) if latency_samples else 0.0,
            "latency_ms_p95": round(_percentile(latency_samples, 95), 3) if latency_samples else 0.0,
            "retrieval_precision_at_5": round(statistics.mean(precision_samples), 6) if precision_samples else 0.0,
            "memory_hit_quality": round(statistics.mean(quality_samples), 6) if quality_samples else 0.0,
            "token_reduction_percent": round(statistics.mean(token_samples), 3) if token_samples else 0.0,
            "pass_rate": round((passed / total), 6) if total else 0.0,
        },
        "counts": {
            "scenarios": len(scenarios),
            "evaluated_cases": total,
            "failure_cases": len(failure_results),
        },
        "cases": cases,
        "failure_cases": failure_results,
    }
    return report


def evaluate_failure_cases(searcher: Searcher, failure_cases: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in failure_cases:
        query = str(row.get("query") or "").strip()
        if not query:
            continue
        expected = [str(v).lower() for v in (row.get("expected_signals") or [])]
        banned = [str(v).lower() for v in (row.get("banned_signals") or [])]
        results = _run_async(searcher.search(query=query, limit=limit, debug=True))
        combined = " ".join(str(r.get("text_content") or r.get("text_excerpt") or "").lower() for r in results)
        has_expected = all(sig in combined for sig in expected) if expected else True
        has_banned = any(sig in combined for sig in banned) if banned else False
        out.append(
            {
                "name": row.get("name"),
                "query": query,
                "pass": bool(has_expected and not has_banned),
                "has_expected": has_expected,
                "has_banned": has_banned,
                "result_count": len(results),
                "risk": row.get("risk", "unknown"),
            }
        )
    return out


def write_report(report: dict[str, Any], out_dir: Path | None = None) -> Path:
    target_dir = out_dir or RUNS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = target_dir / f"research-eval-{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_markdown_summary(report: dict[str, Any], out_dir: Path | None = None) -> Path:
    target_dir = out_dir or RUNS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = target_dir / f"research-eval-{stamp}.md"

    metrics = report.get("metrics") or {}
    failure_cases = report.get("failure_cases") or []
    lines = [
        "# MemoryFeed Research Evaluation Report",
        "",
        f"Generated at: {report.get('generated_at')}",
        "",
        "## Core Metrics",
        "",
        f"- Latency p50 (ms): {metrics.get('latency_ms_p50', 0)}",
        f"- Latency p95 (ms): {metrics.get('latency_ms_p95', 0)}",
        f"- Retrieval Precision@5: {metrics.get('retrieval_precision_at_5', 0)}",
        f"- Memory Hit Quality: {metrics.get('memory_hit_quality', 0)}",
        f"- Token Reduction (%): {metrics.get('token_reduction_percent', 0)}",
        f"- Pass Rate: {metrics.get('pass_rate', 0)}",
        "",
        "## Failure Cases",
        "",
        "| Name | Risk | Pass | Expected | Banned |",
        "|---|---|---:|---:|---:|",
    ]
    for row in failure_cases:
        lines.append(
            f"| {row.get('name', '')} | {row.get('risk', '')} | {'yes' if row.get('pass') else 'no'} | {'yes' if row.get('has_expected') else 'no'} | {'yes' if row.get('has_banned') else 'no'} |"
        )

    lines.extend([
        "",
        "## Performance Graph (Recent Runs)",
        "",
        "```mermaid",
        "xychart-beta",
        "    title \"Latency p95 over runs\"",
        "    x-axis [run1, run2, run3, run4, run5]",
        "    y-axis \"ms\" 0 --> 3000",
        f"    line [{_mermaid_recent_series('latency_ms_p95')}]",
        "```",
        "",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _mermaid_recent_series(metric_key: str) -> str:
    runs = sorted(RUNS_DIR.glob("research-eval-*.json"))[-5:]
    values: list[str] = []
    for run in runs:
        try:
            payload = json.loads(run.read_text(encoding="utf-8"))
            metric = float((payload.get("metrics") or {}).get(metric_key) or 0.0)
            values.append(str(round(metric, 2)))
        except Exception:
            values.append("0")
    while len(values) < 5:
        values.insert(0, "0")
    return ", ".join(values)


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (p / 100.0) * (len(ordered) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    frac = rank - lower
    return ordered[lower] * (1.0 - frac) + ordered[upper] * frac


def _run_async(coro):
    import asyncio

    return asyncio.run(coro)
