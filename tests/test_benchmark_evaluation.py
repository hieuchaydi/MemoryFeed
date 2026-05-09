from __future__ import annotations

import unittest

from backend.benchmarking import evaluate_memory_retrieval


class BenchmarkEvalTests(unittest.TestCase):
    def test_evaluate_memory_retrieval(self) -> None:
        dataset = [
            {"query": "docker", "must_include_any": ["docker"], "type": "long_term_recall"},
            {"query": "preference", "must_include_any": ["favorite"], "type": "consistency"},
        ]
        retrieved = [
            {"id": "1", "text_content": "docker compose setup"},
            {"id": "2", "text_content": "my favorite editor"},
        ]
        report = evaluate_memory_retrieval(dataset, retrieved)
        self.assertEqual(report["total_cases"], 2)
        self.assertAlmostEqual(report["metrics"]["recall_at_k"], 1.0)


if __name__ == "__main__":
    unittest.main()
