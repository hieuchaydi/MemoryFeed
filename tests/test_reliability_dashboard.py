from __future__ import annotations

import unittest

from backend.stats import build_reliability_dashboard


class ReliabilityDashboardTests(unittest.TestCase):
    def test_dashboard_aggregates_local_metrics(self) -> None:
        payload = build_reliability_dashboard(
            items=[
                {"capture_confidence": 0.8, "quality_flags": ["missing_text"], "capture_debug": {"fallback_selector_used": True}},
                {"capture_confidence": 1.0, "quality_flags": [], "capture_debug": {}},
            ],
            capture_reliability=[{"platform": "twitter", "success_rate": 0.9}],
            replay_history=[{"date": "2026-05-09", "score": 0.95}],
        )
        self.assertIn("duplicate_rate", payload)
        self.assertIn("capture_confidence_avg", payload)
        self.assertIn("selector_fallback_usage", payload)
        self.assertIn("replay_benchmark_history", payload)


if __name__ == "__main__":
    unittest.main()
