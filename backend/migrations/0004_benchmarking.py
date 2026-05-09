from __future__ import annotations

import sqlite3

from backend.migrations import ensure_indexes

REVISION = 4
NAME = "benchmarking_history"


def apply(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS benchmark_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL,
            platform TEXT NOT NULL,
            success_rate REAL DEFAULT 0.0,
            duplicate_rate REAL DEFAULT 0.0,
            missing_field_rate REAL DEFAULT 0.0,
            snapshot_json TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    ensure_indexes(
        conn,
        [
            "CREATE INDEX IF NOT EXISTS idx_benchmark_runs_created_at ON benchmark_runs(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_benchmark_runs_platform ON benchmark_runs(platform);",
        ],
    )
