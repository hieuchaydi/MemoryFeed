from __future__ import annotations

import sqlite3

from memoryfeed_core.migrations import ensure_indexes

REVISION = 6
NAME = "memory_lifecycle_infrastructure"


def apply(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_events (
            event_id TEXT PRIMARY KEY,
            memory_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_nodes (
            memory_id TEXT PRIMARY KEY,
            item_id TEXT,
            state TEXT NOT NULL,
            memory_type TEXT NOT NULL,
            summary_short TEXT,
            summary_medium TEXT,
            summary_long TEXT,
            confidence REAL DEFAULT 1.0,
            reinforcement REAL DEFAULT 0.0,
            decay_score REAL DEFAULT 0.0,
            importance_score REAL DEFAULT 0.0,
            last_accessed_at TEXT,
            forgotten_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_edges (
            edge_id TEXT PRIMARY KEY,
            from_memory_id TEXT NOT NULL,
            to_memory_id TEXT NOT NULL,
            relation TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_conflicts (
            conflict_id TEXT PRIMARY KEY,
            memory_id TEXT NOT NULL,
            field_name TEXT NOT NULL,
            value_a TEXT,
            value_b TEXT,
            confidence_a REAL DEFAULT 0.5,
            confidence_b REAL DEFAULT 0.5,
            resolved_value TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            resolved_at TEXT
        );
        """
    )

    ensure_indexes(
        conn,
        [
            "CREATE INDEX IF NOT EXISTS idx_memory_events_memory_id ON memory_events(memory_id);",
            "CREATE INDEX IF NOT EXISTS idx_memory_events_type ON memory_events(event_type);",
            "CREATE INDEX IF NOT EXISTS idx_memory_nodes_state ON memory_nodes(state);",
            "CREATE INDEX IF NOT EXISTS idx_memory_nodes_item_id ON memory_nodes(item_id);",
            "CREATE INDEX IF NOT EXISTS idx_memory_edges_from ON memory_edges(from_memory_id);",
            "CREATE INDEX IF NOT EXISTS idx_memory_edges_to ON memory_edges(to_memory_id);",
            "CREATE INDEX IF NOT EXISTS idx_memory_conflicts_memory_id ON memory_conflicts(memory_id);",
            "CREATE INDEX IF NOT EXISTS idx_memory_conflicts_status ON memory_conflicts(status);",
        ],
    )

