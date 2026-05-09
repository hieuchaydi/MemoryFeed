from __future__ import annotations

import io
import json
import logging
import unittest

from backend.logging import log_event


class LoggingSafetyTests(unittest.TestCase):
    def test_log_event_redacts_and_strips_sensitive_query(self) -> None:
        stream = io.StringIO()
        logger = logging.getLogger("memoryfeed-test-logging")
        logger.handlers = []
        logger.propagate = False
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        log_event(
            logger,
            "capture_attempt",
            platform="twitter",
            duplicate_reason="Bearer abcdefghijklmnopqrstuvwxyz",
            benchmark_context={
                "url": "https://example.com/page?token=abc123&auth=x&safe=ok",
                "note": "x" * 1200,
            },
        )

        raw = stream.getvalue().strip()
        payload = json.loads(raw)
        self.assertEqual(payload["event_type"], "capture_attempt")
        encoded = json.dumps(payload)
        self.assertNotIn("token=abc123", encoded)
        self.assertNotIn("auth=x", encoded)
        self.assertIn("[REDACTED_TOKEN]", encoded)
        self.assertIn("[truncated]", encoded)


if __name__ == "__main__":
    unittest.main()
