from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tests._util import ensure_test_data_dir

ensure_test_data_dir()

from backend.store import Store


class RankingTests(unittest.TestCase):
    def test_ranking_scores_exist_and_react_to_star(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-ranking-") as tmp:
            store = Store(db_path=Path(tmp) / "memoryfeed.db")
            captured_at = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
            item = {
                "id": "rank-1",
                "url": "https://example.com/rank/1",
                "canonical_url": "https://example.com/rank/1",
                "platform": "unknown",
                "content_type": "post",
                "text_content": "Ranking foundations for resurfacing and recurrence.",
                "captured_at": captured_at,
                "dedupe_key": "rank-key-1",
            }
            inserted, _ = store.insert_item(item)
            self.assertTrue(inserted)

            before = store.get_item("rank-1")
            self.assertGreaterEqual(before["importance_score"], 0.0)
            self.assertLessEqual(before["importance_score"], 1.0)
            self.assertGreaterEqual(before["resurfacing_score"], 0.0)
            self.assertLessEqual(before["resurfacing_score"], 1.0)

            store.update_item_metadata("rank-1", starred=True)
            after = store.get_item("rank-1")
            self.assertGreaterEqual(after["importance_score"], before["importance_score"])

    def test_low_confidence_capture_gets_lower_importance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-ranking-confidence-") as tmp:
            store = Store(db_path=Path(tmp) / "memoryfeed.db")
            captured_at = datetime.now(timezone.utc).isoformat()
            high = {
                "id": "rank-hi",
                "url": "https://example.com/rank/high",
                "platform": "unknown",
                "content_type": "post",
                "text_content": "high confidence sample",
                "captured_at": captured_at,
                "dedupe_key": "rank-hi-key",
                "capture_confidence": 0.95,
                "quality_flags": [],
            }
            low = {
                "id": "rank-lo",
                "url": "https://example.com/rank/low",
                "platform": "unknown",
                "content_type": "post",
                "text_content": "low confidence sample",
                "captured_at": captured_at,
                "dedupe_key": "rank-lo-key",
                "capture_confidence": 0.25,
                "quality_flags": ["missing_author_name", "missing_media_urls"],
            }
            ok_hi, _ = store.insert_item(high)
            ok_lo, _ = store.insert_item(low)
            self.assertTrue(ok_hi)
            self.assertTrue(ok_lo)
            high_row = store.get_item("rank-hi")
            low_row = store.get_item("rank-lo")
            self.assertGreaterEqual(high_row["importance_score"], low_row["importance_score"])


if __name__ == "__main__":
    unittest.main()
