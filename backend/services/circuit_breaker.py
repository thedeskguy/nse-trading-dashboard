"""
Simple circuit-breaker for external HTTP clients (yfinance, Angel One).

States:
  CLOSED  — normal operation; failures accumulate.
  OPEN    — all calls are rejected until cooldown_seconds have elapsed.
  HALF-OPEN — first call through after cooldown; resets on success, reopens on failure.
"""
import time
import threading
from dataclasses import dataclass, field


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5     # consecutive failures before opening
    cooldown_seconds: int = 120    # time to wait before trying again

    _failures: int = field(default=0, init=False, repr=False)
    _opened_at: float | None = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def is_open(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return False
            if time.monotonic() - self._opened_at >= self.cooldown_seconds:
                # cooldown elapsed — transition to HALF-OPEN (reset and allow one call)
                self._failures = 0
                self._opened_at = None
                return False
            return True

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._opened_at = time.monotonic()

    def __str__(self) -> str:
        state = "OPEN" if self._opened_at else "CLOSED"
        return f"CircuitBreaker({self.name}, {state}, failures={self._failures})"


# Module-level singletons — shared across the process
yfinance_breaker = CircuitBreaker("yfinance", failure_threshold=5, cooldown_seconds=120)
