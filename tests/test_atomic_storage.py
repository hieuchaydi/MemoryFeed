from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.store import Store


class AtomicStorageTests(unittest.TestCase):
    def test_failed_insert_rolls_back_without_partial_row(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-atomic-") as tmp:
            store = Store(db_path=Path(tmp) / "memoryfeed.db")
            with self.assertRaises(RuntimeError):
                store.insert_item_atomic(
                    {
                        "id": "atomic-1",
                        "url": "https://example.com/post/1",
                        "platform": "unknown",
                        "content_type": "post",
                        "text_content": "rollback me",
                        "captured_at": "2026-05-09T10:00:00+00:00",
                    },
                    fail_after_write=True,
                )
            self.assertIsNone(store.get_item("atomic-1"))


if __name__ == "__main__":
    unittest.main()
