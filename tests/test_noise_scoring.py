from __future__ import annotations

import unittest

from backend.noise import classify_noise


class NoiseScoringTests(unittest.TestCase):
    def test_noise_classifier_flags_engagement_bait(self) -> None:
        score, reason = classify_noise({"text_content": "Like and subscribe now for free money airdrop"})
        self.assertGreater(score, 0.4)
        self.assertIsNotNone(reason)


if __name__ == "__main__":
    unittest.main()
