from __future__ import annotations

import sqlite3

from backend.migrations import ensure_column, ensure_indexes

REVISION = 2
NAME = "capture_quality_and_metadata"


def apply(conn: sqlite3.Connection) -> None:
    ensure_column(conn, "items", "starred", "INTEGER DEFAULT 0")
    ensure_column(conn, "items", "note", "TEXT")
    ensure_column(conn, "items", "tags", "TEXT")
    ensure_column(conn, "items", "heat", "REAL DEFAULT 1.0")
    ensure_column(conn, "items", "last_surfaced", "TEXT")
    ensure_column(conn, "items", "surfaced_count", "INTEGER DEFAULT 0")
    ensure_column(conn, "items", "archived_at", "TEXT")
    ensure_column(conn, "items", "canonical_url", "TEXT")
    ensure_column(conn, "items", "post_id", "TEXT")
    ensure_column(conn, "items", "media_urls", "TEXT")
    ensure_column(conn, "items", "author_name", "TEXT")
    ensure_column(conn, "items", "author_handle", "TEXT")
    ensure_column(conn, "items", "thumbnail_url", "TEXT")
    ensure_column(conn, "items", "source_context", "TEXT")
    ensure_column(conn, "items", "quality_flags", "TEXT")
    ensure_column(conn, "items", "capture_debug", "TEXT")
    ensure_column(conn, "items", "url_domain", "TEXT")
    ensure_indexes(
        conn,
        [
            "CREATE INDEX IF NOT EXISTS idx_items_captured_at ON items(captured_at);",
            "CREATE INDEX IF NOT EXISTS idx_items_platform ON items(platform);",
            "CREATE INDEX IF NOT EXISTS idx_items_type ON items(content_type);",
            "CREATE INDEX IF NOT EXISTS idx_items_heat ON items(heat);",
            "CREATE INDEX IF NOT EXISTS idx_items_archived_at ON items(archived_at);",
            "CREATE INDEX IF NOT EXISTS idx_items_canonical_url ON items(canonical_url);",
            "CREATE INDEX IF NOT EXISTS idx_items_post_id ON items(post_id);",
            "CREATE INDEX IF NOT EXISTS idx_items_url_domain ON items(url_domain);",
        ],
    )
