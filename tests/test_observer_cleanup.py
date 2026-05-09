from __future__ import annotations

import unittest
from pathlib import Path


class ObserverCleanupTests(unittest.TestCase):
    def test_content_script_has_centralized_cleanup_lifecycle(self) -> None:
        text = Path("extension/chrome/content.js").read_text(encoding="utf-8")
        self.assertIn("cleanupRegistry", text)
        self.assertIn("clearAllRuntime()", text)
        self.assertIn("registerObserver(", text)
        self.assertIn("registerInterval(", text)
        self.assertIn("memoryfeed:route-change", text)


if __name__ == "__main__":
    unittest.main()
