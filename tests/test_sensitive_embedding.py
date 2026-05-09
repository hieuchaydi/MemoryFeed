from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests._util import ensure_test_data_dir

ensure_test_data_dir()

from backend.indexer import IndexerService
from backend.redaction import scan_sensitive_content
from backend.store import Store


class SensitiveEmbeddingTests(unittest.TestCase):
    def test_sensitive_scan_detects_multiple_signals(self) -> None:
        sample = "Contact admin@example.com with Bearer abcdefghijklmnopqrstuvwxyz and sk-ABCDEF1234567890123456"
        result = scan_sensitive_content(sample)
        self.assertTrue(result["sensitive"])
        self.assertIn("email", result["reasons"])
        self.assertIn("bearer_token", result["reasons"])

    def test_indexer_skips_sensitive_embedding(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-sensitive-") as tmp:
            with patch.dict(os.environ, {"MEMORY_SKIP_SENSITIVE_EMBEDDING": "true"}, clear=False):
                store = Store(db_path=Path(tmp) / "memoryfeed.db")
                item = {
                    "id": "sens-1",
                    "url": "https://example.com/sensitive/1",
                    "canonical_url": "https://example.com/sensitive/1",
                    "platform": "unknown",
                    "content_type": "post",
                    "text_content": "Bearer abcdefghijklmnopqrstuvwxyz token here",
                    "captured_at": "2026-05-08T11:05:00+00:00",
                    "dedupe_key": "sens-key-1",
                }
                inserted, _ = store.insert_item(item)
                self.assertTrue(inserted)
                indexer = IndexerService(store)

                with patch("backend.indexer.SentenceTransformer", side_effect=AssertionError("Model must not load")):
                    asyncio.run(indexer.index_item("sens-1"))

                stored = store.get_item("sens-1")
                self.assertTrue(stored["embedding_done"])
                self.assertTrue((stored.get("embedding_skipped_reason") or "").startswith("sensitive:"))


if __name__ == "__main__":
    unittest.main()
