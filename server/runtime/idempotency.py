"""
IdempotencyCache — a bounded, thread-safe LRU so a retried puck request
isn't processed twice.

Why this exists: pucks talk to Flask over plain HTTP on bar Wi-Fi. A
flaky link means the firmware retries a POST it already delivered — the
score lands twice, the lock-in fires twice, the boost is spent twice.
The fix is an idempotency key: the firmware stamps each *logical* event
with a stable id; the server processes the first arrival and replays the
same response for any retry of that id.

Keyed by an opaque string (the caller composes
`f"{match_id}:{puck_index}:{event_id}"`). Bounded so a long-running
server doesn't grow the map without limit; the oldest entries fall off
once `maxsize` is reached, which is safe because a retry old enough to
have been evicted is also old enough that re-processing is harmless (the
match has long since moved on or finalised).

Single in-process for now, like the rest of the runtime. A multi-worker
deployment shares this in Redis with `SETNX` + TTL and the same key.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any, Optional


# Default capacity. At pilot scale (one bar, a handful of pucks at a few
# Hz) this holds many minutes of history — far longer than any realistic
# retry window.
DEFAULT_MAXSIZE = 8192


class IdempotencyCache:
    def __init__(self, maxsize: int = DEFAULT_MAXSIZE) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be >= 1")
        self._maxsize = maxsize
        self._store: "OrderedDict[str, Any]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Return the cached value for key, or None if unseen. Touches the
        entry so it's treated as recently used."""
        with self._lock:
            if key not in self._store:
                return None
            self._store.move_to_end(key)
            return self._store[key]

    def put(self, key: str, value: Any) -> None:
        """Record value under key, evicting the oldest entry if the cache
        is full. A re-put of an existing key refreshes both its value and
        its recency."""
        with self._lock:
            self._store[key] = value
            self._store.move_to_end(key)
            while len(self._store) > self._maxsize:
                self._store.popitem(last=False)

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._store

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
