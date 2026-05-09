from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.searcher import Searcher
from backend.store import Store


class _FakeIndexer:
    async def semantic_search(self, query: str, limit: int = 20):
        return []

    def status(self):
        return {}


class SearchDiversityTests(unittest.TestCase):
    def test_diversity_penalizes_near_duplicates(self) -> None:
        with patch.dict(
            os.environ,
            {
                "MEMORY_SEARCH_DIVERSITY": "true",
                "MEMORY_SEARCH_DIVERSITY_FACTOR": "0.8",
            },
            clear=False,
        ):
            with tempfile.TemporaryDirectory(prefix="memoryfeed-search-diversity-") as tmp:
                store = Store(db_path=Path(tmp) / "memoryfeed.db")
                store.insert_item(
                    {
                        "id": "d1",
                        "url": "https://x.com/alice/status/1",
                        "platform": "twitter",
                        "content_type": "post",
                        "text_content": "docker tip same post",
                        "captured_at": "2026-05-09T10:00:00+00:00",
                    }
                )
                store.insert_item(
                    {
                        "id": "d2",
                        "url": "https://x.com/alice/status/1?utm_source=x",
                        "platform": "twitter",
                        "content_type": "post",
                        "text_content": "docker tip same post",
                        "captured_at": "2026-05-09T10:10:00+00:00",
                    }
                )
                store.insert_item(
                    {
                        "id": "d3",
                        "url": "https://www.linkedin.com/feed/update/urn:li:activity:999",
                        "platform": "linkedin",
                        "content_type": "post",
                        "text_content": "docker orchestration writeup",
                        "captured_at": "2026-05-09T10:20:00+00:00",
                    }
                )
                searcher = Searcher(store, _FakeIndexer())  # type: ignore[arg-type]
                rows = asyncio.run(searcher.search("docker", limit=5, debug=True))
                self.assertGreaterEqual(len(rows), 2)
                penalties = [float(row.get("diversity_penalty") or 0.0) for row in rows]
                self.assertTrue(any(p > 0.0 for p in penalties))


if __name__ == "__main__":
    unittest.main()
