from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.store import Store
from backend.verify import verify_store


class VerifyTests(unittest.TestCase):
    def test_verify_detects_and_repairs_integrity_issues(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-verify-") as tmp:
            store = Store(db_path=Path(tmp) / "memoryfeed.db")
            inserted, item_id = store.insert_item(
                {
                    "id": "v1",
                    "url": "https://x.com/alice/status/123",
                    "platform": "twitter",
                    "content_type": "post",
                    "text_content": "hello world",
                    "captured_at": "2026-05-09T10:00:00+00:00",
                }
            )
            self.assertTrue(inserted)
            self.assertEqual(item_id, "v1")

            store.update_integrity_fields("v1", {"canonical_url": "not-a-url", "captured_at": "bad-timestamp", "image_cache_paths": ["C:\\tmp\\missing.png"]})
            conn = store._connect()
            try:
                conn.execute("UPDATE items SET related_topics = ? WHERE id = ?", ('{"bad":"field"}', "v1"))
                conn.commit()
            finally:
                conn.close()

            report = verify_store(store, repair=False)
            self.assertIn("v1", report.invalid_canonical_urls)
            self.assertIn("v1", report.missing_timestamps)
            self.assertTrue(any(entry.startswith("v1:") for entry in report.broken_references))
            self.assertIn("v1:related_topics", report.invalid_schema_fields)

            repaired = verify_store(store, repair=True)
            self.assertIn("v1", repaired.repaired)
            row = store.get_item("v1")
            self.assertIsNotNone(row)
            self.assertTrue(str(row["canonical_url"]).startswith("https://"))


if __name__ == "__main__":
    unittest.main()
