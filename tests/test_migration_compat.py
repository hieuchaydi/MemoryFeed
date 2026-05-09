from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from tests._util import ensure_test_data_dir

ensure_test_data_dir()

from backend.import_export import build_export_payload, import_payload
from backend.store import Store


class MigrationCompatTests(unittest.TestCase):
    def test_old_schema_without_schema_version_is_upgraded_safely(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-migrate-compat-") as tmp:
            db_path = Path(tmp) / "memoryfeed.db"
            conn = sqlite3.connect(db_path)
            try:
                conn.execute(
                    """
                    CREATE TABLE items (
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
                    )
                    """
                )
                conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
                conn.commit()
            finally:
                conn.close()

            store = Store(db_path=db_path)
            schema_version = store.schema_version()
            self.assertGreaterEqual(schema_version, 5)

            item = {
                "id": "compat-1",
                "url": "https://x.com/alice/status/1",
                "platform": "twitter",
                "content_type": "post",
                "text_content": "compat migration test",
                "captured_at": "2026-05-09T00:00:00+00:00",
                "dedupe_key": "compat-key-1",
            }
            inserted, _ = store.insert_item(item)
            self.assertTrue(inserted)
            stored = store.get_item("compat-1")
            self.assertIn("canonical_url", stored)
            self.assertIn("capture_confidence", stored)
            self.assertIn("capture_method", stored)

    def test_import_export_preserves_new_capture_fields(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-import-export-") as tmp:
            store = Store(db_path=Path(tmp) / "memoryfeed.db")
            item = {
                "id": "compat-2",
                "url": "https://example.com/1",
                "platform": "unknown",
                "content_type": "post",
                "text_content": "hello",
                "captured_at": "2026-05-09T01:00:00+00:00",
                "dedupe_key": "compat-key-2",
                "capture_confidence": 0.91,
                "confidence_reasons": ["fallback_selector_used:text"],
                "capture_method": "manual_capture",
                "extractor_version": "unknown_v3_1",
                "capture_source": "manual_button",
            }
            inserted, _ = store.insert_item(item)
            self.assertTrue(inserted)
            payload = build_export_payload(store)
            self.assertGreaterEqual(payload.get("schema_version", 0), 5)
            self.assertEqual(len(payload.get("items", [])), 1)

            store2 = Store(db_path=Path(tmp) / "memoryfeed-copy.db")
            report = import_payload(store2, payload)
            self.assertEqual(report["inserted"], 1)
            restored = store2.get_item("compat-2")
            self.assertAlmostEqual(float(restored["capture_confidence"]), 0.91, places=2)
            self.assertEqual(restored["capture_method"], "manual_capture")


if __name__ == "__main__":
    unittest.main()
