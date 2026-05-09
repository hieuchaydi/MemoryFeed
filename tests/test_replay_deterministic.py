from __future__ import annotations

import unittest
from pathlib import Path

from backend.extractor_replay import replay_fixture


class ReplayDeterministicTests(unittest.TestCase):
    def test_deterministic_replay_stable_output(self) -> None:
        fixture = Path("tests/fixtures/twitter_basic.html")
        a = replay_fixture(fixture, deterministic=True)
        b = replay_fixture(fixture, deterministic=True)
        self.assertTrue(a.deterministic)
        self.assertEqual(a.replay_timestamp, "2024-01-01T00:00:00+00:00")
        self.assertEqual(a.replay_timestamp, b.replay_timestamp)
        self.assertEqual(a.extracted, b.extracted)
        self.assertEqual(a.selector_used, b.selector_used)
        self.assertEqual(a.quality_flags, b.quality_flags)


if __name__ == "__main__":
    unittest.main()
