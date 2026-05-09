from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class CircuitBreakerState:
    name: str
    status: str
    failure_count: int
    opened_at: float | None
    cooldown_seconds: float


class CircuitBreakerOpen(Exception):
    pass


class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 5, cooldown_seconds: float = 30.0) -> None:
        self.name = name
        self.failure_threshold = max(1, int(failure_threshold))
        self.cooldown_seconds = max(1.0, float(cooldown_seconds))
        self._failure_count = 0
        self._opened_at: float | None = None
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return True
            if (time.monotonic() - self._opened_at) >= self.cooldown_seconds:
                # half-open trial
                self._opened_at = None
                self._failure_count = 0
                return True
            return False

    def on_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._opened_at = None

    def on_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._opened_at = time.monotonic()

    def state(self) -> CircuitBreakerState:
        with self._lock:
            status = "open" if self._opened_at is not None else "closed"
            return CircuitBreakerState(
                name=self.name,
                status=status,
                failure_count=self._failure_count,
                opened_at=self._opened_at,
                cooldown_seconds=self.cooldown_seconds,
            )


def backoff_seconds(attempt: int, base: float = 0.8, cap: float = 30.0) -> float:
    n = max(1, int(attempt))
    return min(float(cap), float(base) * (2 ** (n - 1)))
