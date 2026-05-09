from __future__ import annotations

import unittest

from backend.url_normalization import canonicalize_url


class CanonicalUrlTests(unittest.TestCase):
    def test_youtube_keeps_timestamp_and_playlist(self) -> None:
        raw = "https://www.youtube.com/watch?v=abc123&t=92&list=PL123&utm_source=feed&token=secret"
        out = canonicalize_url(raw, platform="youtube")
        self.assertEqual(out, "https://youtube.com/watch?v=abc123&t=92&list=PL123")

    def test_youtu_be_short_url_keeps_meaningful_params(self) -> None:
        raw = "https://youtu.be/abc123?si=share&t=41"
        out = canonicalize_url(raw, platform="youtube")
        self.assertEqual(out, "https://youtube.com/watch?v=abc123&t=41")

    def test_facebook_keeps_comment_selector(self) -> None:
        raw = "https://www.facebook.com/some.user/posts/111?comment_id=222&utm_medium=social"
        out = canonicalize_url(raw, platform="facebook")
        self.assertEqual(out, "https://facebook.com/some.user/posts/111?comment_id=222")

    def test_strips_tracking_and_sensitive_params(self) -> None:
        raw = "https://example.com/page?utm_source=x&session=abc123&auth=token&q=hello"
        out = canonicalize_url(raw, platform="unknown")
        self.assertEqual(out, "https://example.com/page?q=hello")

    def test_tiktok_mobile_url_normalization(self) -> None:
        raw = "https://m.tiktok.com/@creator/video/1234567890?lang=en&fbclid=abc"
        out = canonicalize_url(raw, platform="tiktok")
        self.assertEqual(out, "https://m.tiktok.com/@creator/video/1234567890")


if __name__ == "__main__":
    unittest.main()
