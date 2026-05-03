from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import httpx

from backend.indexer import IndexerService
from backend.logging_setup import configure_logging
from backend.native_accel import status as native_status
from backend.searcher import Searcher
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


def _create_services() -> tuple[Store, IndexerService, Searcher]:
    store = Store()
    indexer = IndexerService(store)
    searcher = Searcher(store, indexer)
    return store, indexer, searcher


def create_server(host: str = "127.0.0.1", port: int = 7748, path: str = "/mcp"):
    if FastMCP is None:
        raise RuntimeError(
            "MCP SDK not installed. Run: pip install \"mcp[cli]\""
        ) from _MCP_IMPORT_ERROR

    store, indexer, searcher = _create_services()
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
            "ai": ["sentence-transformers", "Ollama (qwen2.5:7b, llava:7b)"],
            "extension": ["Chrome/Edge/Brave", "Firefox"],
            "optional_native": "C++ via pybind11",
        }
        return {
            "project": "memoryfeed",
            "stack": stack,
            "paths": {
                "data_dir": str(DATA_DIR),
                "db_path": str(DB_PATH),
                "vector_dir": str(LANCEDB_DIR),
                "image_cache_dir": str(IMAGE_CACHE_DIR),
            },
        }

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

        ollama_ok = False
        try:
            resp = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            ollama_ok = resp.status_code == 200
        except Exception:
            ollama_ok = False

        if not ollama_ok:
            issues.append(
                HealthIssue(
                    type="ollama_unreachable",
                    severity="medium",
                    message="Ollama is unreachable at http://localhost:11434.",
                    suggested_fix="Start Ollama with `ollama serve`.",
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
            "Run `memoryfeed serve-web --host 0.0.0.0 --port 7749` for public web access.",
        ]

        return {
            "score": score,
            "issues": [asdict(i) for i in issues],
            "summary": {
                "today": stats.get("today", 0),
                "total": stats.get("total", 0),
                "native": native_status(),
                "ollama_ok": ollama_ok,
            },
            "suggested_next_steps": next_steps,
        }

    @mcp.tool(name="get_memoryfeed_stats")
    def get_memoryfeed_stats() -> dict[str, Any]:
        """Returns capture and platform statistics."""
        payload = store.stats()
        payload["native"] = native_status()
        payload["date"] = date.today().isoformat()
        return payload

    @mcp.tool(name="search_memory")
    async def search_memory(query: str, limit: int = 10, days_back: int | None = None) -> dict[str, Any]:
        """
        Hybrid search across captured social content.
        """
        safe_limit = max(1, min(limit, 50))
        results = await searcher.search(query=query, limit=safe_limit, days_back=days_back)
        return {
            "query": query,
            "count": len(results),
            "results": results,
        }

    @mcp.tool(name="timeline_memories")
    def timeline_memories(date_str: str | None = None, platform: str | None = None, limit: int = 100) -> dict[str, Any]:
        """
        Returns timeline entries for a date, optionally filtered by platform.
        """
        selected_date = date_str or date.today().isoformat()
        items = store.all_for_timeline(selected_date, platform)
        safe_limit = max(1, min(limit, 500))
        trimmed = items[:safe_limit]
        return {
            "date": selected_date,
            "platform": platform,
            "count": len(trimmed),
            "items": trimmed,
        }

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
