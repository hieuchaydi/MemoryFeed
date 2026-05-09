from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.indexing import collect_dirty_items
from backend.store import Store


class IncrementalIndexingTests(unittest.TestCase):
    def test_dirty_items_tracking(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-indexing-") as tmp:
            store = Store(db_path=Path(tmp) / "memoryfeed.db")
            store.insert_item(
                {
                    "id": "ix-1",
                    "url": "https://example.com/idx",
                    "platform": "unknown",
                    "content_type": "post",
                    "text_content": "index me",
                    "captured_at": "2026-05-09T10:00:00+00:00",
                }
            )
            dirty = collect_dirty_items(store, limit=10)
            self.assertEqual(len(dirty), 1)
            store.mark_embedding_done("ix-1")
            dirty_after = collect_dirty_items(store, limit=10)
            self.assertEqual(len(dirty_after), 0)


if __name__ == "__main__":
    unittest.main()
