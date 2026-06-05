"""
Tests for the Redis-backed idempotency cache + distributed lock
(Tier 2, item 9). Run against fakeredis so CI needs no Redis service; the
same tests pass against a real redis (sanity-checked locally).

These verify the COORDINATION primitives. They do not assert multi-worker
match processing — that needs shared match state (see CONTEXT.md).
"""

from __future__ import annotations

import threading

import pytest

fakeredis = pytest.importorskip("fakeredis")

from runtime import (  # noqa: E402
    IdempotencyCache,
    MatchManager,
    InputEvent,
    RedisIdempotencyCache,
    RedisLock,
    registry,
)

from conftest import FakeWriter, make_players  # noqa: E402
from games.speed_pyramid import Question  # noqa: E402


@pytest.fixture
def r():
    return fakeredis.FakeStrictRedis()


# --- RedisIdempotencyCache ---


def test_redis_idempotency_roundtrip(r):
    cache = RedisIdempotencyCache(r, ttl_seconds=60)
    assert cache.get("k") is None
    cache.put("k", {"score": 42, "nested": [1, 2, 3]})
    assert cache.get("k") == {"score": 42, "nested": [1, 2, 3]}


def test_redis_idempotency_dedupes_real_input(r):
    # Same drop-in test as the in-process cache, but Redis-backed.
    mgr = MatchManager(
        registry=registry,
        writer=FakeWriter(),
        idempotency=RedisIdempotencyCache(r),
    )
    match = mgr.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=make_players(2),
        questions=[
            Question(id=1, setup="s", question="q",
                     answers={"A": "a", "B": "b", "C": "c", "D": "d"},
                     correct="A", category="T", time_limit_ms=10_000),
            Question(id=2, setup="s", question="q",
                     answers={"A": "a", "B": "b", "C": "c", "D": "d"},
                     correct="A", category="T", time_limit_ms=10_000),
        ],
    )
    import json

    ev = InputEvent(puck_index=1, tilt_x=0.0, tilt_y=30.0, button_tap=True)
    first = mgr.on_input(match.id, ev, event_id="e1")
    second = mgr.on_input(match.id, ev, event_id="e1")
    # The replay comes back JSON-normalised (int dict keys -> strings),
    # which is exactly what a client gets over HTTP either way.
    assert second.state == json.loads(json.dumps(first.state))

    writer = mgr.writer
    mp1 = writer.match_pucks[(match.id, "uuid-1")]
    rounds = [s for s in writer.scores
              if s["match_puck_id"] == mp1 and s["event_type"] == "round"]
    assert len(rounds) == 1, "Redis idempotency failed to dedupe the retry"


# --- RedisLock ---


def test_redis_lock_is_mutually_exclusive(r):
    lock = RedisLock(r, ttl_ms=5000, acquire_timeout_s=2.0)
    order = []
    held = threading.Event()
    release = threading.Event()

    def first():
        with lock.lock_for("m1"):
            held.set()
            order.append("first-in")
            release.wait(timeout=2)
            order.append("first-out")

    def second():
        held.wait(timeout=2)  # ensure first holds it
        with lock.lock_for("m1"):
            order.append("second-in")

    t1 = threading.Thread(target=first)
    t2 = threading.Thread(target=second)
    t1.start()
    t2.start()
    # Let second block on the held lock, then release first.
    held.wait(timeout=2)
    release.set()
    t1.join(timeout=3)
    t2.join(timeout=3)

    # second must not enter until after first leaves.
    assert order == ["first-in", "first-out", "second-in"]


def test_redis_lock_different_keys_dont_block(r):
    lock = RedisLock(r, acquire_timeout_s=1.0)
    with lock.lock_for("a"):
        # A different key is independently acquirable while 'a' is held.
        with lock.lock_for("b"):
            pass  # no TimeoutError -> independent


def test_redis_lock_release_only_deletes_own_token(r):
    lock = RedisLock(r, namespace="lock")
    with lock.lock_for("k"):
        # Simulate the lock having expired and been re-taken by someone
        # else: overwrite the key with a foreign token.
        r.set("lock:k", "someone-elses-token")
    # Our release ran the compare-and-delete; the foreign token survives.
    assert r.get("lock:k") in (b"someone-elses-token", "someone-elses-token")
