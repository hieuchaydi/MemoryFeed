from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _sqlcipher_enabled() -> bool:
    return os.getenv("MEMORY_SQLCIPHER_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def _sqlcipher_key() -> str:
    return os.getenv("MEMORY_SQLCIPHER_KEY", "").strip()


def sqlcipher_status() -> dict[str, Any]:
    enabled = _sqlcipher_enabled()
    key_present = bool(_sqlcipher_key())
    available = False
    if enabled:
        try:
            import pysqlcipher3.dbapi2 as _  # type: ignore

            available = True
        except Exception:
            available = False
    return {
        "enabled": enabled,
        "available": available,
        "active": bool(enabled and available and key_present),
        "key_present": key_present,
    }


def connect_db(path: Path, *, check_same_thread: bool = False) -> sqlite3.Connection:
    status = sqlcipher_status()
    if status["enabled"] and status["available"]:
        try:
            import pysqlcipher3.dbapi2 as sqlcipher  # type: ignore

            conn = sqlcipher.connect(str(path), check_same_thread=check_same_thread)
            key = _sqlcipher_key()
            if key:
                escaped_key = key.replace("'", "''")
                conn.execute(f"PRAGMA key = '{escaped_key}';")
                conn.execute("PRAGMA cipher_compatibility = 4;")
            else:
                logger.warning("sqlcipher_enabled_but_missing_key")
            return conn
        except Exception:
            logger.exception("sqlcipher_connection_failed_fallback_sqlite path=%s", path)
    return sqlite3.connect(path, check_same_thread=check_same_thread)
