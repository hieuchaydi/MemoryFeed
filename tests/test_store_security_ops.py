from __future__ import annotations

import base64
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.store import Store


class StoreSecurityOpsTests(unittest.TestCase):
    def test_dead_letter_persistence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-dlq-") as tmp:
            store = Store(db_path=Path(tmp) / "memoryfeed.db")
            store.push_dead_letter("vision", "item-1", 4, "boom", {"stage": "x"})
            rows = store.list_dead_letters(limit=10)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["queue_name"], "vision")

    def test_encrypt_migrate_sensitive_fields(self) -> None:
        key = base64.urlsafe_b64encode(b"b" * 32).decode("ascii")
        with tempfile.TemporaryDirectory(prefix="memoryfeed-encmig-") as tmp:
            db_path = Path(tmp) / "memoryfeed.db"
            with patch.dict(
                os.environ,
                {
                    "MEMORY_ENCRYPTION_MODE": "compat",
                    "MEMORY_ENCRYPTION_KEY": key,
                },
                clear=False,
            ):
                store = Store(db_path=db_path)
                store.insert_item(
                    {
                        "id": "enc-1",
                        "url": "https://example.com/x",
                        "canonical_url": "https://example.com/x",
                        "platform": "unknown",
                        "content_type": "post",
                        "text_content": "hello",
                        "note": "secret-note",
                        "source_context": "context-x",
                        "capture_debug": {"a": 1},
                        "dedupe_key": "enc-1",
                    }
                )
                report = store.migrate_encrypt_sensitive_fields(limit=100)
                self.assertGreaterEqual(report["processed"], 0)
                row = store.get_item("enc-1")
                self.assertEqual(row.get("note"), "secret-note")
                conn = sqlite3.connect(db_path)
                raw = conn.execute("SELECT note FROM items WHERE id='enc-1'").fetchone()[0]
                conn.close()
                self.assertTrue(str(raw).startswith("enc:"))


if __name__ == "__main__":
    unittest.main()
