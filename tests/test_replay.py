from __future__ import annotations

import unittest
from pathlib import Path

from backend.extractor_replay import replay_fixture, test_platform_fixtures


class ReplayTests(unittest.TestCase):
    def test_replay_fixture_matches_expected_snapshot(self) -> None:
        fixture = Path("tests/fixtures/twitter_basic.html")
        result = replay_fixture(fixture)
        self.assertTrue(result.matches_expected)
        self.assertEqual(result.platform, "twitter")
        self.assertEqual(result.missing_fields, [])
        self.assertIn("text", result.selector_used)

    def test_platform_fixture_report(self) -> None:
        report = test_platform_fixtures("twitter")
        self.assertGreaterEqual(report["fixtures"], 1)
        self.assertEqual(report["failed"], 0)


if __name__ == "__main__":
    unittest.main()
