from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.research_eval import load_failure_cases, load_scenarios, write_markdown_summary


class ResearchEvalTests(unittest.TestCase):
    def test_load_failure_cases(self) -> None:
        rows = load_failure_cases()
        self.assertTrue(isinstance(rows, list))

    def test_write_markdown_summary(self) -> None:
        report = {
            "generated_at": "2026-05-09T00:00:00+00:00",
            "metrics": {
                "latency_ms_p50": 120.0,
                "latency_ms_p95": 340.0,
                "retrieval_precision_at_5": 0.6,
                "memory_hit_quality": 0.7,
                "token_reduction_percent": 42.0,
                "pass_rate": 0.8,
            },
            "failure_cases": [{"name": "x", "risk": "y", "pass": True, "has_expected": True, "has_banned": False}],
        }
        with tempfile.TemporaryDirectory(prefix="memoryfeed-research-") as tmp:
            out = write_markdown_summary(report, out_dir=Path(tmp))
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
