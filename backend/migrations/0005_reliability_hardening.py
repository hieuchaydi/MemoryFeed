from __future__ import annotations

import sqlite3

from backend.migrations import ensure_column, ensure_indexes

REVISION = 5
NAME = "reliability_hardening_fields"


def apply(conn: sqlite3.Connection) -> None:
    ensure_column(conn, "items", "capture_confidence", "REAL DEFAULT 0.0")
    ensure_column(conn, "items", "confidence_reasons", "TEXT")
    ensure_column(conn, "items", "capture_method", "TEXT")
    ensure_column(conn, "items", "extractor_version", "TEXT")
    ensure_column(conn, "items", "capture_source", "TEXT")
    ensure_column(conn, "items", "replay_source", "TEXT")
    ensure_indexes(
        conn,
        [
            "CREATE INDEX IF NOT EXISTS idx_items_capture_confidence ON items(capture_confidence);",
            "CREATE INDEX IF NOT EXISTS idx_items_capture_source ON items(capture_source);",
        ],
    )
