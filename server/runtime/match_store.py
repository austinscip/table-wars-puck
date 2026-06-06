"""
Match stores — durable persistence of active-match snapshots.

A store is a dumb key/value-plus-index: it holds the serialized form of a
Match (produced by match.serialize_match) under the match id, and tracks
the set of active ids so a freshly-booted MatchManager can recover them.
The store knows nothing about Match internals — the manager does the
serialize/deserialize, the store just persists dicts.

Two implementations:
- InMemoryMatchStore — for tests / a single process that wants explicit
  persistence semantics without Redis.
- RedisMatchStore — survives a server restart and is shared across
  workers (the foundation for distributing match state; see CONTEXT.md).
"""

from __future__ import annotations

import json
import threading
from typing import Any, Optional


class InMemoryMatchStore:
    def __init__(self) -> None:
        self._data: dict[str, dict] = {}
        self._lock = threading.Lock()

    def save(self, match_id: str, data: dict) -> None:
        with self._lock:
            self._data[match_id] = data

    def load(self, match_id: str) -> Optional[dict]:
        with self._lock:
            return self._data.get(match_id)

    def load_all_ids(self) -> list[str]:
        with self._lock:
            return list(self._data.keys())

    def delete(self, match_id: str) -> None:
        with self._lock:
            self._data.pop(match_id, None)


class RedisMatchStore:
    """Persists serialized matches to Redis with an `active` set index."""

    def __init__(self, client: Any, namespace: str = "match") -> None:
        self._r = client
        self._ns = namespace

    def _k(self, match_id: str) -> str:
        return f"{self._ns}:{match_id}"

    def _index(self) -> str:
        return f"{self._ns}:active"

    def save(self, match_id: str, data: dict) -> None:
        # allow_nan=False so a stray NaN/Inf physics float surfaces LOUDLY
        # here (caught by the caller's persist try/except) instead of being
        # written as a non-standard JSON token that poisons the durable copy
        # and either fails a strict reader or hangs the game's comparisons on
        # reload (audit runtime-games-2026-06-06).
        payload = json.dumps(data, allow_nan=False)
        # Pipeline the key write + index add so a kill -9 can't land BETWEEN
        # them (data written but id absent from the active set -> the match is
        # silently not recovered). MULTI/EXEC makes the pair atomic.
        pipe = self._r.pipeline()
        pipe.set(self._k(match_id), payload)
        pipe.sadd(self._index(), match_id)
        pipe.execute()

    def load(self, match_id: str) -> Optional[dict]:
        raw = self._r.get(self._k(match_id))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    def load_all_ids(self) -> list[str]:
        members = self._r.smembers(self._index())
        return [m.decode("utf-8") if isinstance(m, bytes) else m for m in members]

    def delete(self, match_id: str) -> None:
        self._r.delete(self._k(match_id))
        self._r.srem(self._index(), match_id)
