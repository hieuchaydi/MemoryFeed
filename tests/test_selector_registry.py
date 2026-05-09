from __future__ import annotations

import json
import unittest
from pathlib import Path


class SelectorRegistryTests(unittest.TestCase):
    def test_selector_files_exist_and_have_required_fields(self) -> None:
        root = Path("extension/selectors")
        required_platforms = ["facebook", "twitter", "youtube", "linkedin", "tiktok"]
        for platform in required_platforms:
            with self.subTest(platform=platform):
                path = root / f"{platform}.json"
                self.assertTrue(path.exists(), msg=f"Missing selector file: {path}")
                payload = json.loads(path.read_text(encoding="utf-8"))
                for key in [
                    "candidate_selector",
                    "text_selectors",
                    "author_selectors",
                    "author_handle_selectors",
                    "canonical_url_selectors",
                    "media_selectors",
                    "fallback_selectors",
                ]:
                    self.assertIn(key, payload)
                self.assertIsInstance(payload["text_selectors"], list)
                self.assertIsInstance(payload["fallback_selectors"], dict)

    def test_selector_files_copied_to_browser_extension_roots(self) -> None:
        names = ["facebook.json", "twitter.json", "youtube.json", "linkedin.json", "tiktok.json"]
        for name in names:
            with self.subTest(file=name):
                self.assertTrue((Path("extension/chrome/selectors") / name).exists())
                self.assertTrue((Path("extension/firefox/selectors") / name).exists())


if __name__ == "__main__":
    unittest.main()
