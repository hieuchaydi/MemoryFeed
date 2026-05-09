from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests._util import ensure_test_data_dir

ensure_test_data_dir()

from backend.store import Store


class NamespaceIsolationTests(unittest.TestCase):
    def test_namespace_isolation_for_search_and_get(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-ns-") as tmp:
            db_path = Path(tmp) / "memoryfeed.db"
            with patch.dict(os.environ, {"MEMORYFEED_NAMESPACE": "work"}, clear=False):
                work_store = Store(db_path=db_path)
                ok, _ = work_store.insert_item(
                    {
                        "id": "ns-work-1",
                        "url": "https://example.com/work",
                        "canonical_url": "https://example.com/work",
                        "platform": "unknown",
                        "content_type": "post",
                        "text_content": "kubernetes rollout strategy",
                        "dedupe_key": "ns-work-1",
                    }
                )
                self.assertTrue(ok)
                self.assertIsNotNone(work_store.get_item("ns-work-1"))

            with patch.dict(os.environ, {"MEMORYFEED_NAMESPACE": "personal"}, clear=False):
                personal_store = Store(db_path=db_path)
                self.assertIsNone(personal_store.get_item("ns-work-1"))
                hits = personal_store.search_fts("kubernetes", limit=5)
                self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
