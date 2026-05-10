from __future__ import annotations

import sqlite3

from memoryfeed_core.migrations import ensure_column, ensure_indexes

REVISION = 3
NAME = "memory_intelligence_foundations"


def apply(conn: sqlite3.Connection) -> None:
    ensure_column(conn, "items", "related_topics", "TEXT")
    ensure_column(conn, "items", "related_entities", "TEXT")
    ensure_column(conn, "items", "cluster_id", "TEXT")
    ensure_column(conn, "items", "semantic_group", "TEXT")
    ensure_column(conn, "items", "importance_score", "REAL DEFAULT 0.0")
    ensure_column(conn, "items", "resurfacing_score", "REAL DEFAULT 0.0")
    ensure_column(conn, "items", "recency_score", "REAL DEFAULT 0.0")
    ensure_column(conn, "items", "recurrence_score", "REAL DEFAULT 0.0")
    ensure_column(conn, "items", "ranking_debug", "TEXT")
    ensure_column(conn, "items", "embedding_skipped_reason", "TEXT")
    ensure_column(conn, "items", "suspicious_prompt_content", "INTEGER DEFAULT 0")
    ensure_column(conn, "items", "safety_signals", "TEXT")
    ensure_column(conn, "items", "archive_reason", "TEXT")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_links (
            from_item_id TEXT NOT NULL,
            to_item_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            weight REAL DEFAULT 0.0,
            reason TEXT,
            created_at TEXT NOT NULL,
            PRIMARY KEY (from_item_id, to_item_id, relation_type)
        );
        """
    )
    ensure_indexes(
        conn,
        [
            "CREATE INDEX IF NOT EXISTS idx_items_cluster_id ON items(cluster_id);",
            "CREATE INDEX IF NOT EXISTS idx_items_semantic_group ON items(semantic_group);",
            "CREATE INDEX IF NOT EXISTS idx_items_importance ON items(importance_score);",
            "CREATE INDEX IF NOT EXISTS idx_items_resurfacing ON items(resurfacing_score);",
            "CREATE INDEX IF NOT EXISTS idx_links_from ON memory_links(from_item_id);",
            "CREATE INDEX IF NOT EXISTS idx_links_to ON memory_links(to_item_id);",
        ],
    )

