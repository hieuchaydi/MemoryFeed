from __future__ import annotations

import time
import unittest

from backend.resilience import CircuitBreaker, backoff_seconds


class ResilienceTests(unittest.TestCase):
    def test_backoff_growth(self) -> None:
        self.assertAlmostEqual(backoff_seconds(1, base=0.5, cap=10.0), 0.5)
        self.assertAlmostEqual(backoff_seconds(2, base=0.5, cap=10.0), 1.0)
        self.assertAlmostEqual(backoff_seconds(3, base=0.5, cap=10.0), 2.0)

    def test_circuit_breaker_opens_and_recovers(self) -> None:
        cb = CircuitBreaker("test", failure_threshold=2, cooldown_seconds=1.0)
        self.assertTrue(cb.allow())
        cb.on_failure()
        self.assertTrue(cb.allow())
        cb.on_failure()
        self.assertFalse(cb.allow())
        time.sleep(1.05)
        self.assertTrue(cb.allow())


if __name__ == "__main__":
    unittest.main()
