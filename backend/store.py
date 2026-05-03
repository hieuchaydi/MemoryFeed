from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path.home() / ".memoryfeed"
DB_PATH = DATA_DIR / "memoryfeed.db"
LANCEDB_DIR = DATA_DIR / "lancedb"
IMAGE_CACHE_DIR = DATA_DIR / "images"


class Store:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        LANCEDB_DIR.mkdir(parents=True, exist_ok=True)
        IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.execute("PRAGMA foreign_keys=ON;")

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

                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_captured_at ON items(captured_at);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_platform ON items(platform);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_type ON items(content_type);")
                conn.commit()
            finally:
                conn.close()

    def insert_item(self, item: dict[str, Any]) -> tuple[bool, str | None]:
        with self._lock:
            conn = self._connect()
            try:
                existing = conn.execute(
                    "SELECT id FROM items WHERE dedupe_key = ? LIMIT 1", (item["dedupe_key"],)
                ).fetchone()
                if existing:
                    return False, str(existing["id"])

                conn.execute(
                    """
                    INSERT INTO items (
                        id, url, platform, content_type, text_content, image_urls,
                        image_captions, author, captured_at, dwell_seconds,
                        embedding_done, vision_done, dedupe_key, image_cache_paths
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["id"],
                        item["url"],
                        item["platform"],
                        item["content_type"],
                        item.get("text_content"),
                        json.dumps(item.get("image_urls", []), ensure_ascii=False),
                        json.dumps(item.get("image_captions", []), ensure_ascii=False),
                        item.get("author"),
                        item["captured_at"],
                        item.get("dwell_seconds", 0.0),
                        int(item.get("embedding_done", 0)),
                        int(item.get("vision_done", 0)),
                        item["dedupe_key"],
                        json.dumps(item.get("image_cache_paths", []), ensure_ascii=False),
                    ),
                )
                conn.commit()
                return True, item["id"]
            finally:
                conn.close()

    def get_item(self, item_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
            return self._row_to_item(row) if row else None
        finally:
            conn.close()

    def update_vision_result(
        self,
        item_id: str,
        captions: list[str],
        cache_paths: list[str],
    ) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    UPDATE items
                    SET image_captions = ?, image_cache_paths = ?, vision_done = 1, embedding_done = 0
                    WHERE id = ?
                    """,
                    (json.dumps(captions, ensure_ascii=False), json.dumps(cache_paths, ensure_ascii=False), item_id),
                )
                conn.commit()
            finally:
                conn.close()

    def mark_embedding_done(self, item_id: str) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("UPDATE items SET embedding_done = 1 WHERE id = ?", (item_id,))
                conn.commit()
            finally:
                conn.close()

    def search_fts(self, query: str, limit: int = 20, days_back: int | None = None) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            params: list[Any] = [query]
            where = ""
            if days_back is not None:
                cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
                where = "AND items.captured_at >= ?"
                params.append(cutoff.isoformat())
            params.append(limit)

            sql = f"""
                SELECT
                    items.id,
                    items.url,
                    items.platform,
                    items.text_content,
                    items.image_urls,
                    items.image_cache_paths,
                    items.author,
                    items.captured_at,
                    bm25(items_fts) AS bm25_score
                FROM items_fts
                JOIN items ON items_fts.rowid = items.rowid
                WHERE items_fts MATCH ? {where}
                ORDER BY bm25_score ASC
                LIMIT ?
            """
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_search_dict(r, bm25_key="bm25_score") for r in rows]
        finally:
            conn.close()

    def all_for_timeline(self, date_str: str, platform: str | None = None) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            where = "DATE(captured_at) = DATE(?)"
            params: list[Any] = [date_str]
            if platform:
                where += " AND platform = ?"
                params.append(platform)
            rows = conn.execute(
                f"""
                SELECT *
                FROM items
                WHERE {where}
                ORDER BY captured_at DESC
                """,
                params,
            ).fetchall()
            return [self._row_to_item(r) for r in rows]
        finally:
            conn.close()

    def stats(self) -> dict[str, Any]:
        conn = self._connect()
        try:
            total = int(conn.execute("SELECT COUNT(*) FROM items").fetchone()[0])
            today = int(
                conn.execute("SELECT COUNT(*) FROM items WHERE DATE(captured_at)=DATE('now', 'localtime')").fetchone()[0]
            )
            by_platform = [
                {"key": row[0], "count": int(row[1])}
                for row in conn.execute(
                    "SELECT platform, COUNT(*) FROM items GROUP BY platform ORDER BY COUNT(*) DESC"
                ).fetchall()
            ]
            by_type = [
                {"key": row[0], "count": int(row[1])}
                for row in conn.execute(
                    "SELECT content_type, COUNT(*) FROM items GROUP BY content_type ORDER BY COUNT(*) DESC"
                ).fetchall()
            ]
            return {
                "total": total,
                "today": today,
                "by_platform": by_platform,
                "by_type": by_type,
            }
        finally:
            conn.close()

    def count_today(self) -> int:
        conn = self._connect()
        try:
            return int(
                conn.execute("SELECT COUNT(*) FROM items WHERE DATE(captured_at)=DATE('now', 'localtime')").fetchone()[0]
            )
        finally:
            conn.close()

    def all_items(self) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute("SELECT * FROM items ORDER BY captured_at DESC").fetchall()
            return [self._row_to_item(row) for row in rows]
        finally:
            conn.close()

    def get_items_by_ids(self, ids: list[str]) -> dict[str, dict[str, Any]]:
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        conn = self._connect()
        try:
            rows = conn.execute(f"SELECT * FROM items WHERE id IN ({placeholders})", ids).fetchall()
            out: dict[str, dict[str, Any]] = {}
            for row in rows:
                item = self._row_to_item(row)
                if item:
                    out[item["id"]] = item
            return out
        finally:
            conn.close()

    def delete_all(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM items")
                conn.execute("DELETE FROM items_fts")
                conn.commit()
            finally:
                conn.close()

    @staticmethod
    def _row_to_item(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "id": row["id"],
            "url": row["url"],
            "platform": row["platform"],
            "content_type": row["content_type"],
            "text_content": row["text_content"],
            "image_urls": json.loads(row["image_urls"] or "[]"),
            "image_captions": json.loads(row["image_captions"] or "[]"),
            "image_cache_paths": json.loads(row["image_cache_paths"] or "[]"),
            "author": row["author"],
            "captured_at": row["captured_at"],
            "dwell_seconds": row["dwell_seconds"] or 0.0,
            "embedding_done": bool(row["embedding_done"]),
            "vision_done": bool(row["vision_done"]),
            "dedupe_key": row["dedupe_key"],
        }

    @staticmethod
    def _row_to_search_dict(row: sqlite3.Row, bm25_key: str) -> dict[str, Any]:
        image_urls = json.loads(row["image_urls"] or "[]")
        cache_paths = json.loads(row["image_cache_paths"] or "[]")
        thumbnail = cache_paths[0] if cache_paths else (image_urls[0] if image_urls else None)
        return {
            "id": row["id"],
            "url": row["url"],
            "platform": row["platform"],
            "text_content": row["text_content"] or "",
            "thumbnail": thumbnail,
            "author": row["author"],
            "captured_at": row["captured_at"],
            "fts_score": float(row[bm25_key]),
        }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
