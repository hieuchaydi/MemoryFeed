from __future__ import annotations

import json
import sqlite3
import threading
import hashlib
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.dedupe import dedupe_bucket, find_semantic_duplicate
from backend.feed import score_item
from backend.memory_graph import (
    cluster_id_for_item,
    extract_entities,
    extract_topics,
    infer_memory_relationships,
    infer_url_domain,
    persist_relationships,
    semantic_group_for_item,
)
from backend.migrate import run_migrations_on_connection
from backend.ranking import update_item_scores
from backend.retention import run_retention_policy
from backend.runtime_config import load_runtime_config
from backend.safety import detect_prompt_injection
from backend.url_normalization import canonicalize_url, extract_post_id

DATA_DIR = Path(os.getenv("MEMORYFEED_DATA_DIR", str(Path.home() / ".memoryfeed"))).expanduser()
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
                self._ensure_column(conn, "items", "canonical_url", "TEXT")
                self._ensure_column(conn, "items", "post_id", "TEXT")
                self._ensure_column(conn, "items", "media_urls", "TEXT")
                self._ensure_column(conn, "items", "author_name", "TEXT")
                self._ensure_column(conn, "items", "author_handle", "TEXT")
                self._ensure_column(conn, "items", "thumbnail_url", "TEXT")
                self._ensure_column(conn, "items", "source_context", "TEXT")
                self._ensure_column(conn, "items", "quality_flags", "TEXT")
                self._ensure_column(conn, "items", "capture_debug", "TEXT")
                self._ensure_column(conn, "items", "url_domain", "TEXT")
                self._ensure_column(conn, "items", "related_topics", "TEXT")
                self._ensure_column(conn, "items", "related_entities", "TEXT")
                self._ensure_column(conn, "items", "cluster_id", "TEXT")
                self._ensure_column(conn, "items", "semantic_group", "TEXT")
                self._ensure_column(conn, "items", "importance_score", "REAL DEFAULT 0.0")
                self._ensure_column(conn, "items", "resurfacing_score", "REAL DEFAULT 0.0")
                self._ensure_column(conn, "items", "recency_score", "REAL DEFAULT 0.0")
                self._ensure_column(conn, "items", "recurrence_score", "REAL DEFAULT 0.0")
                self._ensure_column(conn, "items", "ranking_debug", "TEXT")
                self._ensure_column(conn, "items", "embedding_skipped_reason", "TEXT")
                self._ensure_column(conn, "items", "suspicious_prompt_content", "INTEGER DEFAULT 0")
                self._ensure_column(conn, "items", "safety_signals", "TEXT")
                self._ensure_column(conn, "items", "archive_reason", "TEXT")
                self._ensure_column(conn, "items", "capture_confidence", "REAL DEFAULT 0.0")
                self._ensure_column(conn, "items", "confidence_reasons", "TEXT")
                self._ensure_column(conn, "items", "capture_method", "TEXT")
                self._ensure_column(conn, "items", "extractor_version", "TEXT")
                self._ensure_column(conn, "items", "capture_source", "TEXT")
                self._ensure_column(conn, "items", "replay_source", "TEXT")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_heat ON items(heat);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_archived_at ON items(archived_at);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_canonical_url ON items(canonical_url);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_post_id ON items(post_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_url_domain ON items(url_domain);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_cluster_id ON items(cluster_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_semantic_group ON items(semantic_group);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_importance_score ON items(importance_score);")
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
                    )
                    """
                )
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
                    )
                    """
                )
                run_migrations_on_connection(conn)
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
                cfg = load_runtime_config()
                existing_fingerprint = conn.execute(
                    "SELECT id FROM items WHERE dedupe_key = ? LIMIT 1",
                    (item["dedupe_key"],),
                ).fetchone()
                if existing_fingerprint:
                    conn.execute(
                        """
                        UPDATE items
                        SET recurrence_score = MIN(1.0, COALESCE(recurrence_score, 0.0) + 0.02)
                        WHERE id = ?
                        """,
                        (str(existing_fingerprint["id"]),),
                    )
                    conn.commit()
                    return False, str(existing_fingerprint["id"])

                if cfg.memory_semantic_dedupe:
                    match = find_semantic_duplicate(conn, item, threshold=cfg.memory_dedupe_similarity_threshold)
                    if match:
                        conn.execute(
                            """
                            UPDATE items
                            SET recurrence_score = MIN(1.0, COALESCE(recurrence_score, 0.0) + 0.03),
                                ranking_debug = COALESCE(ranking_debug, '{}')
                            WHERE id = ?
                            """,
                            (match.duplicate_id,),
                        )
                        conn.commit()
                        return False, match.duplicate_id

                cur = conn.execute(
                    """
                    INSERT OR IGNORE INTO items (
                        id, url, platform, content_type, text_content, image_urls,
                        image_captions, author, captured_at, dwell_seconds,
                        embedding_done, vision_done, dedupe_key, image_cache_paths,
                        starred, note, tags, heat, last_surfaced, surfaced_count, archived_at,
                        canonical_url, post_id, media_urls, author_name, author_handle,
                        thumbnail_url, source_context, quality_flags, capture_debug, url_domain,
                        related_topics, related_entities, cluster_id, semantic_group,
                        importance_score, resurfacing_score, recency_score, recurrence_score,
                        ranking_debug, embedding_skipped_reason, suspicious_prompt_content, safety_signals,
                        archive_reason, capture_confidence, confidence_reasons, capture_method,
                        extractor_version, capture_source, replay_source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        item.get("canonical_url"),
                        item.get("post_id"),
                        json.dumps(item.get("media_urls", []), ensure_ascii=False),
                        item.get("author_name"),
                        item.get("author_handle"),
                        item.get("thumbnail_url"),
                        item.get("source_context"),
                        json.dumps(item.get("quality_flags", []), ensure_ascii=False),
                        json.dumps(item.get("capture_debug", {}), ensure_ascii=False),
                        item.get("url_domain"),
                        json.dumps(item.get("related_topics", []), ensure_ascii=False),
                        json.dumps(item.get("related_entities", []), ensure_ascii=False),
                        item.get("cluster_id"),
                        item.get("semantic_group"),
                        float(item.get("importance_score", 0.0) or 0.0),
                        float(item.get("resurfacing_score", 0.0) or 0.0),
                        float(item.get("recency_score", 0.0) or 0.0),
                        float(item.get("recurrence_score", 0.0) or 0.0),
                        json.dumps(item.get("ranking_debug", {}), ensure_ascii=False),
                        item.get("embedding_skipped_reason"),
                        int(bool(item.get("suspicious_prompt_content", False))),
                        json.dumps(item.get("safety_signals", []), ensure_ascii=False),
                        item.get("archive_reason"),
                        float(item.get("capture_confidence", 0.0) or 0.0),
                        json.dumps(item.get("confidence_reasons", []), ensure_ascii=False),
                        item.get("capture_method"),
                        item.get("extractor_version"),
                        item.get("capture_source"),
                        item.get("replay_source"),
                    ),
                )

                if cur.rowcount == 1:
                    self._refresh_item_derived_fields(conn, item["id"], seed_item=item)
                    self._run_retention_if_enabled(conn)
                    conn.commit()
                    return True, item["id"]

                existing = conn.execute(
                    "SELECT id FROM items WHERE dedupe_key = ? LIMIT 1", (item["dedupe_key"],)
                ).fetchone()
                if existing:
                    conn.execute(
                        """
                        UPDATE items
                        SET recurrence_score = MIN(1.0, COALESCE(recurrence_score, 0.0) + 0.02)
                        WHERE id = ?
                        """,
                        (str(existing["id"]),),
                    )
                conn.commit()
                return False, str(existing["id"]) if existing else None
            finally:
                conn.close()

    @staticmethod
    def _normalize_item_for_insert(item: dict[str, Any]) -> dict[str, Any]:
        out = dict(item)
        out.setdefault("image_urls", [])
        out.setdefault("media_urls", out.get("image_urls", []))
        out.setdefault("image_captions", [])
        out.setdefault("image_cache_paths", [])
        out.setdefault("author", None)
        out.setdefault("author_name", out.get("author"))
        out.setdefault("author_handle", None)
        out.setdefault("canonical_url", out.get("url"))
        out.setdefault("post_id", None)
        out.setdefault("thumbnail_url", None)
        out.setdefault("source_context", None)
        out.setdefault("quality_flags", [])
        out.setdefault("capture_debug", {})
        out.setdefault("url_domain", infer_url_domain(out.get("canonical_url") or out.get("url")))
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
        out.setdefault("archive_reason", None)
        out.setdefault("captured_at", datetime.now(timezone.utc).isoformat())
        out.setdefault("content_type", "post")
        out.setdefault("platform", "unknown")
        out.setdefault("text_content", "")
        out.setdefault("related_topics", [])
        out.setdefault("related_entities", [])
        out.setdefault("cluster_id", None)
        out.setdefault("semantic_group", None)
        out.setdefault("importance_score", 0.0)
        out.setdefault("resurfacing_score", 0.0)
        out.setdefault("recency_score", 0.0)
        out.setdefault("recurrence_score", 0.0)
        out.setdefault("ranking_debug", {})
        out.setdefault("embedding_skipped_reason", None)
        out.setdefault("suspicious_prompt_content", False)
        out.setdefault("safety_signals", [])

        canonical = str(out.get("canonical_url") or out.get("url") or "").strip()
        platform_name = str(out.get("platform") or "unknown")
        if canonical:
            out["canonical_url"] = canonicalize_url(canonical, platform=platform_name) or canonical
        if not out.get("post_id"):
            out["post_id"] = extract_post_id(str(out.get("canonical_url") or ""), platform=platform_name)
        out.setdefault("capture_confidence", 0.0)
        out.setdefault("confidence_reasons", [])
        out.setdefault("capture_method", "import")
        out.setdefault("extractor_version", "legacy")
        out.setdefault("capture_source", "import")
        out.setdefault("replay_source", None)

        if not out.get("dedupe_key"):
            canonical = out.get("canonical_url") or out.get("url") or ""
            author_name = out.get("author_name") or out.get("author") or ""
            captured_at = out.get("captured_at") or now_iso()
            try:
                bucket = dedupe_bucket(str(captured_at), platform=str(out.get("platform") or "unknown"))
            except Exception:
                bucket = str(captured_at)[:13]
            seed = f"{canonical}|{str(out.get('text_content', ''))[:240]}|{author_name[:100]}|{bucket}".encode(
                "utf-8", errors="ignore"
            )
            out["dedupe_key"] = hashlib.sha256(seed).hexdigest()
        return out

    def _refresh_item_derived_fields(
        self,
        conn: sqlite3.Connection,
        item_id: str,
        seed_item: dict[str, Any] | None = None,
    ) -> None:
        item = dict(seed_item or {})
        if not item:
            row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
            parsed = self._row_to_item(row)
            if not parsed:
                return
            item = parsed

        text_blob = " \n ".join(
            [
                str(item.get("text_content") or ""),
                " ".join(item.get("image_captions") or []),
                str(item.get("note") or ""),
            ]
        ).strip()
        topics = extract_topics(text_blob, tags=item.get("tags") or [])
        entities = extract_entities(text_blob, author=item.get("author_name") or item.get("author"))
        item["related_topics"] = topics
        item["related_entities"] = entities
        item["url_domain"] = infer_url_domain(item.get("canonical_url") or item.get("url"))
        item["semantic_group"] = item.get("semantic_group") or semantic_group_for_item(item)
        item["cluster_id"] = item.get("cluster_id") or cluster_id_for_item(item)

        safety = detect_prompt_injection(text_blob)
        item["suspicious_prompt_content"] = bool(safety["suspicious"])
        item["safety_signals"] = list(safety["signals"])

        relations, inferred_topics, inferred_entities = infer_memory_relationships(conn, item)
        if inferred_topics:
            item["related_topics"] = inferred_topics
        if inferred_entities:
            item["related_entities"] = inferred_entities
        item["semantic_group"] = semantic_group_for_item(item)
        item["cluster_id"] = cluster_id_for_item(item)

        conn.execute(
            """
            UPDATE items
            SET url_domain = ?,
                related_topics = ?,
                related_entities = ?,
                cluster_id = ?,
                semantic_group = ?,
                suspicious_prompt_content = ?,
                safety_signals = ?
            WHERE id = ?
            """,
            (
                item.get("url_domain"),
                json.dumps(item.get("related_topics", []), ensure_ascii=False),
                json.dumps(item.get("related_entities", []), ensure_ascii=False),
                item.get("cluster_id"),
                item.get("semantic_group"),
                int(bool(item.get("suspicious_prompt_content"))),
                json.dumps(item.get("safety_signals", []), ensure_ascii=False),
                item_id,
            ),
        )
        persist_relationships(conn, item_id, relations)

        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        parsed = self._row_to_item(row)
        if parsed:
            update_item_scores(conn, item_id, parsed)

    def _run_retention_if_enabled(self, conn: sqlite3.Connection) -> None:
        cfg = load_runtime_config()
        if not cfg.memory_auto_archive:
            return
        today = date.today().isoformat()
        last_row = conn.execute("SELECT value FROM meta WHERE key = 'last_retention_run'").fetchone()
        if last_row and str(last_row["value"]) == today:
            return
        report = run_retention_policy(
            conn,
            retention_days=cfg.memory_retention_days,
            low_score_threshold=cfg.memory_archive_low_score_threshold,
            auto_archive=cfg.memory_auto_archive,
        )
        conn.execute(
            """
            INSERT INTO meta(key, value)
            VALUES('last_retention_run', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (today,),
        )
        if report.get("archived", 0):
            conn.execute(
                """
                INSERT INTO meta(key, value)
                VALUES('last_retention_archive_count', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(int(report["archived"])),),
            )

    def get_item(self, item_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
            return self._row_to_item(row) if row else None
        finally:
            conn.close()

    def latest_item(self) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM items ORDER BY captured_at DESC, rowid DESC LIMIT 1").fetchone()
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
                self._refresh_item_derived_fields(conn, item_id)
                conn.commit()
            finally:
                conn.close()

    def mark_embedding_done(self, item_id: str) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("UPDATE items SET embedding_done = 1, embedding_skipped_reason = NULL WHERE id = ?", (item_id,))
                conn.commit()
            finally:
                conn.close()

    def mark_embedding_skipped(self, item_id: str, reason: str) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    UPDATE items
                    SET embedding_done = 1,
                        embedding_skipped_reason = ?
                    WHERE id = ?
                    """,
                    (reason[:240], item_id),
                )
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
                self._refresh_item_derived_fields(conn, item_id)
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
                row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
                parsed = self._row_to_item(row)
                if parsed:
                    update_item_scores(conn, item_id, parsed)
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
                for item_id in ids:
                    row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
                    parsed = self._row_to_item(row)
                    if parsed:
                        update_item_scores(conn, item_id, parsed)
                conn.commit()
                return int(cur.rowcount or 0)
            finally:
                conn.close()

    def archive_items(self, item_ids: list[str], reason: str = "manual_archive") -> int:
        ids = [item_id for item_id in item_ids if item_id]
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        params: list[Any] = [now_iso(), reason[:240], *ids]
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    f"UPDATE items SET archived_at = ?, archive_reason = ? WHERE id IN ({placeholders})",
                    params,
                )
                conn.commit()
                return int(cur.rowcount or 0)
            finally:
                conn.close()

    def unarchive_items(self, item_ids: list[str]) -> int:
        ids = [item_id for item_id in item_ids if item_id]
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    f"UPDATE items SET archived_at = NULL, archive_reason = NULL WHERE id IN ({placeholders})",
                    ids,
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
            surface_score, reason, needs_review = score_item(item, mode)
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
                    items.starred,
                    items.heat,
                    items.importance_score,
                    items.resurfacing_score,
                    items.recency_score,
                    items.recurrence_score,
                    items.capture_confidence,
                    items.suspicious_prompt_content,
                    items.embedding_skipped_reason,
                    bm25(items_fts) AS bm25_score
                FROM items_fts
                JOIN items ON items_fts.rowid = items.rowid
                WHERE items_fts MATCH ?
                  AND items.archived_at IS NULL
                  {where}
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
            archived_total = int(conn.execute("SELECT COUNT(*) FROM items WHERE archived_at IS NOT NULL").fetchone()[0])
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
                "archived_total": archived_total,
                "active_total": max(0, total - archived_total),
                "today": today,
                "by_platform": by_platform,
                "by_type": by_type,
                "schema_version": self.schema_version(),
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
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            where = []
            params: list[Any] = []
            if not include_archived:
                where.append("archived_at IS NULL")
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

    def schema_version(self) -> int:
        conn = self._connect()
        try:
            row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
            if not row:
                return 0
            try:
                return int(str(row["value"]))
            except Exception:
                return 0
        finally:
            conn.close()

    def migrate(self, target_version: int | None = None) -> dict[str, Any]:
        with self._lock:
            conn = self._connect()
            try:
                report = run_migrations_on_connection(conn, target_version=target_version)
                conn.commit()
                return report
            finally:
                conn.close()

    def related_links(self, item_id: str, limit: int = 20) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT from_item_id, to_item_id, relation_type, weight, reason, created_at
                FROM memory_links
                WHERE from_item_id = ?
                ORDER BY weight DESC, created_at DESC
                LIMIT ?
                """,
                (item_id, max(1, limit)),
            ).fetchall()
            return [
                {
                    "from_item_id": row["from_item_id"],
                    "to_item_id": row["to_item_id"],
                    "relation_type": row["relation_type"],
                    "weight": float(row["weight"] or 0.0),
                    "reason": row["reason"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
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
                conn.execute("DELETE FROM memory_links")
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
            "media_urls": json.loads(row["media_urls"] or "[]") if "media_urls" in row.keys() and row["media_urls"] else json.loads(row["image_urls"] or "[]"),
            "image_captions": json.loads(row["image_captions"] or "[]"),
            "image_cache_paths": json.loads(row["image_cache_paths"] or "[]"),
            "author": row["author"],
            "author_name": row["author_name"] if "author_name" in row.keys() and row["author_name"] is not None else row["author"],
            "author_handle": row["author_handle"] if "author_handle" in row.keys() else None,
            "captured_at": row["captured_at"],
            "dwell_seconds": row["dwell_seconds"] or 0.0,
            "embedding_done": bool(row["embedding_done"]),
            "vision_done": bool(row["vision_done"]),
            "dedupe_key": row["dedupe_key"],
            "canonical_url": row["canonical_url"] if "canonical_url" in row.keys() and row["canonical_url"] else row["url"],
            "post_id": row["post_id"] if "post_id" in row.keys() else None,
            "thumbnail_url": row["thumbnail_url"] if "thumbnail_url" in row.keys() else None,
            "source_context": row["source_context"] if "source_context" in row.keys() else None,
            "quality_flags": json.loads(row["quality_flags"] or "[]") if "quality_flags" in row.keys() and row["quality_flags"] else [],
            "capture_debug": json.loads(row["capture_debug"] or "{}") if "capture_debug" in row.keys() and row["capture_debug"] else {},
            "capture_confidence": float(row["capture_confidence"]) if "capture_confidence" in row.keys() and row["capture_confidence"] is not None else 0.0,
            "confidence_reasons": json.loads(row["confidence_reasons"] or "[]") if "confidence_reasons" in row.keys() and row["confidence_reasons"] else [],
            "capture_method": row["capture_method"] if "capture_method" in row.keys() else None,
            "extractor_version": row["extractor_version"] if "extractor_version" in row.keys() else None,
            "capture_source": row["capture_source"] if "capture_source" in row.keys() else None,
            "replay_source": row["replay_source"] if "replay_source" in row.keys() else None,
            "url_domain": row["url_domain"] if "url_domain" in row.keys() else infer_url_domain(row["canonical_url"] if "canonical_url" in row.keys() else row["url"]),
            "related_topics": json.loads(row["related_topics"] or "[]") if "related_topics" in row.keys() and row["related_topics"] else [],
            "related_entities": json.loads(row["related_entities"] or "[]") if "related_entities" in row.keys() and row["related_entities"] else [],
            "cluster_id": row["cluster_id"] if "cluster_id" in row.keys() else None,
            "semantic_group": row["semantic_group"] if "semantic_group" in row.keys() else None,
            "importance_score": float(row["importance_score"]) if "importance_score" in row.keys() and row["importance_score"] is not None else 0.0,
            "resurfacing_score": float(row["resurfacing_score"]) if "resurfacing_score" in row.keys() and row["resurfacing_score"] is not None else 0.0,
            "recency_score": float(row["recency_score"]) if "recency_score" in row.keys() and row["recency_score"] is not None else 0.0,
            "recurrence_score": float(row["recurrence_score"]) if "recurrence_score" in row.keys() and row["recurrence_score"] is not None else 0.0,
            "ranking_debug": json.loads(row["ranking_debug"] or "{}") if "ranking_debug" in row.keys() and row["ranking_debug"] else {},
            "embedding_skipped_reason": row["embedding_skipped_reason"] if "embedding_skipped_reason" in row.keys() else None,
            "suspicious_prompt_content": bool(row["suspicious_prompt_content"]) if "suspicious_prompt_content" in row.keys() else False,
            "safety_signals": json.loads(row["safety_signals"] or "[]") if "safety_signals" in row.keys() and row["safety_signals"] else [],
            "starred": bool(row["starred"]) if "starred" in row.keys() else False,
            "note": row["note"] if "note" in row.keys() else None,
            "tags": json.loads(row["tags"] or "[]") if "tags" in row.keys() and row["tags"] else [],
            "heat": float(row["heat"]) if "heat" in row.keys() and row["heat"] is not None else 1.0,
            "last_surfaced": row["last_surfaced"] if "last_surfaced" in row.keys() else None,
            "surfaced_count": int(row["surfaced_count"] or 0) if "surfaced_count" in row.keys() else 0,
            "archived_at": row["archived_at"] if "archived_at" in row.keys() else None,
            "archive_reason": row["archive_reason"] if "archive_reason" in row.keys() else None,
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
            "importance_score": float(row["importance_score"]) if "importance_score" in row.keys() and row["importance_score"] is not None else 0.0,
            "resurfacing_score": float(row["resurfacing_score"]) if "resurfacing_score" in row.keys() and row["resurfacing_score"] is not None else 0.0,
            "recency_score": float(row["recency_score"]) if "recency_score" in row.keys() and row["recency_score"] is not None else 0.0,
            "recurrence_score": float(row["recurrence_score"]) if "recurrence_score" in row.keys() and row["recurrence_score"] is not None else 0.0,
            "capture_confidence": float(row["capture_confidence"]) if "capture_confidence" in row.keys() and row["capture_confidence"] is not None else 0.0,
            "suspicious_prompt_content": bool(row["suspicious_prompt_content"]) if "suspicious_prompt_content" in row.keys() else False,
            "embedding_skipped_reason": row["embedding_skipped_reason"] if "embedding_skipped_reason" in row.keys() else None,
        }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
