from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.benchmarking import build_benchmark_rows, write_benchmark_snapshot


class BenchmarkingTests(unittest.TestCase):
    def test_build_benchmark_rows(self) -> None:
        rows = build_benchmark_rows(
            {
                "twitter": {"attempts": 100, "stored": 94, "duplicates": 3, "missing": 2},
                "youtube": {"attempts": 50, "stored": 45, "duplicates": 2, "missing": 1},
            },
            version="0.4.0",
        )
        self.assertEqual(len(rows), 2)
        twitter = next(row for row in rows if row["platform"] == "twitter")
        self.assertEqual(twitter["version"], "0.4.0")
        self.assertAlmostEqual(twitter["success_rate"], 0.94)
        self.assertAlmostEqual(twitter["duplicate_rate"], 0.03)

    def test_write_snapshot_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-bench-") as tmp:
            bench_dir = Path(tmp) / "benchmarks"
            with patch("backend.benchmarking.BENCHMARK_DIR", bench_dir):
                path = write_benchmark_snapshot({"twitter": {"attempts": 10, "stored": 9, "duplicates": 1, "missing": 0}}, "0.4.0")
            self.assertTrue(path.exists())
            self.assertIn("benchmark-", path.name)


if __name__ == "__main__":
    unittest.main()
