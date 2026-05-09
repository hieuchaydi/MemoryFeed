from __future__ import annotations

import unittest
from pathlib import Path

from backend.extractor_replay import test_platform_fixtures


class RealWorldFixtureTests(unittest.TestCase):
    def test_platform_fixture_directories_have_minimum_samples(self) -> None:
        root = Path("tests/fixtures")
        for platform in ["facebook", "twitter", "youtube", "linkedin", "tiktok"]:
            with self.subTest(platform=platform):
                files = list((root / platform).glob("*.html"))
                self.assertGreaterEqual(len(files), 3)

    def test_platform_fixture_replay_reports(self) -> None:
        for platform in ["facebook", "twitter", "youtube", "linkedin", "tiktok"]:
            with self.subTest(platform=platform):
                report = test_platform_fixtures(platform, deterministic=True)
                self.assertGreaterEqual(report["fixtures"], 3)
                self.assertEqual(report["failed"], 0)


if __name__ == "__main__":
    unittest.main()
