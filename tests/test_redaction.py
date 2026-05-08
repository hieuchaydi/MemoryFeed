from __future__ import annotations

import unittest

from backend.redaction import redact_text, redact_value


class RedactionTests(unittest.TestCase):
    def test_redact_text_masks_common_sensitive_patterns(self) -> None:
        text = "Contact me at alice@example.com, +1 (555) 123-4567, Bearer supersecrettoken123456789, sk_ABCDEF1234567890"
        redacted = redact_text(text)
        self.assertNotIn("alice@example.com", redacted)
        self.assertIn("[REDACTED_EMAIL]", redacted)
        self.assertIn("[REDACTED_PHONE]", redacted)
        self.assertIn("Bearer [REDACTED_TOKEN]", redacted)
        self.assertIn("[REDACTED_KEY]", redacted)

    def test_redact_value_handles_nested_structures(self) -> None:
        payload = {
            "email": "bob@example.org",
            "items": ["+44 7700 900123", {"token": "Bearer abcd1234abcd1234abcd1234"}],
        }
        redacted = redact_value(payload)
        self.assertEqual(redacted["email"], "[REDACTED_EMAIL]")
        self.assertEqual(redacted["items"][0], "[REDACTED_PHONE]")
        self.assertEqual(redacted["items"][1]["token"], "Bearer [REDACTED_TOKEN]")


if __name__ == "__main__":
    unittest.main()
