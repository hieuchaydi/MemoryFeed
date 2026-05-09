from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any

from backend.llm_clients import gemini_state, groq_state
from backend.migrate import latest_schema_version, run_migrations
from backend.runtime_config import load_runtime_config, provider_requires_key
from backend.store import DB_PATH, LANCEDB_DIR


def run_doctor() -> dict[str, Any]:
    cfg = load_runtime_config()
    checks: list[dict[str, Any]] = []

    py_ok = sys.version_info >= (3, 12)
    checks.append(
        _check(
            "python_version",
            py_ok,
            f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "Python 3.12+ is required",
        )
    )

    db_ok, db_message = _check_db_writable(DB_PATH)
    checks.append(_check("db_writable", db_ok, db_message, f"Cannot write DB path: {DB_PATH}"))

    fts_ok, fts_message = _check_sqlite_fts5()
    checks.append(_check("sqlite_fts5", fts_ok, fts_message, "SQLite FTS5 is unavailable"))

    lancedb_ok, lancedb_message = _check_lancedb(LANCEDB_DIR)
    checks.append(_check("lancedb", lancedb_ok, lancedb_message, "LanceDB is unavailable"))

    frontend_dist = Path("frontend") / "dist" / "index.html"
    checks.append(
        _check(
            "frontend_build",
            frontend_dist.exists(),
            f"Found frontend build at {frontend_dist}" if frontend_dist.exists() else "frontend/dist not built yet",
            "Build frontend for production serving (memoryfeed build-frontend)",
            severity="warning",
        )
    )

    checks.append(
        _check(
            "offline_mode",
            True,
            "OFFLINE_ONLY is enabled" if cfg.offline_only else "OFFLINE_ONLY is disabled",
            "",
            severity="info",
        )
    )

    g_state = gemini_state()
    gemini_required = provider_requires_key("gemini", cfg)
    checks.append(
        _check(
            "gemini_key",
            (not gemini_required) or g_state.enabled,
            g_state.reason,
            "Set GEMINI_API_KEY or disable Gemini provider",
        )
    )

    q_state = groq_state()
    groq_required = provider_requires_key("groq", cfg)
    checks.append(
        _check(
            "groq_key",
            (not groq_required) or q_state.enabled,
            q_state.reason,
            "Set GROQ_API_KEY or disable Groq provider",
        )
    )

    checks.append(
        _check(
            "public_mode_admin_token",
            (not cfg.public_mode) or bool(cfg.admin_token),
            "Admin token configured" if cfg.admin_token else "Admin token missing",
            "Set MEMORYFEED_ADMIN_TOKEN when MEMORYFEED_PUBLIC_MODE=true",
        )
    )

    try:
        migration_report = run_migrations(DB_PATH)
        current = int(migration_report["after"])
        latest = int(latest_schema_version())
        checks.append(
            _check(
                "schema_version",
                current >= latest,
                f"Schema version {current} (latest={latest})",
                "Run memoryfeed migrate",
                severity="warning",
            )
        )
    except Exception as exc:
        checks.append(
            _check(
                "schema_version",
                False,
                f"Cannot validate schema version: {exc}",
                "Run memoryfeed migrate",
                severity="warning",
            )
        )

    has_error = any((not item["ok"]) and item["severity"] == "error" for item in checks)
    has_warning = any((not item["ok"]) and item["severity"] == "warning" for item in checks)
    status = "fail" if has_error else "warn" if has_warning else "ok"

    return {
        "status": status,
        "config": {
            "offline_only": cfg.offline_only,
            "ai_provider": cfg.ai_provider,
            "public_mode": cfg.public_mode,
            "admin_token_configured": bool(cfg.admin_token),
            "mcp": {
                "max_results": cfg.mcp_max_results,
                "allow_timeline": cfg.mcp_allow_timeline,
                "allow_active_feed": cfg.mcp_allow_active_feed,
                "redact_output": cfg.mcp_redact_output,
            },
            "memory_intelligence": {
                "semantic_dedupe": cfg.memory_semantic_dedupe,
                "dedupe_similarity_threshold": cfg.memory_dedupe_similarity_threshold,
                "sanitize_prompt_content": cfg.memory_sanitize_prompt_content,
                "skip_sensitive_embedding": cfg.memory_skip_sensitive_embedding,
                "retention_days": cfg.memory_retention_days,
                "auto_archive": cfg.memory_auto_archive,
                "archive_low_score_threshold": cfg.memory_archive_low_score_threshold,
            },
        },
        "checks": checks,
    }


def _check(name: str, ok: bool, message: str, suggested_fix: str, severity: str = "error") -> dict[str, Any]:
    return {
        "name": name,
        "ok": bool(ok),
        "severity": "info" if severity == "info" else ("warning" if severity == "warning" else "error"),
        "message": message,
        "suggested_fix": suggested_fix,
    }


def _check_db_writable(db_path: Path) -> tuple[bool, str]:
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS doctor_probe (id INTEGER PRIMARY KEY, ok INTEGER)")
        conn.execute("DELETE FROM doctor_probe")
        conn.execute("INSERT INTO doctor_probe(ok) VALUES (1)")
        conn.commit()
        conn.close()
        return True, f"DB writable: {db_path}"
    except Exception as exc:  # pragma: no cover - platform-specific failure paths
        return False, str(exc)


def _check_sqlite_fts5() -> tuple[bool, str]:
    try:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE VIRTUAL TABLE fts5_probe USING fts5(content)")
        conn.close()
        return True, "SQLite FTS5 is available"
    except Exception as exc:
        return False, str(exc)


def _check_lancedb(path: Path) -> tuple[bool, str]:
    try:
        import lancedb

        path.mkdir(parents=True, exist_ok=True)
        lancedb.connect(str(path))
        return True, f"LanceDB available at {path}"
    except Exception as exc:
        return False, str(exc)
