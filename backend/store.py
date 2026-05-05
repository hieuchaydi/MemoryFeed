from __future__ import annotations

import json
import sqlite3
import threading
import hashlib
import math
from datetime import date, datetime, timedelta, timezone
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

                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_captured_at ON items(captured_at);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_platform ON items(platform);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_type ON items(content_type);")
                self._ensure_column(conn, "items", "starred", "INTEGER DEFAULT 0")
                self._ensure_column(conn, "items", "note", "TEXT")
                self._ensure_column(conn, "items", "tags", "TEXT")
                self._ensure_column(conn, "items", "heat", "REAL DEFAULT 1.0")
                self._ensure_column(conn, "items", "last_surfaced", "TEXT")
                self._ensure_column(conn, "items", "surfaced_count", "INTEGER DEFAULT 0")
                self._ensure_column(conn, "items", "archived_at", "TEXT")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_heat ON items(heat);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_archived_at ON items(archived_at);")
                conn.commit()
            finally:
                conn.close()

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table: str, col_name: str, col_type: str) -> None:
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        names = {row[1] for row in cols}
        if col_name not in names:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")

    def insert_item(self, item: dict[str, Any]) -> tuple[bool, str | None]:
        item = self._normalize_item_for_insert(item)
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    """
                    INSERT OR IGNORE INTO items (
                        id, url, platform, content_type, text_content, image_urls,
                        image_captions, author, captured_at, dwell_seconds,
                        embedding_done, vision_done, dedupe_key, image_cache_paths,
                        starred, note, tags, heat, last_surfaced, surfaced_count, archived_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        int(bool(item.get("starred", 0))),
                        item.get("note"),
                        json.dumps(item.get("tags", []), ensure_ascii=False),
                        float(item.get("heat", 1.0)),
                        item.get("last_surfaced"),
                        int(item.get("surfaced_count", 0) or 0),
                        item.get("archived_at"),
                    ),
                )
                conn.commit()

                if cur.rowcount == 1:
                    return True, item["id"]

                existing = conn.execute(
                    "SELECT id FROM items WHERE dedupe_key = ? LIMIT 1", (item["dedupe_key"],)
                ).fetchone()
                return False, str(existing["id"]) if existing else None
            finally:
                conn.close()

    @staticmethod
    def _normalize_item_for_insert(item: dict[str, Any]) -> dict[str, Any]:
        out = dict(item)
        out.setdefault("image_urls", [])
        out.setdefault("image_captions", [])
        out.setdefault("image_cache_paths", [])
        out.setdefault("author", None)
        out.setdefault("dwell_seconds", 0.0)
        out.setdefault("embedding_done", 0)
        out.setdefault("vision_done", 1 if not out.get("image_urls") else 0)
        out.setdefault("starred", 0)
        out.setdefault("note", None)
        out.setdefault("tags", [])
        out.setdefault("heat", 1.0)
        out.setdefault("last_surfaced", None)
        out.setdefault("surfaced_count", 0)
        out.setdefault("archived_at", None)
        out.setdefault("captured_at", datetime.now(timezone.utc).isoformat())
        out.setdefault("content_type", "post")
        out.setdefault("platform", "unknown")
        out.setdefault("text_content", "")

        if not out.get("dedupe_key"):
            seed = f"{out.get('url', '')}|{str(out.get('text_content', ''))[:100]}".encode(
                "utf-8", errors="ignore"
            )
            out["dedupe_key"] = hashlib.sha256(seed).hexdigest()
        return out

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

    def update_item_metadata(
        self,
        item_id: str,
        starred: bool | None = None,
        note: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any] | None:
        updates: list[str] = []
        params: list[Any] = []
        if starred is not None:
            updates.append("starred = ?")
            params.append(1 if starred else 0)
        if note is not None:
            updates.append("note = ?")
            params.append(note)
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags, ensure_ascii=False))
        if not updates:
            return self.get_item(item_id)

        params.append(item_id)
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(f"UPDATE items SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()
            finally:
                conn.close()
        return self.get_item(item_id)

    def apply_heat_decay(self, decay: float = 0.95, idle_days: int = 7) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=idle_days)
        today = date.today().isoformat()
        with self._lock:
            conn = self._connect()
            try:
                last_decay = conn.execute(
                    "SELECT value FROM meta WHERE key = 'last_heat_decay_date'"
                ).fetchone()
                if last_decay and last_decay["value"] == today:
                    return 0

                cur = conn.execute(
                    """
                    UPDATE items
                    SET heat = MAX(0.05, COALESCE(heat, 1.0) * ?)
                    WHERE archived_at IS NULL
                      AND DATETIME(COALESCE(last_surfaced, captured_at)) < DATETIME(?)
                    """,
                    (float(decay), cutoff.isoformat()),
                )
                conn.execute(
                    """
                    INSERT INTO meta(key, value)
                    VALUES('last_heat_decay_date', ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (today,),
                )
                conn.commit()
                return int(cur.rowcount or 0)
            finally:
                conn.close()

    def bump_heat(
        self,
        item_id: str,
        amount: float = 0.35,
        mark_surfaced: bool = False,
        cap: float = 10.0,
    ) -> dict[str, Any] | None:
        updates = ["heat = MIN(?, COALESCE(heat, 1.0) + ?)"]
        params: list[Any] = [float(cap), float(amount)]
        if mark_surfaced:
            updates.append("last_surfaced = ?")
            updates.append("surfaced_count = COALESCE(surfaced_count, 0) + 1")
            params.append(now_iso())
        params.append(item_id)

        with self._lock:
            conn = self._connect()
            try:
                conn.execute(f"UPDATE items SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()
            finally:
                conn.close()
        return self.get_item(item_id)

    def mark_items_surfaced(self, item_ids: list[str]) -> int:
        ids = [item_id for item_id in item_ids if item_id]
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        params: list[Any] = [now_iso(), *ids]
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    f"""
                    UPDATE items
                    SET last_surfaced = ?,
                        surfaced_count = COALESCE(surfaced_count, 0) + 1,
                        heat = MIN(10.0, COALESCE(heat, 1.0) + 0.05)
                    WHERE id IN ({placeholders})
                    """,
                    params,
                )
                conn.commit()
                return int(cur.rowcount or 0)
            finally:
                conn.close()

    def archive_items(self, item_ids: list[str]) -> int:
        ids = [item_id for item_id in item_ids if item_id]
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        params: list[Any] = [now_iso(), *ids]
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    f"UPDATE items SET archived_at = ? WHERE id IN ({placeholders})",
                    params,
                )
                conn.commit()
                return int(cur.rowcount or 0)
            finally:
                conn.close()

    def smart_feed(self, limit: int = 20, mode: str = "default") -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT *
                FROM items
                WHERE archived_at IS NULL
                ORDER BY COALESCE(heat, 1.0) DESC, captured_at DESC
                LIMIT ?
                """,
                (max(limit * 12, 120),),
            ).fetchall()
            items = [self._row_to_item(row) for row in rows]
        finally:
            conn.close()

        ranked = []
        for item in items:
            if not item:
                continue
            surface_score, reason, needs_review = _feed_score(item, mode)
            out = dict(item)
            out["surface_score"] = round(surface_score, 6)
            out["surface_reason"] = reason
            out["needs_review"] = needs_review
            out["text_excerpt"] = (out.get("text_content") or "").strip()[:220]
            image_urls = out.get("image_urls") or []
            cache_paths = out.get("image_cache_paths") or []
            out["thumbnail"] = _normalize_thumbnail(cache_paths[0] if cache_paths else (image_urls[0] if image_urls else None))
            ranked.append(out)

        ranked.sort(key=lambda item: item["surface_score"], reverse=True)
        return ranked[:limit]

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

    def list_items(
        self,
        limit: int = 50,
        offset: int = 0,
        platform: str | None = None,
        starred_only: bool = False,
    ) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            where = []
            params: list[Any] = []
            if platform:
                where.append("platform = ?")
                params.append(platform)
            if starred_only:
                where.append("starred = 1")
            clause = f"WHERE {' AND '.join(where)}" if where else ""
            params.extend([limit, offset])
            rows = conn.execute(
                f"SELECT * FROM items {clause} ORDER BY captured_at DESC LIMIT ? OFFSET ?",
                params,
            ).fetchall()
            return [self._row_to_item(row) for row in rows]
        finally:
            conn.close()

    def export_items(self) -> list[dict[str, Any]]:
        return self.all_items()

    def import_items(self, items: list[dict[str, Any]]) -> dict[str, int]:
        inserted = 0
        duplicates = 0
        for item in items:
            ok, _ = self.insert_item(item)
            if ok:
                inserted += 1
            else:
                duplicates += 1
        return {"inserted": inserted, "duplicates": duplicates}

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
            "starred": bool(row["starred"]) if "starred" in row.keys() else False,
            "note": row["note"] if "note" in row.keys() else None,
            "tags": json.loads(row["tags"] or "[]") if "tags" in row.keys() and row["tags"] else [],
            "heat": float(row["heat"]) if "heat" in row.keys() and row["heat"] is not None else 1.0,
            "last_surfaced": row["last_surfaced"] if "last_surfaced" in row.keys() else None,
            "surfaced_count": int(row["surfaced_count"] or 0) if "surfaced_count" in row.keys() else 0,
            "archived_at": row["archived_at"] if "archived_at" in row.keys() else None,
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
            "starred": bool(row["starred"]) if "starred" in row.keys() else False,
            "heat": float(row["heat"]) if "heat" in row.keys() and row["heat"] is not None else 1.0,
        }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _feed_score(item: dict[str, Any], mode: str) -> tuple[float, str, bool]:
    now = datetime.now(timezone.utc)
    captured_at = _parse_iso(item.get("captured_at")) or now
    last_surfaced = _parse_iso(item.get("last_surfaced"))
    age_days = max(0.0, (now - captured_at).total_seconds() / 86400.0)
    untouched_days = max(0.0, (now - (last_surfaced or captured_at)).total_seconds() / 86400.0)

    heat = max(0.05, float(item.get("heat") or 1.0))
    recency = 1.0 / (1.0 + age_days / 14.0)
    dwell_bonus = min(0.25, float(item.get("dwell_seconds") or 0.0) / 120.0)
    star_bonus = 0.45 if item.get("starred") else 0.0
    resurfacing_gap = 0.18 if age_days >= 3 and untouched_days >= 14 else 0.0
    mode_bonus = _mode_bonus(item, mode)

    score = heat * 0.68 + recency * 0.2 + dwell_bonus + star_bonus + resurfacing_gap + mode_bonus
    reason = "hot_memory"
    if age_days >= 30 and untouched_days >= 30:
        reason = "review_or_archive"
    elif resurfacing_gap:
        reason = "worth_resurfacing"
    elif item.get("starred"):
        reason = "starred_memory"
    elif age_days < 2:
        reason = "recent_capture"

    needs_review = age_days >= 30 and untouched_days >= 30 and heat < 0.8
    return score, reason, needs_review


def _mode_bonus(item: dict[str, Any], mode: str) -> float:
    content_type = str(item.get("content_type") or "")
    text = str(item.get("text_content") or "").lower()
    if mode == "focus":
        technical_tokens = ("api", "docker", "kubernetes", "database", "architecture", "python", "typescript")
        return 0.2 if content_type in {"article", "post"} and any(t in text for t in technical_tokens) else 0.05
    if mode == "light":
        return 0.18 if content_type in {"video", "image"} else 0.0
    if mode == "explore":
        surfaced_count = int(item.get("surfaced_count") or 0)
        return max(0.0, 0.16 - math.log1p(surfaced_count) * 0.04)
    return 0.0


def _normalize_thumbnail(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith(("http://", "https://", "/images/")):
        return value
    p = Path(value)
    try:
        if p.exists() and p.parent.resolve() == IMAGE_CACHE_DIR.resolve():
            return f"/images/{p.name}"
    except Exception:
        return None
    return None
