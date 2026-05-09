from __future__ import annotations

import unittest

from backend.capture_quality import compute_capture_confidence


class CaptureConfidenceTests(unittest.TestCase):
    def test_high_confidence_capture(self) -> None:
        score, reasons = compute_capture_confidence(
            {
                "url": "https://x.com/alice/status/1",
                "canonical_url": "https://x.com/alice/status/1",
                "platform": "twitter",
                "post_id": "1",
                "text_content": "MemoryFeed reliability hardening note.",
                "media_urls": ["https://cdn.example.com/1.jpg"],
                "author_name": "alice",
                "quality_flags": [],
                "capture_debug": {"selector_used": {"text": "[data-testid=tweetText]"}},
            }
        )
        self.assertGreaterEqual(score, 0.85)
        self.assertEqual(reasons, [])

    def test_low_confidence_capture_contains_reasons(self) -> None:
        score, reasons = compute_capture_confidence(
            {
                "url": "https://example.com/post",
                "canonical_url": "",
                "platform": "unknown",
                "post_id": "",
                "text_content": "",
                "media_urls": [],
                "author_name": "",
                "quality_flags": ["missing_text", "missing_author_name"],
                "capture_debug": {"selector_used": {"text": "fallback:none", "author_name": "fallback:none"}},
            }
        )
        self.assertLess(score, 0.5)
        self.assertIn("missing_text", reasons)
        self.assertIn("missing_author", reasons)
        self.assertIn("fallback_selector_used:text", reasons)


if __name__ == "__main__":
    unittest.main()
