from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from backend.retention import compute_decay


class MemoryDecayTests(unittest.TestCase):
    def test_decay_increases_with_age(self) -> None:
        now = datetime(2026, 5, 9, tzinfo=timezone.utc)
        recent = {"captured_at": (now - timedelta(days=5)).isoformat(), "heat": 1.0}
        old = {"captured_at": (now - timedelta(days=200)).isoformat(), "heat": 1.0}
        recent_score, _ = compute_decay(recent, half_life_days=90, now=now)
        old_score, state = compute_decay(old, half_life_days=90, now=now)
        self.assertGreater(old_score, recent_score)
        self.assertIn(state, {"cooling", "stale", "archived"})


if __name__ == "__main__":
    unittest.main()
