from __future__ import annotations

import unittest
from pathlib import Path


class SelectorRegistryValidationTests(unittest.TestCase):
    def test_content_scripts_include_selector_validation_guards(self) -> None:
        for path in [Path("extension/chrome/content.js"), Path("extension/firefox/content.js")]:
            with self.subTest(file=str(path)):
                text = path.read_text(encoding="utf-8")
                self.assertIn("selector config for", text)
                self.assertIn("normalizeConfig(raw, fallbackCfg, platformName)", text)
                self.assertIn("candidate_selector", text)
                self.assertIn("fallback_selectors", text)


if __name__ == "__main__":
    unittest.main()
