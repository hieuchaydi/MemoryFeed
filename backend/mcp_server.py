from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

from backend.indexer import IndexerService
from backend.interest import InterestEngine
from backend.llm_clients import check_gemini_connectivity, check_groq_connectivity, providers_snapshot
from backend.logging import log_event
from backend.logging_setup import configure_logging
from backend.native_accel import status as native_status
from backend.redaction import redact_value
from backend.runtime_config import load_runtime_config, provider_requires_key
from backend.safety import assess_prompt_risk
from backend.searcher import Searcher
from backend.safety import sanitize_untrusted_payload
from backend.store import DATA_DIR, DB_PATH, IMAGE_CACHE_DIR, LANCEDB_DIR, Store

try:
    from mcp.server.fastmcp import FastMCP
except Exception as exc:  # pragma: no cover
    FastMCP = None  # type: ignore[assignment]
    _MCP_IMPORT_ERROR = exc
else:
    _MCP_IMPORT_ERROR = None

configure_logging()
logger = logging.getLogger("memoryfeed.mcp")


@dataclass
class HealthIssue:
    type: str
    severity: str
    message: str
    suggested_fix: str


def _create_services() -> tuple[Store, IndexerService, Searcher, InterestEngine]:
    store = Store()
    indexer = IndexerService(store)
    searcher = Searcher(store, indexer)
    interest = InterestEngine(store, searcher)
    return store, indexer, searcher, interest


def _clamp_mcp_limit(requested: int, hard_cap: int = 50) -> int:
    cfg = load_runtime_config()
    return max(1, min(requested, cfg.mcp_max_results, hard_cap))


def _finalize_tool_payload(tool_name: str, payload: dict[str, Any], query: str | None = None) -> dict[str, Any]:
    cfg = load_runtime_config()
    if cfg.memory_sanitize_prompt_content:
        payload = sanitize_untrusted_payload(payload)
    if cfg.mcp_redact_output:
        payload = redact_value(payload)
        payload = _sanitize_untrusted_payload(payload)
    result_count = int(payload.get("count", 0))
    log_event(
        logger,
        "mcp_tool_result",
        platform="mcp",
        status=tool_name,
        count=result_count,
        benchmark_context={"query": (query or "")[:200]},
    )
    return payload


def _sanitize_untrusted_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("items") or payload.get("results")
    if not isinstance(rows, list):
        return payload
    sanitized = []
    for row in rows:
        if not isinstance(row, dict):
            sanitized.append(row)
            continue
        copy = dict(row)
        risk, reason = assess_prompt_risk(str(copy.get("text_content") or copy.get("text_excerpt") or ""))
        if risk >= 0.6:
            copy["text_content"] = "[SANITIZED_UNTRUSTED_CONTENT]"
            copy["text_excerpt"] = "[SANITIZED_UNTRUSTED_CONTENT]"
            copy["prompt_risk_score"] = risk
            copy["prompt_risk_reason"] = reason
        sanitized.append(copy)
    if "items" in payload:
        payload["items"] = sanitized
    if "results" in payload:
        payload["results"] = sanitized
    return payload


