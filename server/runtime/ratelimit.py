"""
Token-bucket rate limiting, per (match_id, puck_index).

A misbehaving or malicious puck firmware can spray input at the match
endpoint far faster than the 10 Hz the game needs, burning Flask CPU and
flooding the snapshot write path. A token bucket per puck caps the
sustained rate while still allowing a short burst (legitimate retries, a
laggy batch catching up).

Keyed by (match_id, puck_index) so one chatty puck can't starve another,
and so the limit travels with the puck across the match. Enforced AFTER
auth in the route, so unauthenticated floods are cheaply rejected without
consuming a real puck's bucket.

In-process for the pilot; a multi-worker deployment shares the buckets in
Redis with the same key and a Lua refill script.
"""

from __future__ import annotations

import threading
import time
from typing import Callable


# Defaults: the runtime ticks at 10 Hz and a puck rarely needs to send
# faster, so 20/s sustained with a 40-token burst is generous headroom
# while still bounding abuse. Tunable via the container.
DEFAULT_RATE_PER_SEC = 20.0
DEFAULT_BURST = 40.0


class RateLimiter:
    def __init__(
        self,
        rate_per_sec: float = DEFAULT_RATE_PER_SEC,
        burst: float = DEFAULT_BURST,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        if rate_per_sec <= 0 or burst <= 0:
            raise ValueError("rate_per_sec and burst must be positive")
        self.rate = rate_per_sec
        self.burst = burst
        self._now = now
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """Consume one token for key. Returns True if a token was
        available (request allowed), False if the bucket is empty
        (rate-limited)."""
        now = self._now()
        with self._lock:
            tokens, last = self._buckets.get(key, (self.burst, now))
            # Refill proportionally to elapsed time, capped at burst.
            tokens = min(self.burst, tokens + (now - last) * self.rate)
            if tokens >= 1.0:
                self._buckets[key] = (tokens - 1.0, now)
                return True
            self._buckets[key] = (tokens, now)
            return False

    def drop(self, key_prefix: str) -> None:
        """Forget buckets whose key starts with key_prefix — called when a
        match finalises so the map doesn't accumulate dead pucks."""
        with self._lock:
            for key in [k for k in self._buckets if k.startswith(key_prefix)]:
                del self._buckets[key]
