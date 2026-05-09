from __future__ import annotations

import unittest
from pathlib import Path

from backend.extractor_replay import replay_fixture


class ExtractorReplayTests(unittest.TestCase):
    def test_replay_reports_selector_and_quality_flags(self) -> None:
        result = replay_fixture(Path("tests/fixtures/twitter_basic.html"))
        self.assertIn("selector_used", result.__dict__)
        self.assertEqual(result.quality_flags, [])
        self.assertTrue(result.matches_expected)


if __name__ == "__main__":
    unittest.main()
