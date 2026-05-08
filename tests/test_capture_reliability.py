from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from backend.capture import normalize_capture
from backend.models import CaptureRequest
from backend.store import Store


class CaptureReliabilityTests(unittest.TestCase):
    def test_platform_happy_path_normalization(self) -> None:
        cases = [
            {
                "platform": "facebook",
                "url": "https://www.facebook.com/some.user/posts/1234567890?utm_source=feed",
                "expected_canonical": "https://facebook.com/some.user/posts/1234567890",
                "post_id": "1234567890",
            },
            {
                "platform": "twitter",
                "url": "https://x.com/alice/status/1928374655647382910?t=abc",
                "expected_canonical": "https://x.com/alice/status/1928374655647382910",
                "post_id": "1928374655647382910",
            },
            {
                "platform": "youtube",
                "url": "https://youtu.be/abc123XYZ90?si=share",
                "expected_canonical": "https://youtube.com/watch?v=abc123XYZ90",
                "post_id": "abc123XYZ90",
            },
            {
                "platform": "linkedin",
                "url": "https://www.linkedin.com/feed/update/urn:li:activity:1234567890/?utm_source=share",
                "expected_canonical": "https://linkedin.com/feed/update/urn:li:activity:1234567890",
                "post_id": "urn:li:activity:1234567890",
            },
            {
                "platform": "tiktok",
                "url": "https://www.tiktok.com/@creator/video/1234567890123456789?lang=en",
                "expected_canonical": "https://tiktok.com/@creator/video/1234567890123456789",
                "post_id": "1234567890123456789",
            },
        ]

        captured_at = datetime(2026, 5, 8, 10, 30, tzinfo=timezone.utc)
        for case in cases:
            with self.subTest(platform=case["platform"]):
                payload = CaptureRequest(
                    url=case["url"],
                    platform=case["platform"],
                    text_content="Sample post text",
                    media_urls=["https://cdn.example.com/image.jpg"],
                    author_name="Author",
                    captured_at=captured_at,
                )
                out = normalize_capture(payload)
                self.assertEqual(out["platform"], case["platform"])
                self.assertEqual(out["canonical_url"], case["expected_canonical"])
                self.assertEqual(out["post_id"], case["post_id"])
                self.assertEqual(out["author_name"], "Author")
                self.assertEqual(out["media_urls"], ["https://cdn.example.com/image.jpg"])
                self.assertNotIn("missing_platform", out["quality_flags"])

    def test_missing_fields_emit_quality_flags(self) -> None:
        payload = CaptureRequest(
            url="https://x.com/alice/status/1010101010101010101",
            platform="twitter",
            text_content="",
            media_urls=[],
            author_name=None,
            captured_at=datetime(2026, 5, 8, 10, 30, tzinfo=timezone.utc),
        )
        out = normalize_capture(payload)
        self.assertIn("missing_author_name", out["quality_flags"])
        self.assertIn("missing_text", out["quality_flags"])
        self.assertIn("missing_media_urls", out["quality_flags"])

    def test_duplicate_fingerprint_within_time_bucket(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-capture-reliability-") as tmp:
            store = Store(db_path=Path(tmp) / "memoryfeed.db")
            captured_at = datetime(2026, 5, 8, 11, 5, tzinfo=timezone.utc)

            payload1 = CaptureRequest(
                url="https://x.com/alice/status/1928374655647382910?t=aaa",
                platform="twitter",
                text_content="Docker networking post",
                media_urls=["https://cdn.example.com/1.jpg"],
                author_name="alice",
                captured_at=captured_at,
            )
            payload2 = CaptureRequest(
                url="https://x.com/alice/status/1928374655647382910?t=bbb",
                platform="twitter",
                text_content="Docker networking post",
                media_urls=["https://cdn.example.com/2.jpg"],
                author_name="alice",
                captured_at=captured_at,
            )

            first = normalize_capture(payload1)
            second = normalize_capture(payload2)

            inserted_1, _ = store.insert_item(first)
            inserted_2, duplicate_id = store.insert_item(second)

            self.assertTrue(inserted_1)
            self.assertFalse(inserted_2)
            self.assertIsNotNone(duplicate_id)


if __name__ == "__main__":
    unittest.main()
