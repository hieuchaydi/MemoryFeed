from __future__ import annotations

import sqlite3

from backend.migrations import ensure_column, ensure_indexes

REVISION = 7
NAME = "namespace_isolation_fields"


def apply(conn: sqlite3.Connection) -> None:
    ensure_column(conn, "items", "namespace", "TEXT DEFAULT 'default'")
    ensure_column(conn, "memory_nodes", "namespace", "TEXT DEFAULT 'default'")
    ensure_indexes(
        conn,
        [
            "CREATE INDEX IF NOT EXISTS idx_items_namespace ON items(namespace);",
            "CREATE INDEX IF NOT EXISTS idx_memory_nodes_namespace ON memory_nodes(namespace);",
        ],
    )
