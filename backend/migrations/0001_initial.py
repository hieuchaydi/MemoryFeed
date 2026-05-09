from __future__ import annotations

import sqlite3

REVISION = 1
NAME = "initial_schema"


def apply(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            platform TEXT NOT NULL,
            content_type TEXT NOT NULL,
            text_content TEXT,
            image_urls TEXT,
            image_captions TEXT,
            author TEXT,
            captured_at TEXT NOT NULL,
            dwell_seconds REAL,
            embedding_done INTEGER DEFAULT 0,
            vision_done INTEGER DEFAULT 0,
            dedupe_key TEXT UNIQUE,
            image_cache_paths TEXT
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )

    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
            text_content,
            image_captions,
            author,
            content=items,
            content_rowid=rowid
        );
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS items_ai AFTER INSERT ON items BEGIN
            INSERT INTO items_fts(rowid, text_content, image_captions, author)
            VALUES (new.rowid, new.text_content, new.image_captions, new.author);
        END;
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS items_ad AFTER DELETE ON items BEGIN
            INSERT INTO items_fts(items_fts, rowid, text_content, image_captions, author)
            VALUES('delete', old.rowid, old.text_content, old.image_captions, old.author);
        END;
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS items_au AFTER UPDATE ON items BEGIN
            INSERT INTO items_fts(items_fts, rowid, text_content, image_captions, author)
            VALUES('delete', old.rowid, old.text_content, old.image_captions, old.author);
            INSERT INTO items_fts(rowid, text_content, image_captions, author)
            VALUES (new.rowid, new.text_content, new.image_captions, new.author);
        END;
        """
    )
