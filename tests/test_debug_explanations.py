from __future__ import annotations

import unittest

from backend.debug import (
    explain_archival_decision,
    explain_confidence_reduction,
    explain_duplicate_decision,
    explain_ranking_penalties,
)


class DebugExplanationTests(unittest.TestCase):
    def test_debug_explanations_are_human_readable(self) -> None:
        item = {
            "dedupe_key": "abcdef1234567890",
            "canonical_url": "https://example.com/post",
            "aging_state": "cooling",
            "decay_score": 0.6,
            "quality_flags": ["missing_author_name"],
        }
        self.assertIn("dedupe_key", explain_duplicate_decision(item))
        self.assertIn("aging_state", explain_archival_decision(item))
        self.assertIn("missing_fields", explain_confidence_reduction(item))
        penalties = explain_ranking_penalties({"duplicate_penalty": 0.2})
        self.assertIn("duplicate_penalty", penalties)


if __name__ == "__main__":
    unittest.main()
