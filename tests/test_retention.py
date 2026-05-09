from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from tests._util import ensure_test_data_dir

ensure_test_data_dir()

from backend.store import Store


class RetentionTests(unittest.TestCase):
    def test_auto_archive_and_unarchive(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-retention-") as tmp:
            with patch.dict(
                os.environ,
                {
                    "MEMORY_AUTO_ARCHIVE": "true",
                    "MEMORY_RETENTION_DAYS": "30",
                    "MEMORY_ARCHIVE_LOW_SCORE_THRESHOLD": "1.0",
                },
                clear=False,
            ):
                store = Store(db_path=Path(tmp) / "memoryfeed.db")
                old_time = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
                item = {
                    "id": "ret-1",
                    "url": "https://example.com/retention/1",
                    "canonical_url": "https://example.com/retention/1",
                    "platform": "unknown",
                    "content_type": "post",
                    "text_content": "Low value memory for retention test",
                    "image_urls": [],
                    "image_captions": [],
                    "captured_at": old_time,
                    "dedupe_key": "ret-key-1",
                }
                inserted, _ = store.insert_item(item)
                self.assertTrue(inserted)

                stored = store.get_item("ret-1")
                self.assertIsNotNone(stored)
                self.assertIsNotNone(stored["archived_at"])
                self.assertTrue((stored.get("archive_reason") or "").startswith("retention:"))

                changed = store.unarchive_items(["ret-1"])
                self.assertEqual(changed, 1)
                restored = store.get_item("ret-1")
                self.assertIsNone(restored["archived_at"])
                self.assertIsNone(restored.get("archive_reason"))


if __name__ == "__main__":
    unittest.main()