def create_server(host: str = "127.0.0.1", port: int = 7748, path: str = "/mcp"):
    if FastMCP is None:
        raise RuntimeError(
            "MCP SDK not installed. Run: pip install \"mcp[cli]\""
        ) from _MCP_IMPORT_ERROR

    store, indexer, searcher, interest = _create_services()
    logger.info("create_mcp_server host=%s port=%s path=%s", host, port, path)
    mcp = FastMCP(
        "MemoryFeed MCP",
        host=host,
        port=port,
        mount_path="/",
        streamable_http_path=path,
    )

    @mcp.tool(name="detect_stack")
    def detect_stack() -> dict[str, Any]:
        """Detects project stack and runtime profile for MemoryFeed."""
        stack = {
            "backend": "Python + FastAPI",
            "frontend": "React + Vite + TypeScript",
            "database": ["SQLite (FTS5 + WAL)", "LanceDB"],
            "ai": ["sentence-transformers", "Gemini API", "Groq API (Qwen)"],
            "extension": ["Chrome/Edge/Brave", "Firefox"],
            "optional_native": "C++ via pybind11",
        }
        return _finalize_tool_payload(
            "detect_stack",
            {
            "project": "memoryfeed",
            "stack": stack,
            "paths": {
                "data_dir": str(DATA_DIR),
                "db_path": str(DB_PATH),
                "vector_dir": str(LANCEDB_DIR),
                "image_cache_dir": str(IMAGE_CACHE_DIR),
            },
            },
        )

    @mcp.tool(name="check_project_health")
    def check_project_health() -> dict[str, Any]:
        """
        Runs a local health check for MemoryFeed and returns score, issues, and next steps.
        """
        issues: list[HealthIssue] = []

        if not DB_PATH.exists():
            issues.append(
                HealthIssue(
                    type="missing_db",
                    severity="high",
                    message=f"Database not found: {DB_PATH}",
                    suggested_fix="Start server once and capture at least one item.",
                )
            )
        elif DB_PATH.stat().st_size == 0:
            issues.append(
                HealthIssue(
                    type="empty_db",
                    severity="medium",
                    message=f"Database file is empty: {DB_PATH}",
                    suggested_fix="Check write permissions and run a capture test.",
                )
            )

        cfg = load_runtime_config()
        gemini_ok, gemini_reason = check_gemini_connectivity(timeout_s=4.0)
        groq_ok, groq_reason = check_groq_connectivity(timeout_s=4.0)
        gemini_required = provider_requires_key("gemini", cfg)
        groq_required = provider_requires_key("groq", cfg)

        if not gemini_ok and gemini_required:
            issues.append(
                HealthIssue(
                    type="gemini_unavailable",
                    severity="medium",
                    message=f"Gemini unavailable: {gemini_reason}",
                    suggested_fix="Set valid GEMINI_API_KEY and verify network egress.",
                )
            )

        if not groq_ok and groq_required:
            issues.append(
                HealthIssue(
                    type="groq_unavailable",
                    severity="medium",
                    message=f"Groq unavailable: {groq_reason}",
                    suggested_fix="Set valid GROQ_API_KEY and verify Groq API access.",
                )
            )

        stats = store.stats()
        if stats.get("total", 0) == 0:
            issues.append(
                HealthIssue(
                    type="no_captures",
                    severity="low",
                    message="No captured items yet.",
                    suggested_fix="Load extension and browse supported social feeds for 3+ seconds.",
                )
            )

        base_score = 100
        penalties = {"high": 35, "medium": 20, "low": 10}
        for issue in issues:
            base_score -= penalties.get(issue.severity, 10)
        score = max(0, base_score)

        next_steps = [i.suggested_fix for i in issues] or [
            "Run `search_memory` to validate retrieval quality.",
            "Run `memoryfeed doctor` for full local safety diagnostics.",
        ]

        return _finalize_tool_payload(
            "check_project_health",
            {
            "score": score,
            "issues": [asdict(i) for i in issues],
            "summary": {
                "today": stats.get("today", 0),
                "total": stats.get("total", 0),
                "native": native_status(),
                "providers": providers_snapshot(),
                "gemini_ok": gemini_ok,
                "groq_ok": groq_ok,
                "runtime_perf": searcher.perf_stats(),
            },
            "suggested_next_steps": next_steps,
            },
        )

    @mcp.tool(name="get_memoryfeed_stats")
    def get_memoryfeed_stats() -> dict[str, Any]:
        """Returns capture and platform statistics."""
        payload = store.stats()
        payload["native"] = native_status()
        payload["date"] = date.today().isoformat()
        return _finalize_tool_payload("get_memoryfeed_stats", payload)

    @mcp.tool(name="get_runtime_perf")
    def get_runtime_perf() -> dict[str, Any]:
        """Returns runtime diagnostics (cache, queues, native status)."""
        payload = {
            "searcher": searcher.perf_stats(),
            "indexer": indexer.status(),
            "native": native_status(),
        }
        return _finalize_tool_payload("get_runtime_perf", payload)

    @mcp.tool(name="active_memory_feed")
    async def active_memory_feed(limit: int = 10, mode: str = "default") -> dict[str, Any]:
        """
        Returns a proactive feed ranked by memory heat, recency, resurfacing gap, and mode.
        """
        cfg = load_runtime_config()
        if not cfg.mcp_allow_active_feed:
            return _finalize_tool_payload(
                "active_memory_feed",
                {"count": 0, "items": [], "warning": "active_memory_feed is disabled by server policy"},
            )
        safe_limit = _clamp_mcp_limit(limit, hard_cap=50)
        safe_mode = mode if mode in {"default", "focus", "light", "explore"} else "default"
        items = await interest.active_feed(limit=safe_limit, mode=safe_mode)
        return _finalize_tool_payload(
            "active_memory_feed",
            {
            "mode": safe_mode,
            "count": len(items),
            "items": items,
            },
        )

    @mcp.tool(name="resurface_memory_context")
    async def resurface_memory_context(context: str, limit: int = 5, bump_heat: bool = True) -> dict[str, Any]:
        """
        Surfaces old memories related to the current work/read/write context.
        """
        safe_limit = _clamp_mcp_limit(limit, hard_cap=20)
        items = await interest.resurface_context(context=context, limit=safe_limit, bump_heat=bump_heat)
        return _finalize_tool_payload(
            "resurface_memory_context",
            {
            "count": len(items),
            "items": items,
            },
            query=context,
        )

    @mcp.tool(name="search_memory")
    async def search_memory(query: str, limit: int = 10, days_back: int | None = None) -> dict[str, Any]:
        """
        Hybrid search across captured social content.
        """
        safe_limit = _clamp_mcp_limit(limit, hard_cap=50)
        results = await searcher.search(query=query, limit=safe_limit, days_back=days_back)
        return _finalize_tool_payload(
            "search_memory",
            {
            "query": query,
            "count": len(results),
            "results": results,
            },
            query=query,
        )

    @mcp.tool(name="timeline_memories")
    def timeline_memories(date_str: str | None = None, platform: str | None = None, limit: int = 100) -> dict[str, Any]:
        """
        Returns timeline entries for a date, optionally filtered by platform.
        """
        cfg = load_runtime_config()
        if not cfg.mcp_allow_timeline:
            return _finalize_tool_payload(
                "timeline_memories",
                {"count": 0, "items": [], "warning": "timeline_memories is disabled by server policy"},
            )
        selected_date = date_str or date.today().isoformat()
        items = store.all_for_timeline(selected_date, platform)
        safe_limit = _clamp_mcp_limit(limit, hard_cap=500)
        trimmed = items[:safe_limit]
        return _finalize_tool_payload(
            "timeline_memories",
            {
            "date": selected_date,
            "platform": platform,
            "count": len(trimmed),
            "items": trimmed,
            },
            query=f"date={selected_date};platform={platform or ''}",
        )

    return mcp


def run_mcp(transport: str = "stdio", host: str = "127.0.0.1", port: int = 7748, path: str = "/mcp") -> None:
    mcp = create_server(host=host, port=port, path=path)
    logger.info("run_mcp transport=%s host=%s port=%s path=%s", transport, host, port, path)
    if transport == "stdio":
        mcp.run(transport="stdio")
        return
    if transport in {"streamable-http", "http"}:
        mcp.run(transport="streamable-http")
        return
    if transport == "sse":
        mcp.run(transport="sse")
        return
    raise ValueError(f"Unsupported MCP transport: {transport}")


if __name__ == "__main__":
    run_mcp()
