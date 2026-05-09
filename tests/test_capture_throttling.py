from __future__ import annotations

import unittest
from pathlib import Path


class CaptureThrottlingTests(unittest.TestCase):
    def test_content_script_has_debounce_visibility_rate_limit_controls(self) -> None:
        text = Path("extension/chrome/content.js").read_text(encoding="utf-8")
        self.assertIn("MEMORY_CAPTURE_MIN_VISIBLE_MS", text)
        self.assertIn("MEMORY_CAPTURE_DEBOUNCE_MS", text)
        self.assertIn("MEMORY_CAPTURE_MAX_ATTEMPTS_PER_MINUTE", text)
        self.assertIn("allowCaptureAttempt(", text)
        self.assertIn("captureAttemptTimeline", text)
        self.assertIn("minDwellMsForPlatform()", text)


if __name__ == "__main__":
    unittest.main()
