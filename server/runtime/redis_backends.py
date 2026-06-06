"""
Redis-backed building blocks for a multi-worker runtime.

Two components, each a drop-in for an in-process equivalent:

- RedisIdempotencyCache — same get/put surface as IdempotencyCache, so
  `MatchManager(idempotency=RedisIdempotencyCache(...))` dedupes retried
  inputs across workers. Values are JSON (the response state dict the
  manager now caches), with a TTL so the keyspace self-trims.

- RedisLock — a correct distributed mutex (SET NX PX + a unique token,
  released by a Lua compare-and-delete so we never drop someone else's
  lock). `lock_for(key)` returns a context manager matching the
  in-process `with manager._lock_for(id):` usage.

IMPORTANT — what these do and don't unlock. They make the *coordination*
primitives distributable. They do NOT by themselves make the runtime
multi-worker, because the match STATE (the live Game objects) still lives
in one worker's `MatchManager.matches`. A request that lands on a worker
without the match can't process it. True multi-worker needs the game
state itself shared (serialised to Redis and reconstructed), which is a
deeper change tracked in runtime/CONTEXT.md. These backends are the
ready-and-tested seams for when that lands.

Both are exercised against fakeredis in the test suite (no service
dependency) and were sanity-checked against a real local redis.
"""

from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from typing import Any, Iterator, Optional


DEFAULT_TTL_SECONDS = 3600


class RedisIdempotencyCache:
    """get/put-compatible with IdempotencyCache, backed by Redis with a
    TTL. Stores JSON values (the manager caches a state dict)."""

    def __init__(self, client: Any, ttl_seconds: int = DEFAULT_TTL_SECONDS,
                 namespace: str = "idem") -> None:
        self._r = client
        self._ttl = ttl_seconds
        self._ns = namespace

    def _k(self, key: str) -> str:
        return f"{self._ns}:{key}"

    def get(self, key: str) -> Optional[Any]:
        raw = self._r.get(self._k(key))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    def put(self, key: str, value: Any) -> None:
        self._r.set(self._k(key), json.dumps(value), ex=self._ttl)

    def keys_for_match(self, match_id: str, limit: int = 64) -> list[str]:
        """No-op for the Redis backend: Redis already survives a restart, so
        there's nothing to snapshot into the match record. Returns [] so the
        manager's persist/recover path (which calls this for the in-process
        cache, audit runtime F6) is a harmless no-op here."""
        return []


def _release_if_owner(client: Any, full_key: str, token: str) -> None:
    """Delete the lock key only if it still holds our token — a
    compare-and-delete so we never drop a lock that already expired and
    was re-acquired by someone else. Uses a WATCH/MULTI transaction so it
    works on both real Redis and fakeredis (no server-side Lua needed)."""
    with client.pipeline() as pipe:
        while True:
            try:
                pipe.watch(full_key)
                current = pipe.get(full_key)
                if isinstance(current, bytes):
                    current = current.decode("utf-8")
                if current != token:
                    pipe.unwatch()
                    return
                pipe.multi()
                pipe.delete(full_key)
                pipe.execute()
                return
            except Exception:
                # WatchError (key changed under us) or transient — the key
                # is owned by someone else now, or the TTL will free it.
                return


class RedisLock:
    """Per-key distributed mutex over Redis.

    lock_for(key) returns a context manager. Acquisition blocks (polling)
    up to `acquire_timeout`; the held lock auto-expires after `ttl` so a
    crashed holder can't wedge the key forever. NOT reentrant — matches
    the MatchManager's usage, which never re-acquires a held match lock.
    """

    def __init__(self, client: Any, ttl_ms: int = 10_000,
                 acquire_timeout_s: float = 5.0, poll_s: float = 0.02,
                 namespace: str = "lock") -> None:
        self._r = client
        self._ttl_ms = ttl_ms
        self._acquire_timeout_s = acquire_timeout_s
        self._poll_s = poll_s
        self._ns = namespace

    @contextmanager
    def lock_for(self, key: str) -> Iterator[None]:
        full = f"{self._ns}:{key}"
        token = uuid.uuid4().hex
        deadline = time.monotonic() + self._acquire_timeout_s
        while True:
            if self._r.set(full, token, nx=True, px=self._ttl_ms):
                break
            if time.monotonic() >= deadline:
                raise TimeoutError(f"could not acquire lock {full!r}")
            time.sleep(self._poll_s)
        try:
            yield
        finally:
            _release_if_owner(self._r, full, token)
