from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from backend.retention import compute_decay


class RetentionMemoryTypeTests(unittest.TestCase):
    def test_fact_decays_slower_than_ephemeral(self) -> None:
        captured = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        fact_item = {
            "captured_at": captured,
            "tags": ["fact"],
            "content_type": "post",
            "heat": 1.0,
        }
        ephemeral_item = {
            "captured_at": captured,
            "tags": [],
            "content_type": "image",
            "heat": 1.0,
        }
        fact_decay, _ = compute_decay(fact_item, half_life_days=60)
        eph_decay, _ = compute_decay(ephemeral_item, half_life_days=60)
        self.assertLess(fact_decay, eph_decay)


if __name__ == "__main__":
    unittest.main()
