from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.redaction import classify_sensitivity
from backend.store import Store


class SensitiveClassificationTests(unittest.TestCase):
    def test_sensitive_detection_flags_high_risk_text(self) -> None:
        level, reasons = classify_sensitivity("Bearer sk_ABCDEF1234567890 and password=hello")
        self.assertEqual(level, "high")
        self.assertTrue(reasons)

    def test_store_marks_sensitive_items_for_embedding_skip(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-sensitive-") as tmp:
            store = Store(db_path=Path(tmp) / "memoryfeed.db")
            store.insert_item(
                {
                    "id": "sec-1",
                    "url": "https://example.com/secret",
                    "platform": "unknown",
                    "content_type": "post",
                    "text_content": "token Bearer sk_ABCDEF1234567890",
                    "captured_at": "2026-05-09T10:00:00+00:00",
                }
            )
            item = store.get_item("sec-1")
            self.assertIsNotNone(item)
            self.assertEqual(item["sensitivity_level"], "high")
            self.assertTrue(item["embedding_skipped"])


if __name__ == "__main__":
    unittest.main()
