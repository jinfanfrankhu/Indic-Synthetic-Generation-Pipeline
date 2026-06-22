"""
Rate limiting.

NVIDIA Build's free tier caps the account at ~40 API calls/minute. Rather than
relying on every call site to pace itself, :class:`RateLimiter` enforces a
minimum spacing between call *starts* shared across threads, so the cap holds no
matter how many workers a batch dispatches.

The limiter serializes only the moment a call is *granted* (it sleeps under a
lock until enough time has elapsed since the previous grant); the requests
themselves still overlap in flight, so concurrency still helps throughput up to
the cadence ceiling. This is proactive — :class:`~syndata.client.NvidiaClient`
keeps its reactive 429 backoff as a safety net underneath it.
"""
from __future__ import annotations

import threading
import time


class RateLimiter:
    """Thread-safe min-interval throttle.

    ``calls_per_minute`` is the sustained ceiling; the limiter spaces grants at
    least ``60 / calls_per_minute`` seconds apart. Default 36/min sits under the
    40/min account cap with margin for clock jitter and the occasional retry.
    """

    def __init__(self, calls_per_minute: float = 36.0) -> None:
        if calls_per_minute <= 0:
            raise ValueError("calls_per_minute must be positive")
        self._min_interval = 60.0 / calls_per_minute
        self._lock = threading.Lock()
        # Last grant time on the monotonic clock; -inf so the first call is free.
        self._last_grant = float("-inf")

    def acquire(self) -> None:
        """Block until the next call is allowed to start, then record the grant."""
        with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_grant)
            if wait > 0:
                time.sleep(wait)
                now = time.monotonic()
            self._last_grant = now
