from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from tests._util import ensure_test_data_dir

ensure_test_data_dir()

from backend.store import Store


class SemanticDedupeTests(unittest.TestCase):
    def test_semantic_near_duplicate_collapses_second_item(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-sem-dedupe-") as tmp:
            with patch.dict(
                os.environ,
                {
                    "MEMORY_SEMANTIC_DEDUPE": "true",
                    "MEMORY_DEDUPE_SIMILARITY_THRESHOLD": "0.82",
                },
                clear=False,
            ):
                store = Store(db_path=Path(tmp) / "memoryfeed.db")
                captured_at = datetime(2026, 5, 8, 11, 5, tzinfo=timezone.utc).isoformat()

                item_a = {
                    "id": "item-a",
                    "url": "https://x.com/alice/status/1",
                    "canonical_url": "https://x.com/alice/status/1",
                    "platform": "twitter",
                    "content_type": "post",
                    "text_content": "MemoryFeed architecture notes about semantic dedupe and embeddings.",
                    "image_urls": [],
                    "image_captions": [],
                    "author": "alice",
                    "author_name": "alice",
                    "captured_at": captured_at,
                    "dedupe_key": "fingerprint-a",
                }
                item_b = {
                    "id": "item-b",
                    "url": "https://x.com/alice/status/2",
                    "canonical_url": "https://x.com/alice/status/2",
                    "platform": "twitter",
                    "content_type": "post",
                    "text_content": "MemoryFeed architecture note about semantic dedupe and embedding behavior.",
                    "image_urls": [],
                    "image_captions": [],
                    "author": "alice",
                    "author_name": "alice",
                    "captured_at": captured_at,
                    "dedupe_key": "fingerprint-b",
                }

                inserted_a, id_a = store.insert_item(item_a)
                inserted_b, duplicate_id = store.insert_item(item_b)

                self.assertTrue(inserted_a)
                self.assertEqual(id_a, "item-a")
                self.assertFalse(inserted_b)
                self.assertEqual(duplicate_id, "item-a")


if __name__ == "__main__":
    unittest.main()
