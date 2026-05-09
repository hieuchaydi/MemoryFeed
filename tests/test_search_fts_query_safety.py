from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from backend.searcher import Searcher
from backend.store import Store


class _FakeIndexer:
    async def semantic_search(self, query: str, limit: int = 20):
        return []

    def status(self):
        return {}


class SearchFtsQuerySafetyTests(unittest.TestCase):
    def test_search_fts_handles_colon_query_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-search-fts-safe-") as tmp:
            store = Store(db_path=Path(tmp) / "memoryfeed.db")
            store.insert_item(
                {
                    "id": "q1",
                    "url": "https://example.com/1",
                    "platform": "youtube",
                    "content_type": "video",
                    "text_content": "Make money tutorial and docker tips",
                    "captured_at": "2026-05-09T10:00:00+00:00",
                }
            )
            rows = store.search_fts("Make: money", limit=5)
            self.assertIsInstance(rows, list)

    def test_searcher_handles_video_like_query_tokens(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-search-fts-safe-") as tmp:
            store = Store(db_path=Path(tmp) / "memoryfeed.db")
            store.insert_item(
                {
                    "id": "q2",
                    "url": "https://example.com/2",
                    "platform": "tiktok",
                    "content_type": "video",
                    "text_content": "loQAD challenge trend",
                    "captured_at": "2026-05-09T10:00:00+00:00",
                }
            )
            searcher = Searcher(store, _FakeIndexer())  # type: ignore[arg-type]
            rows = asyncio.run(searcher.search("loQAD: challenge", limit=5))
            self.assertIsInstance(rows, list)


if __name__ == "__main__":
    unittest.main()
