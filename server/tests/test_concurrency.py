"""
Regression tests for the per-match lock (review Open 3.2 / Tier 2 seam)
and the duplicate-puck guard (review Open 2.3).

The lock serialises every mutation of a match's state so the scheduler
thread (tick) and Flask request threads (on_input) can't race on game
internals or on the idempotency check-then-act. These drive real
concurrency through the MatchManager.
"""

from __future__ import annotations

import threading

import pytest

from runtime import IdempotencyCache, InputEvent, MatchManager, Player, registry

from conftest import FakeWriter, make_players
from games.speed_pyramid import Question


def _fixture(n=6):
    return [
        Question(
            id=i,
            setup="s",
            question="q",
            answers={"A": "a", "B": "b", "C": "c", "D": "d"},
            correct="A",
            category="T",
            time_limit_ms=10_000,
        )
        for i in range(1, n + 1)
    ]


# ---------------------------------------------------------------------------
# Duplicate puck_index guard
# ---------------------------------------------------------------------------


def test_duplicate_puck_index_rejected(manager, writer):
    dupes = [
        Player(puck_uuid="u1", puck_index=1, name="A", color="#111"),
        Player(puck_uuid="u2", puck_index=1, name="B", color="#222"),
    ]
    with pytest.raises(ValueError, match="duplicate puck_index"):
        manager.create(
            location_id="loc",
            game_slug="speed_pyramid",
            table_number=1,
            players=dupes,
            questions=_fixture(),
        )
    # Rejected before any DB write.
    assert writer.matches == []
    assert manager.matches == {}


# ---------------------------------------------------------------------------
# Per-match lock
# ---------------------------------------------------------------------------


def test_concurrent_duplicate_input_processed_once():
    """Many threads fire the SAME idempotency key at once. With the lock
    holding the check-then-act atomic, exactly one is applied — no
    double-counted score under contention."""
    writer = FakeWriter()
    mgr = MatchManager(
        registry=registry, writer=writer, idempotency=IdempotencyCache()
    )
    players = make_players(2)
    match = mgr.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=players,
        questions=_fixture(),
    )

    ev = InputEvent(puck_index=1, tilt_x=0.0, tilt_y=30.0, button_tap=True)
    start = threading.Barrier(20)

    def fire():
        start.wait()  # release all threads at once for maximum contention
        mgr.on_input(match.id, ev, event_id="same-key")

    threads = [threading.Thread(target=fire) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    mp1 = writer.match_pucks[(match.id, "uuid-1")]
    round_scores = [
        s
        for s in writer.scores
        if s["match_puck_id"] == mp1 and s["event_type"] == "round"
    ]
    assert len(round_scores) == 1, (
        f"duplicate key applied {len(round_scores)} times under concurrency"
    )


def test_concurrent_distinct_pucks_no_lost_updates():
    """Two pucks hammering on_input concurrently must each land their
    lock-in for the round — no update lost to a race on game state."""
    writer = FakeWriter()
    mgr = MatchManager(registry=registry, writer=writer)
    players = make_players(2)
    match = mgr.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=players,
        questions=_fixture(),
    )
    game = match.game
    start = threading.Barrier(2)

    def answer(puck):
        start.wait()
        mgr.on_input(
            match.id,
            InputEvent(puck_index=puck, tilt_x=0.0, tilt_y=30.0, button_tap=True),
        )

    t1 = threading.Thread(target=answer, args=(1,))
    t2 = threading.Thread(target=answer, args=(2,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Both locked in -> round advanced exactly once. (Pre-lock, a race on
    # _all_locked / _advance_round could double-advance or drop a lock.)
    assert game.round_index == 1
    mp1 = writer.match_pucks[(match.id, "uuid-1")]
    mp2 = writer.match_pucks[(match.id, "uuid-2")]
    assert any(s["match_puck_id"] == mp1 and s["event_type"] == "round" for s in writer.scores)
    assert any(s["match_puck_id"] == mp2 and s["event_type"] == "round" for s in writer.scores)


def test_injected_lock_provider_is_used():
    """on_input/tick go through an injected distributed lock provider (the
    seam a RedisLock plugs into) instead of the in-process RLock."""
    from contextlib import contextmanager

    class RecordingLockProvider:
        def __init__(self):
            self.acquired: list[str] = []

        @contextmanager
        def lock_for(self, key):
            self.acquired.append(key)
            yield

    lp = RecordingLockProvider()
    writer = FakeWriter()
    mgr = MatchManager(registry=registry, writer=writer, lock_provider=lp)
    match = mgr.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=make_players(2),
        questions=_fixture(),
    )
    mgr.on_input(match.id, InputEvent(puck_index=1, tilt_y=30.0, button_tap=True))
    mgr.tick(match.id)
    # Both on_input and tick acquired the injected lock for this match.
    assert lp.acquired.count(match.id) >= 2


def test_match_lock_dropped_on_finalize():
    """The per-match lock entry is released once the match is terminal so
    the lock map doesn't grow without bound across many matches."""
    writer = FakeWriter()
    mgr = MatchManager(registry=registry, writer=writer)
    players = make_players(1)
    match = mgr.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=players,
        questions=_fixture(n=1),  # single question -> finishes in one answer
    )
    # Touch the lock so it exists.
    mgr.on_input(
        match.id,
        InputEvent(puck_index=1, tilt_x=0.0, tilt_y=30.0, button_tap=True),
    )
    assert match.game.is_over()
    assert match.id not in mgr._match_locks
