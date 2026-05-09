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


class SearchDebugTests(unittest.TestCase):
    def test_search_debug_includes_explainability_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-search-debug-") as tmp:
            store = Store(db_path=Path(tmp) / "memoryfeed.db")
            store.insert_item(
                {
                    "id": "s1",
                    "url": "https://x.com/alice/status/1",
                    "platform": "twitter",
                    "content_type": "post",
                    "text_content": "python docker networking tips",
                    "captured_at": "2026-05-09T10:00:00+00:00",
                }
            )
            searcher = Searcher(store, _FakeIndexer())  # type: ignore[arg-type]
            rows = asyncio.run(searcher.search("python", limit=5, debug=True))
            self.assertGreaterEqual(len(rows), 1)
            dbg = rows[0].get("search_debug") or {}
            self.assertIn("ranking_factors", dbg)
            self.assertIn("matched_fields", dbg)
            self.assertIn("penalties", dbg)


if __name__ == "__main__":
    unittest.main()
