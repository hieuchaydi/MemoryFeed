from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
import hashlib
import math
import os
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.memory_graph import derive_graph_fields
from backend.db_connection import connect_db
from backend.noise import classify_noise
from backend.crypto_at_rest import AtRestCrypto
from backend.retention import compute_decay
from backend.runtime_config import load_runtime_config
from backend.safety import assess_prompt_risk, classify_sensitivity
from backend.dedupe import semantic_similarity

DATA_DIR = Path(os.getenv("MEMORYFEED_DATA_DIR", str(Path.home() / ".memoryfeed"))).expanduser()
DB_PATH = DATA_DIR / "memoryfeed.db"
LANCEDB_DIR = DATA_DIR / "lancedb"
IMAGE_CACHE_DIR = DATA_DIR / "images"
IMAGE_ENCRYPTED_DIR = DATA_DIR / "images_enc"
logger = logging.getLogger(__name__)


class Store:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        LANCEDB_DIR.mkdir(parents=True, exist_ok=True)
        IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        IMAGE_ENCRYPTED_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._crypto = AtRestCrypto()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = connect_db(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def ping(self) -> bool:
        conn = self._connect()
        try:
            row = conn.execute("SELECT 1 as ok").fetchone()
            return bool(row and int(row["ok"]) == 1)
        except Exception:
            return False
        finally:
            conn.close()

    def _maybe_encrypt_text(self, value: Any, aad: bytes) -> str | None:
        if value is None:
            return None
        text = str(value)
        if not self._crypto.enabled:
            return text
        try:
            return self._crypto.encrypt_text(text, aad=aad)
        except Exception:
            return text

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
                    CREATE TABLE IF NOT EXISTS job_dead_letters (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        queue_name TEXT NOT NULL,
                        item_id TEXT,
                        attempt INTEGER DEFAULT 1,
                        error TEXT,
                        payload TEXT,
                        created_at TEXT NOT NULL
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
                self._ensure_column(conn, "items", "capture_confidence", "REAL DEFAULT 1.0")
                self._ensure_column(conn, "items", "noise_score", "REAL DEFAULT 0.0")
                self._ensure_column(conn, "items", "low_signal_reason", "TEXT")
                self._ensure_column(conn, "items", "decay_score", "REAL DEFAULT 0.0")
                self._ensure_column(conn, "items", "aging_state", "TEXT DEFAULT 'active'")
                self._ensure_column(conn, "items", "related_topics", "TEXT")
                self._ensure_column(conn, "items", "related_entities", "TEXT")
                self._ensure_column(conn, "items", "semantic_group", "TEXT")
                self._ensure_column(conn, "items", "prompt_risk_score", "REAL DEFAULT 0.0")
                self._ensure_column(conn, "items", "prompt_risk_reason", "TEXT")
                self._ensure_column(conn, "items", "sensitivity_level", "TEXT DEFAULT 'none'")
                self._ensure_column(conn, "items", "sensitivity_reasons", "TEXT")
                self._ensure_column(conn, "items", "embedding_skipped", "INTEGER DEFAULT 0")
                self._ensure_column(conn, "items", "embedding_skipped_reason", "TEXT")
                self._ensure_column(conn, "items", "search_hidden", "INTEGER DEFAULT 0")
                self._ensure_column(conn, "items", "index_dirty", "INTEGER DEFAULT 1")
                self._ensure_column(conn, "items", "updated_at", "TEXT")
                self._ensure_column(conn, "items", "confidence_reasons", "TEXT")
                self._ensure_column(conn, "items", "capture_method", "TEXT")
                self._ensure_column(conn, "items", "extractor_version", "TEXT")
                self._ensure_column(conn, "items", "capture_source", "TEXT")
                self._ensure_column(conn, "items", "replay_source", "TEXT")
                self._ensure_column(conn, "items", "suspicious_prompt_content", "INTEGER DEFAULT 0")
                self._ensure_column(conn, "items", "safety_signals", "TEXT")
                self._ensure_column(conn, "items", "archive_reason", "TEXT")
                self._ensure_column(conn, "items", "importance_score", "REAL DEFAULT 0.0")
                self._ensure_column(conn, "items", "resurfacing_score", "REAL DEFAULT 0.0")
                self._ensure_column(conn, "items", "recency_score", "REAL DEFAULT 0.0")
                self._ensure_column(conn, "items", "recurrence_score", "REAL DEFAULT 0.0")
                self._ensure_column(conn, "items", "namespace", "TEXT DEFAULT 'default'")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_heat ON items(heat);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_archived_at ON items(archived_at);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_canonical_url ON items(canonical_url);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_post_id ON items(post_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_search_hidden ON items(search_hidden);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_index_dirty ON items(index_dirty);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_items_namespace ON items(namespace);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_dead_letters_queue ON job_dead_letters(queue_name);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_dead_letters_created_at ON job_dead_letters(created_at);")
                conn.commit()
            finally:
                conn.close()

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table: str, col_name: str, col_type: str) -> None:
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        names = {row[1] for row in cols}
        if col_name not in names:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")

    @contextmanager
    def _write_transaction(self):
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def insert_item(self, item: dict[str, Any]) -> tuple[bool, str | None]:
        cfg = load_runtime_config()
        if cfg.memory_semantic_dedupe:
            duplicate_id = self._find_semantic_duplicate(item)
            if duplicate_id:
                return False, duplicate_id
        return self.insert_item_atomic(item, fail_after_write=False)

    def insert_item_atomic(self, item: dict[str, Any], fail_after_write: bool = False) -> tuple[bool, str | None]:
        item = self._normalize_item_for_insert(item)
        with self._write_transaction() as conn:
            cur = conn.execute(
                    """
                    INSERT OR IGNORE INTO items (
                        id, url, platform, content_type, text_content, image_urls,
                        image_captions, author, captured_at, dwell_seconds,
                        embedding_done, vision_done, dedupe_key, image_cache_paths,
                        starred, note, tags, heat, last_surfaced, surfaced_count, archived_at,
                        canonical_url, post_id, media_urls, author_name, author_handle,
                        thumbnail_url, source_context, quality_flags, capture_debug, capture_confidence,
                        noise_score, low_signal_reason, decay_score, aging_state,
                        related_topics, related_entities, semantic_group,
                        prompt_risk_score, prompt_risk_reason,
                        sensitivity_level, sensitivity_reasons,
                        embedding_skipped, search_hidden, index_dirty, updated_at, namespace
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        self._maybe_encrypt_text(item.get("note"), aad=b"memoryfeed:note"),
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
                        self._maybe_encrypt_text(item.get("source_context"), aad=b"memoryfeed:source_context"),
                        json.dumps(item.get("quality_flags", []), ensure_ascii=False),
                        self._maybe_encrypt_text(json.dumps(item.get("capture_debug", {}), ensure_ascii=False), aad=b"memoryfeed:capture_debug"),
                        float(item.get("capture_confidence", 1.0)),
                        float(item.get("noise_score", 0.0)),
                        item.get("low_signal_reason"),
                        float(item.get("decay_score", 0.0)),
                        item.get("aging_state", "active"),
                        json.dumps(item.get("related_topics", []), ensure_ascii=False),
                        json.dumps(item.get("related_entities", []), ensure_ascii=False),
                        item.get("semantic_group"),
                        float(item.get("prompt_risk_score", 0.0)),
                        item.get("prompt_risk_reason"),
                        item.get("sensitivity_level", "none"),
                        json.dumps(item.get("sensitivity_reasons", []), ensure_ascii=False),
                        int(bool(item.get("embedding_skipped", 0))),
                        int(bool(item.get("search_hidden", 0))),
                        int(bool(item.get("index_dirty", 1))),
                        item.get("updated_at", now_iso()),
                        item.get("namespace", "default"),
                    ),
                )
            if fail_after_write:
                raise RuntimeError("simulated_atomic_failure")
            if cur.rowcount == 1:
                return True, item["id"]

            existing = conn.execute(
                "SELECT id FROM items WHERE dedupe_key = ? LIMIT 1", (item["dedupe_key"],)
            ).fetchone()
            return False, str(existing["id"]) if existing else None

    @staticmethod
    def _normalize_item_for_insert(item: dict[str, Any]) -> dict[str, Any]:
        out = dict(item)
        cfg = load_runtime_config()
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
        out.setdefault("confidence_reasons", [])
        out.setdefault("capture_method", "mutation_observer")
        out.setdefault("extractor_version", f"{out.get('platform') or 'unknown'}_v3_1")
        out.setdefault("capture_source", "timeline_scroll")
        out.setdefault("replay_source", None)
        out.setdefault("capture_confidence", _capture_confidence(out))
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
        out.setdefault("updated_at", now_iso())
        out.setdefault("content_type", "post")
        out.setdefault("platform", "unknown")
        out.setdefault("text_content", "")
        out.setdefault("namespace", cfg.memory_namespace)

        if not out.get("dedupe_key"):
            canonical = out.get("canonical_url") or out.get("url") or ""
            author_name = out.get("author_name") or out.get("author") or ""
            captured_at = out.get("captured_at") or now_iso()
            try:
                dt = datetime.fromisoformat(str(captured_at).replace("Z", "+00:00")).astimezone(timezone.utc)
                bucket = str(int(dt.timestamp() // (2 * 60 * 60)))
            except Exception:
                bucket = str(captured_at)[:13]
            seed = f"{out.get('namespace','default')}|{canonical}|{str(out.get('text_content', ''))[:240]}|{author_name[:100]}|{bucket}".encode(
                "utf-8", errors="ignore"
            )
            out["dedupe_key"] = hashlib.sha256(seed).hexdigest()

        noise_score, low_signal_reason = classify_noise(out)
        out.setdefault("noise_score", noise_score)
        out.setdefault("low_signal_reason", low_signal_reason)

        related = derive_graph_fields(out)
        out.setdefault("related_topics", related["related_topics"])
        out.setdefault("related_entities", related["related_entities"])
        out.setdefault("semantic_group", related["semantic_group"])

        prompt_risk_score, prompt_risk_reason = assess_prompt_risk(
            f"{out.get('text_content') or ''}\n{json.dumps(out.get('capture_debug') or {}, ensure_ascii=False)}"
        )
        out.setdefault("prompt_risk_score", prompt_risk_score)
        out.setdefault("prompt_risk_reason", prompt_risk_reason)
        out.setdefault("suspicious_prompt_content", bool(prompt_risk_score >= 0.4))
        safety_signals = []
        if prompt_risk_reason:
            safety_signals.append(prompt_risk_reason)
        out.setdefault("safety_signals", safety_signals)

        sensitivity_level, sensitivity_reasons = classify_sensitivity(
            str(out.get("text_content") or ""),
            str(out.get("url") or ""),
        )
        out.setdefault("sensitivity_level", sensitivity_level)
        out.setdefault("sensitivity_reasons", sensitivity_reasons)
        skip_embedding = cfg.skip_sensitive_embedding and sensitivity_level == "high"
        out.setdefault("embedding_skipped", 1 if skip_embedding else 0)
        out.setdefault("embedding_skipped_reason", f"sensitive:{','.join(sensitivity_reasons)}" if skip_embedding else None)
        out.setdefault("search_hidden", 1 if (cfg.hide_sensitive_from_search and sensitivity_level == "high") else 0)
        out.setdefault("index_dirty", 0 if skip_embedding else 1)

        decay_score, aging_state = compute_decay(out, half_life_days=cfg.decay_half_life_days)
        out.setdefault("decay_score", decay_score)
        out.setdefault("aging_state", aging_state)
        importance_score, resurfacing_score, recency_score, recurrence_score = _compute_ranking_primitives(out)
        out.setdefault("importance_score", importance_score)
        out.setdefault("resurfacing_score", resurfacing_score)
        out.setdefault("recency_score", recency_score)
        out.setdefault("recurrence_score", recurrence_score)
        if cfg.memory_auto_archive:
            _maybe_apply_auto_archive(out, cfg.memory_retention_days, cfg.memory_archive_low_score_threshold)
        # Backward-compatible storage for fields not present in older schemas.
        capture_debug = out.setdefault("capture_debug", {})
        capture_debug.setdefault("_confidence_reasons", list(out.get("confidence_reasons") or []))
        capture_debug.setdefault("_capture_method", str(out.get("capture_method") or "mutation_observer"))
        capture_debug.setdefault("_extractor_version", str(out.get("extractor_version") or "unknown_v3_1"))
        capture_debug.setdefault("_capture_source", str(out.get("capture_source") or "timeline_scroll"))
        capture_debug.setdefault("_replay_source", out.get("replay_source"))
        capture_debug.setdefault("_safety_signals", list(out.get("safety_signals") or []))
        capture_debug.setdefault("_suspicious_prompt_content", bool(out.get("suspicious_prompt_content")))
        capture_debug.setdefault("_embedding_skipped_reason", out.get("embedding_skipped_reason"))
        capture_debug.setdefault("_importance_score", float(out.get("importance_score") or 0.0))
        capture_debug.setdefault("_resurfacing_score", float(out.get("resurfacing_score") or 0.0))
        capture_debug.setdefault("_recency_score", float(out.get("recency_score") or 0.0))
        capture_debug.setdefault("_recurrence_score", float(out.get("recurrence_score") or 0.0))
        capture_debug.setdefault("_archive_reason", out.get("archive_reason"))
        return out

    def get_item(self, item_id: str) -> dict[str, Any] | None:
        cfg = load_runtime_config()
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM items WHERE id = ? AND COALESCE(namespace, 'default') = ?",
                (item_id, cfg.memory_namespace),
            ).fetchone()
            return self._row_to_item(row) if row else None
        finally:
            conn.close()

    def update_vision_result(
        self,
        item_id: str,
        captions: list[str],
        cache_paths: list[str],
    ) -> None:
        with self._write_transaction() as conn:
            conn.execute(
                """
                UPDATE items
                SET image_captions = ?, image_cache_paths = ?, vision_done = 1, embedding_done = 0,
                    index_dirty = 1, updated_at = ?
                WHERE id = ?
                """,
                (json.dumps(captions, ensure_ascii=False), json.dumps(cache_paths, ensure_ascii=False), now_iso(), item_id),
            )

    def mark_embedding_done(self, item_id: str) -> None:
        with self._write_transaction() as conn:
            conn.execute(
                "UPDATE items SET embedding_done = 1, index_dirty = 0, updated_at = ? WHERE id = ?",
                (now_iso(), item_id),
            )

    def mark_embedding_skipped(self, item_id: str, reason: str) -> None:
        with self._write_transaction() as conn:
            conn.execute(
                """
                UPDATE items
                SET embedding_done = 1,
                    embedding_skipped = 1,
                    embedding_skipped_reason = ?,
                    index_dirty = 0,
                    updated_at = ?
                WHERE id = ?
                """,
                (reason[:500], now_iso(), item_id),
            )

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
            params.append(self._maybe_encrypt_text(note, aad=b"memoryfeed:note"))
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags, ensure_ascii=False))
        if not updates:
            return self.get_item(item_id)

        params.append(item_id)
        updates.append("updated_at = ?")
        params.insert(-1, now_iso())
        with self._write_transaction() as conn:
            conn.execute(f"UPDATE items SET {', '.join(updates)} WHERE id = ?", params)
        return self.get_item(item_id)

    def apply_heat_decay(self, decay: float = 0.95, idle_days: int = 7) -> int:
        cfg = load_runtime_config()
        if not cfg.enable_decay:
            return 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=idle_days)
        today = date.today().isoformat()
        with self._write_transaction() as conn:
            last_decay = conn.execute(
                "SELECT value FROM meta WHERE key = 'last_heat_decay_date'"
            ).fetchone()
            if last_decay and last_decay["value"] == today:
                return 0

            cur = conn.execute(
                """
                UPDATE items
                SET heat = MAX(0.05, COALESCE(heat, 1.0) * ?),
                    updated_at = ?
                WHERE archived_at IS NULL
                  AND DATETIME(COALESCE(last_surfaced, captured_at)) < DATETIME(?)
                """,
                (float(decay), now_iso(), cutoff.isoformat()),
            )
            conn.execute(
                """
                INSERT INTO meta(key, value)
                VALUES('last_heat_decay_date', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (today,),
            )
            return int(cur.rowcount or 0)

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
        updates.append("updated_at = ?")
        params.append(now_iso())
        params.append(item_id)

        with self._write_transaction() as conn:
            conn.execute(f"UPDATE items SET {', '.join(updates)} WHERE id = ?", params)
        return self.get_item(item_id)

    def mark_items_surfaced(self, item_ids: list[str]) -> int:
        ids = [item_id for item_id in item_ids if item_id]
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        params: list[Any] = [now_iso(), *ids]
        with self._write_transaction() as conn:
            cur = conn.execute(
                f"""
                UPDATE items
                SET last_surfaced = ?,
                    surfaced_count = COALESCE(surfaced_count, 0) + 1,
                    heat = MIN(10.0, COALESCE(heat, 1.0) + 0.05),
                    updated_at = ?
                WHERE id IN ({placeholders})
                """,
                [now_iso(), *params],
            )
            return int(cur.rowcount or 0)

    def archive_items(self, item_ids: list[str]) -> int:
        ids = [item_id for item_id in item_ids if item_id]
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        params: list[Any] = [now_iso(), now_iso(), *ids]
        with self._write_transaction() as conn:
            cur = conn.execute(
                f"UPDATE items SET archived_at = ?, updated_at = ? WHERE id IN ({placeholders})",
                params,
            )
            return int(cur.rowcount or 0)

    def unarchive_items(self, item_ids: list[str]) -> int:
        ids = [item_id for item_id in item_ids if item_id]
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        params: list[Any] = [now_iso(), *ids]
        with self._write_transaction() as conn:
            cur = conn.execute(
                f"UPDATE items SET archived_at = NULL, archive_reason = NULL, updated_at = ? WHERE id IN ({placeholders})",
                params,
            )
            return int(cur.rowcount or 0)

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
        cfg = load_runtime_config()
        conn = self._connect()
        try:
            normalized_query = _build_safe_fts_query(query)
            params: list[Any] = [normalized_query]
            where = "AND items.archived_at IS NULL AND COALESCE(items.namespace, 'default') = ?"
            params.append(cfg.memory_namespace)
            if cfg.hide_sensitive_from_search:
                where += " AND COALESCE(items.search_hidden, 0) = 0"
            if days_back is not None:
                cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
                where += " AND items.captured_at >= ?"
                params.append(cutoff.isoformat())
            params.append(limit)

            sql = f"""
                SELECT
                    items.id,
                    items.url,
                    items.platform,
                    items.content_type,
                    items.text_content,
                    items.image_urls,
                    items.image_cache_paths,
                    items.author,
                    items.captured_at,
                    items.starred,
                    items.heat,
                    items.noise_score,
                    items.capture_confidence,
                    items.canonical_url,
                    items.sensitivity_level,
                    bm25(items_fts) AS bm25_score
                FROM items_fts
                JOIN items ON items_fts.rowid = items.rowid
                WHERE items_fts MATCH ? {where}
                ORDER BY bm25_score ASC
                LIMIT ?
            """
            try:
                rows = conn.execute(sql, params).fetchall()
            except sqlite3.OperationalError as exc:
                # Fallback to phrase query for malformed user/content text that breaks FTS parser.
                logger.warning("fts_query_fallback query=%r error=%s", query, exc)
                fallback_params = [_build_fts_phrase_query(query), *params[1:]]
                rows = conn.execute(sql, fallback_params).fetchall()
            return [self._row_to_search_dict(r, bm25_key="bm25_score") for r in rows]
        finally:
            conn.close()

    def all_for_timeline(self, date_str: str, platform: str | None = None) -> list[dict[str, Any]]:
        cfg = load_runtime_config()
        conn = self._connect()
        try:
            where = "DATE(captured_at) = DATE(?) AND COALESCE(namespace, 'default') = ?"
            params: list[Any] = [date_str, cfg.memory_namespace]
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
        cfg = load_runtime_config()
        conn = self._connect()
        try:
            total = int(
                conn.execute(
                    "SELECT COUNT(*) FROM items WHERE COALESCE(namespace, 'default') = ?",
                    (cfg.memory_namespace,),
                ).fetchone()[0]
            )
            today = int(
                conn.execute(
                    "SELECT COUNT(*) FROM items WHERE COALESCE(namespace, 'default') = ? AND DATE(captured_at)=DATE('now', 'localtime')",
                    (cfg.memory_namespace,),
                ).fetchone()[0]
            )
            by_platform = [
                {"key": row[0], "count": int(row[1])}
                for row in conn.execute(
                    "SELECT platform, COUNT(*) FROM items WHERE COALESCE(namespace, 'default') = ? GROUP BY platform ORDER BY COUNT(*) DESC",
                    (cfg.memory_namespace,),
                ).fetchall()
            ]
            by_type = [
                {"key": row[0], "count": int(row[1])}
                for row in conn.execute(
                    "SELECT content_type, COUNT(*) FROM items WHERE COALESCE(namespace, 'default') = ? GROUP BY content_type ORDER BY COUNT(*) DESC",
                    (cfg.memory_namespace,),
                ).fetchall()
            ]
            return {
                "total": total,
                "today": today,
                "by_platform": by_platform,
                "by_type": by_type,
                "namespace": cfg.memory_namespace,
            }
        finally:
            conn.close()

    def count_today(self) -> int:
        cfg = load_runtime_config()
        conn = self._connect()
        try:
            return int(
                conn.execute(
                    "SELECT COUNT(*) FROM items WHERE COALESCE(namespace, 'default') = ? AND DATE(captured_at)=DATE('now', 'localtime')",
                    (cfg.memory_namespace,),
                ).fetchone()[0]
            )
        finally:
            conn.close()

    def schema_version(self) -> int:
        conn = self._connect()
        try:
            row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
            if row:
                try:
                    return int(str(row["value"]))
                except Exception:
                    return 0
            # Backward compatibility fallback for legacy DBs without migration metadata.
            return 5
        finally:
            conn.close()

    def all_items(self) -> list[dict[str, Any]]:
        cfg = load_runtime_config()
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM items WHERE COALESCE(namespace, 'default') = ? ORDER BY captured_at DESC",
                (cfg.memory_namespace,),
            ).fetchall()
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
        cfg = load_runtime_config()
        try:
            where = []
            params: list[Any] = []
            where.append("COALESCE(namespace, 'default') = ?")
            params.append(cfg.memory_namespace)
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
        cfg = load_runtime_config()
        conn = self._connect()
        try:
            rows = conn.execute(
                f"SELECT * FROM items WHERE id IN ({placeholders}) AND COALESCE(namespace, 'default') = ?",
                [*ids, cfg.memory_namespace],
            ).fetchall()
            out: dict[str, dict[str, Any]] = {}
            for row in rows:
                item = self._row_to_item(row)
                if item:
                    out[item["id"]] = item
            return out
        finally:
            conn.close()

    def list_dirty_items(self, limit: int = 200) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT *
                FROM items
                WHERE COALESCE(index_dirty, 0) = 1
                  AND COALESCE(embedding_skipped, 0) = 0
                  AND COALESCE(namespace, 'default') = ?
                ORDER BY COALESCE(updated_at, captured_at) ASC
                LIMIT ?
                """,
                (load_runtime_config().memory_namespace, limit),
            ).fetchall()
            return [self._row_to_item(row) for row in rows]
        finally:
            conn.close()

    def mark_index_dirty(self, item_id: str) -> None:
        with self._write_transaction() as conn:
            conn.execute(
                "UPDATE items SET index_dirty = 1, embedding_done = 0, updated_at = ? WHERE id = ?",
                (now_iso(), item_id),
            )

    def update_integrity_fields(self, item_id: str, fields: dict[str, Any]) -> None:
        if not fields:
            return
        normalized: dict[str, Any] = {}
        for key, value in fields.items():
            if key in {"image_urls", "image_captions", "image_cache_paths", "media_urls", "tags", "quality_flags", "related_topics", "related_entities", "sensitivity_reasons"}:
                normalized[key] = json.dumps(value or [], ensure_ascii=False)
            elif key in {"capture_debug"}:
                normalized[key] = self._maybe_encrypt_text(json.dumps(value or {}, ensure_ascii=False), aad=b"memoryfeed:capture_debug")
            elif key in {"note"}:
                normalized[key] = self._maybe_encrypt_text(value, aad=b"memoryfeed:note")
            elif key in {"source_context"}:
                normalized[key] = self._maybe_encrypt_text(value, aad=b"memoryfeed:source_context")
            else:
                normalized[key] = value
        normalized["updated_at"] = now_iso()
        updates = ", ".join(f"{key} = ?" for key in normalized.keys())
        params = [normalized[key] for key in normalized.keys()] + [item_id]
        with self._write_transaction() as conn:
            conn.execute(f"UPDATE items SET {updates} WHERE id = ?", params)

    def _find_semantic_duplicate(self, item: dict[str, Any]) -> str | None:
        text = str(item.get("text_content") or "").strip()
        if not text:
            return None
        cfg = load_runtime_config()
        threshold = float(cfg.memory_dedupe_similarity_threshold)
        platform = str(item.get("platform") or "unknown")
        namespace = str(item.get("namespace") or cfg.memory_namespace)
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT id, text_content
                FROM items
                WHERE platform = ?
                  AND COALESCE(namespace, 'default') = ?
                ORDER BY captured_at DESC
                LIMIT 120
                """,
                (platform, namespace),
            ).fetchall()
            for row in rows:
                score = semantic_similarity(text, str(row["text_content"] or ""))
                if score >= threshold:
                    return str(row["id"])
            return None
        finally:
            conn.close()

    def rebuild_all_fingerprints(self) -> int:
        rows = self.all_items()
        changed = 0
        for row in rows:
            rebuilt = self._normalize_item_for_insert(row).get("dedupe_key")
            if rebuilt and rebuilt != row.get("dedupe_key"):
                self.update_integrity_fields(str(row["id"]), {"dedupe_key": rebuilt})
                changed += 1
        return changed

    def compact_indexes(self) -> int:
        with self._write_transaction() as conn:
            conn.execute("INSERT INTO items_fts(items_fts) VALUES('optimize')")
            conn.execute("PRAGMA optimize")
        return 1

    def cleanup_old_logs(self, keep_days: int = 7) -> int:
        logs_dir = DATA_DIR / "logs"
        if not logs_dir.exists():
            return 0
        now = datetime.now(timezone.utc).timestamp()
        removed = 0
        for candidate in logs_dir.glob("memoryfeed.log.*"):
            try:
                age_days = (now - candidate.stat().st_mtime) / 86400.0
                if age_days > keep_days:
                    candidate.unlink(missing_ok=True)
                    removed += 1
            except Exception:
                continue
        return removed

    def recompute_decay_states(self) -> int:
        cfg = load_runtime_config()
        rows = self.all_items()
        changed = 0
        for row in rows:
            decay_score, aging_state = compute_decay(row, half_life_days=cfg.decay_half_life_days)
            if float(row.get("decay_score") or 0.0) != decay_score or str(row.get("aging_state") or "") != aging_state:
                self.update_integrity_fields(str(row["id"]), {"decay_score": decay_score, "aging_state": aging_state})
                changed += 1
        return changed

    def delete_all(self) -> None:
        with self._write_transaction() as conn:
            conn.execute("DELETE FROM items")
            conn.execute("DELETE FROM items_fts")
            conn.execute("DELETE FROM job_dead_letters")

    def push_dead_letter(
        self,
        queue_name: str,
        item_id: str | None,
        attempt: int,
        error: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        with self._write_transaction() as conn:
            conn.execute(
                """
                INSERT INTO job_dead_letters(queue_name, item_id, attempt, error, payload, created_at)
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    queue_name[:120],
                    item_id,
                    int(attempt),
                    str(error)[:1000],
                    json.dumps(payload or {}, ensure_ascii=False),
                    now_iso(),
                ),
            )

    def list_dead_letters(self, limit: int = 200) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT id, queue_name, item_id, attempt, error, payload, created_at
                FROM job_dead_letters
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
            return [
                {
                    "id": int(r["id"]),
                    "queue_name": str(r["queue_name"]),
                    "item_id": r["item_id"],
                    "attempt": int(r["attempt"] or 0),
                    "error": str(r["error"] or ""),
                    "payload": _safe_json_dict(r["payload"]),
                    "created_at": str(r["created_at"]),
                }
                for r in rows
            ]
        finally:
            conn.close()

    def migrate_encrypt_sensitive_fields(self, limit: int = 2000) -> dict[str, int]:
        if not self._crypto.enabled:
            return {"processed": 0, "updated": 0}
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT id, note, source_context, capture_debug
                FROM items
                WHERE (
                    (note IS NOT NULL AND note != '' AND note NOT LIKE 'enc:%')
                    OR (source_context IS NOT NULL AND source_context != '' AND source_context NOT LIKE 'enc:%')
                    OR (capture_debug IS NOT NULL AND capture_debug != '' AND capture_debug NOT LIKE 'enc:%')
                )
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        finally:
            conn.close()
        updated = 0
        for row in rows:
            fields: dict[str, Any] = {}
            if row["note"] and not str(row["note"]).startswith("enc:"):
                fields["note"] = str(row["note"])
            if row["source_context"] and not str(row["source_context"]).startswith("enc:"):
                fields["source_context"] = str(row["source_context"])
            if row["capture_debug"] and not str(row["capture_debug"]).startswith("enc:"):
                try:
                    fields["capture_debug"] = _safe_json_dict(str(row["capture_debug"]))
                except Exception:
                    fields["capture_debug"] = {"raw": str(row["capture_debug"])}
            if fields:
                self.update_integrity_fields(str(row["id"]), fields)
                updated += 1
        return {"processed": len(rows), "updated": updated}

    def migrate_encrypt_media(self, limit: int = 5000) -> dict[str, int]:
        return self._crypto.migrate_media_folder(IMAGE_CACHE_DIR, IMAGE_ENCRYPTED_DIR, limit=limit)

    @staticmethod
    def _row_to_item(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        capture_debug = _safe_json_dict(row["capture_debug"]) if "capture_debug" in row.keys() else {}
        if "capture_debug" in row.keys() and isinstance(row["capture_debug"], str):
            capture_debug = _safe_json_dict(_decrypt_row_text(row["capture_debug"], aad=b"memoryfeed:capture_debug"))
        importance_score, resurfacing_score, recency_score, recurrence_score = _compute_ranking_primitives(
            {
                "captured_at": row["captured_at"] if "captured_at" in row.keys() else None,
                "capture_confidence": row["capture_confidence"] if "capture_confidence" in row.keys() else 1.0,
                "starred": bool(row["starred"]) if "starred" in row.keys() else False,
                "heat": float(row["heat"]) if "heat" in row.keys() and row["heat"] is not None else 1.0,
                "surfaced_count": int(row["surfaced_count"] or 0) if "surfaced_count" in row.keys() else 0,
                "decay_score": float(row["decay_score"]) if "decay_score" in row.keys() and row["decay_score"] is not None else 0.0,
            }
        )
        return {
            "id": row["id"],
            "url": row["url"],
            "platform": row["platform"],
            "content_type": row["content_type"],
            "text_content": row["text_content"],
            "image_urls": _safe_json_list(row["image_urls"]),
            "media_urls": _safe_json_list(row["media_urls"]) if "media_urls" in row.keys() and row["media_urls"] else _safe_json_list(row["image_urls"]),
            "image_captions": _safe_json_list(row["image_captions"]),
            "image_cache_paths": _safe_json_list(row["image_cache_paths"]),
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
            "source_context": (
                _decrypt_row_text(row["source_context"], aad=b"memoryfeed:source_context")
                if "source_context" in row.keys() and row["source_context"] is not None
                else None
            ),
            "quality_flags": _safe_json_list(row["quality_flags"]) if "quality_flags" in row.keys() else [],
            "capture_debug": capture_debug,
            "starred": bool(row["starred"]) if "starred" in row.keys() else False,
            "note": (
                _decrypt_row_text(row["note"], aad=b"memoryfeed:note")
                if "note" in row.keys() and row["note"] is not None
                else None
            ),
            "tags": _safe_json_list(row["tags"]) if "tags" in row.keys() else [],
            "heat": float(row["heat"]) if "heat" in row.keys() and row["heat"] is not None else 1.0,
            "last_surfaced": row["last_surfaced"] if "last_surfaced" in row.keys() else None,
            "surfaced_count": int(row["surfaced_count"] or 0) if "surfaced_count" in row.keys() else 0,
            "archived_at": row["archived_at"] if "archived_at" in row.keys() else None,
            "capture_confidence": float(row["capture_confidence"]) if "capture_confidence" in row.keys() and row["capture_confidence"] is not None else 1.0,
            "noise_score": float(row["noise_score"]) if "noise_score" in row.keys() and row["noise_score"] is not None else 0.0,
            "low_signal_reason": row["low_signal_reason"] if "low_signal_reason" in row.keys() else None,
            "decay_score": float(row["decay_score"]) if "decay_score" in row.keys() and row["decay_score"] is not None else 0.0,
            "aging_state": row["aging_state"] if "aging_state" in row.keys() else "active",
            "related_topics": _safe_json_list(row["related_topics"]) if "related_topics" in row.keys() else [],
            "related_entities": _safe_json_list(row["related_entities"]) if "related_entities" in row.keys() else [],
            "semantic_group": row["semantic_group"] if "semantic_group" in row.keys() else None,
            "prompt_risk_score": float(row["prompt_risk_score"]) if "prompt_risk_score" in row.keys() and row["prompt_risk_score"] is not None else 0.0,
            "prompt_risk_reason": row["prompt_risk_reason"] if "prompt_risk_reason" in row.keys() else None,
            "sensitivity_level": row["sensitivity_level"] if "sensitivity_level" in row.keys() and row["sensitivity_level"] else "none",
            "sensitivity_reasons": _safe_json_list(row["sensitivity_reasons"]) if "sensitivity_reasons" in row.keys() else [],
            "embedding_skipped": bool(row["embedding_skipped"]) if "embedding_skipped" in row.keys() else False,
            "embedding_skipped_reason": row["embedding_skipped_reason"] if "embedding_skipped_reason" in row.keys() else capture_debug.get("_embedding_skipped_reason"),
            "search_hidden": bool(row["search_hidden"]) if "search_hidden" in row.keys() else False,
            "index_dirty": bool(row["index_dirty"]) if "index_dirty" in row.keys() else False,
            "updated_at": row["updated_at"] if "updated_at" in row.keys() else None,
            "confidence_reasons": _safe_json_list(row["confidence_reasons"]) if "confidence_reasons" in row.keys() and row["confidence_reasons"] else list(capture_debug.get("_confidence_reasons") or []),
            "capture_method": row["capture_method"] if "capture_method" in row.keys() and row["capture_method"] else capture_debug.get("_capture_method"),
            "extractor_version": row["extractor_version"] if "extractor_version" in row.keys() and row["extractor_version"] else capture_debug.get("_extractor_version"),
            "capture_source": row["capture_source"] if "capture_source" in row.keys() and row["capture_source"] else capture_debug.get("_capture_source"),
            "replay_source": row["replay_source"] if "replay_source" in row.keys() and row["replay_source"] else capture_debug.get("_replay_source"),
            "namespace": row["namespace"] if "namespace" in row.keys() and row["namespace"] else "default",
            "suspicious_prompt_content": (
                (bool(row["suspicious_prompt_content"]) if "suspicious_prompt_content" in row.keys() else False)
                or bool(capture_debug.get("_suspicious_prompt_content"))
            ),
            "safety_signals": _safe_json_list(row["safety_signals"]) if "safety_signals" in row.keys() and row["safety_signals"] else list(capture_debug.get("_safety_signals") or []),
            "importance_score": float(row["importance_score"]) if "importance_score" in row.keys() and row["importance_score"] is not None else importance_score,
            "resurfacing_score": float(row["resurfacing_score"]) if "resurfacing_score" in row.keys() and row["resurfacing_score"] is not None else resurfacing_score,
            "recency_score": float(row["recency_score"]) if "recency_score" in row.keys() and row["recency_score"] is not None else recency_score,
            "recurrence_score": float(row["recurrence_score"]) if "recurrence_score" in row.keys() and row["recurrence_score"] is not None else recurrence_score,
            "archive_reason": (
                row["archive_reason"]
                if "archive_reason" in row.keys() and row["archive_reason"]
                else (
                    capture_debug.get("_archive_reason")
                    if (capture_debug.get("_archive_reason") and ("archived_at" in row.keys() and row["archived_at"]))
                    else ("retention:auto_archive" if ("archived_at" in row.keys() and row["archived_at"]) else None)
                )
            ),
        }

    @staticmethod
    def _row_to_search_dict(row: sqlite3.Row, bm25_key: str) -> dict[str, Any]:
        image_urls = _safe_json_list(row["image_urls"])
        cache_paths = _safe_json_list(row["image_cache_paths"])
        thumbnail = cache_paths[0] if cache_paths else (image_urls[0] if image_urls else None)
        return {
            "id": row["id"],
            "url": row["url"],
            "platform": row["platform"],
            "content_type": row["content_type"] if "content_type" in row.keys() else "post",
            "text_content": row["text_content"] or "",
            "thumbnail": thumbnail,
            "author": row["author"],
            "captured_at": row["captured_at"],
            "fts_score": float(row[bm25_key]),
            "starred": bool(row["starred"]) if "starred" in row.keys() else False,
            "heat": float(row["heat"]) if "heat" in row.keys() and row["heat"] is not None else 1.0,
            "noise_score": float(row["noise_score"]) if "noise_score" in row.keys() and row["noise_score"] is not None else 0.0,
            "capture_confidence": float(row["capture_confidence"]) if "capture_confidence" in row.keys() and row["capture_confidence"] is not None else 1.0,
            "canonical_url": row["canonical_url"] if "canonical_url" in row.keys() else row["url"],
            "sensitivity_level": row["sensitivity_level"] if "sensitivity_level" in row.keys() else "none",
            "namespace": row["namespace"] if "namespace" in row.keys() and row["namespace"] else "default",
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


def _build_safe_fts_query(query: str) -> str:
    text = " ".join(str(query or "").strip().split())
    if not text:
        return "\"\""
    tokens = [t for t in re.findall(r"\w+", text, flags=re.UNICODE) if t]
    if not tokens:
        return _build_fts_phrase_query(text)
    return " AND ".join(f"\"{token.replace('\"', '\"\"')}\"" for token in tokens[:16])


def _build_fts_phrase_query(query: str) -> str:
    phrase = " ".join(str(query or "").strip().split())
    return f"\"{phrase.replace('\"', '\"\"')}\""


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
    decay_penalty = min(0.45, float(item.get("decay_score") or 0.0) * 0.4)
    noise_penalty = min(0.35, float(item.get("noise_score") or 0.0) * 0.35)
    mode_bonus = _mode_bonus(item, mode)

    score = heat * 0.68 + recency * 0.2 + dwell_bonus + star_bonus + resurfacing_gap + mode_bonus - decay_penalty - noise_penalty
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
    if value.startswith(("http://", "https://", "/images/", "/api/images/")):
        return value
    p = Path(value)
    try:
        if p.exists() and p.parent.resolve() == IMAGE_CACHE_DIR.resolve():
            return f"/images/{p.name}"
        if p.exists() and p.parent.resolve() == IMAGE_ENCRYPTED_DIR.resolve():
            return f"/api/images/{p.name}"
    except Exception:
        return None
    return None


def _safe_json_list(raw: Any) -> list[Any]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if not isinstance(raw, str):
        return []
    try:
        value = json.loads(raw or "[]")
    except Exception:
        return []
    return value if isinstance(value, list) else []


def _safe_json_dict(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return {}
    try:
        value = json.loads(raw or "{}")
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _decrypt_row_text(raw: Any, aad: bytes) -> str:
    if raw is None:
        return ""
    if not isinstance(raw, str):
        return str(raw)
    crypto = AtRestCrypto()
    try:
        return crypto.decrypt_text(raw, aad=aad)
    except Exception:
        return raw


def _capture_confidence(item: dict[str, Any]) -> float:
    flags = item.get("quality_flags") or []
    missing = sum(1 for flag in flags if str(flag).startswith("missing_"))
    prompt_risk, _ = assess_prompt_risk(str(item.get("text_content") or ""))
    penalty = missing * 0.12 + prompt_risk * 0.25
    return round(max(0.05, min(1.0, 1.0 - penalty)), 6)


def _compute_ranking_primitives(item: dict[str, Any]) -> tuple[float, float, float, float]:
    now = datetime.now(timezone.utc)
    captured = _parse_iso(str(item.get("captured_at") or "")) or now
    age_days = max(0.0, (now - captured).total_seconds() / 86400.0)
    recency = max(0.0, 1.0 - min(1.0, age_days / 365.0))
    confidence = max(0.0, min(1.0, float(item.get("capture_confidence") or 1.0)))
    starred_boost = 0.18 if item.get("starred") else 0.0
    heat_component = min(0.35, float(item.get("heat") or 1.0) * 0.08)
    decay_penalty = min(0.35, float(item.get("decay_score") or 0.0) * 0.25)
    recurrence = max(0.0, min(1.0, float(item.get("surfaced_count") or 0) / 10.0))
    importance = max(0.0, min(1.0, confidence * 0.62 + recency * 0.2 + heat_component + starred_boost - decay_penalty))
    resurfacing = max(0.0, min(1.0, recency * 0.35 + recurrence * 0.45 + importance * 0.2))
    return round(importance, 6), round(resurfacing, 6), round(recency, 6), round(recurrence, 6)


def _maybe_apply_auto_archive(item: dict[str, Any], retention_days: int, low_score_threshold: float) -> None:
    captured = _parse_iso(str(item.get("captured_at") or ""))
    if not captured:
        return
    age_days = max(0.0, (datetime.now(timezone.utc) - captured).total_seconds() / 86400.0)
    importance = float(item.get("importance_score") or 0.0)
    if age_days >= max(1, int(retention_days)) and importance <= float(low_score_threshold):
        if not item.get("archived_at"):
            item["archived_at"] = now_iso()
        if not item.get("archive_reason"):
            item["archive_reason"] = f"retention:auto_archive:{retention_days}d"
