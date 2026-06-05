"""
Regression tests for input idempotency (Tier 1, item 5).

A retried puck request — same logical event_id from the same puck in the
same match — must be processed exactly once. The harm otherwise is a
double-counted score / double lock-in on a network retry. Drives the real
MatchManager.on_input path with an IdempotencyCache wired in.
"""

from __future__ import annotations

from runtime import IdempotencyCache, InputEvent, MatchManager, registry

from conftest import FakeWriter, make_players
from games.speed_pyramid import Question


def _make_manager():
    writer = FakeWriter()
    mgr = MatchManager(
        registry=registry, writer=writer, idempotency=IdempotencyCache()
    )
    return mgr, writer


def _fixture():
    return [
        Question(
            id=1,
            setup="s",
            question="q",
            answers={"A": "a", "B": "b", "C": "c", "D": "d"},
            correct="A",
            category="T",
            time_limit_ms=10_000,
        ),
        Question(
            id=2,
            setup="s2",
            question="q2",
            answers={"A": "a", "B": "b", "C": "c", "D": "d"},
            correct="A",
            category="T",
            time_limit_ms=10_000,
        ),
    ]


def test_duplicate_input_is_not_double_counted():
    mgr, writer = _make_manager()
    players = make_players(2)
    match = mgr.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=players,
        questions=_fixture(),
    )
    game = match.game

    # Puck 1 locks in answer A for round 1 with event_id "e1".
    ev = InputEvent(puck_index=1, tilt_x=0.0, tilt_y=30.0, button_tap=True)
    first = mgr.on_input(match.id, ev, event_id="e1")
    assert game.locked[1] is not None
    score_total_after_first = game.scores[1]

    # The firmware retries the SAME event_id (network hiccup). It must be
    # a no-op: no second lock, no second score event, no score change.
    second = mgr.on_input(match.id, ev, event_id="e1")
    assert second is first, "retry should replay the cached response object"

    mp1 = writer.match_pucks[(match.id, "uuid-1")]
    puck1_round_scores = [
        s
        for s in writer.scores
        if s["match_puck_id"] == mp1 and s["event_type"] == "round"
    ]
    assert len(puck1_round_scores) == 1, "duplicate input double-counted the score"
    assert game.scores[1] == score_total_after_first


def test_distinct_event_ids_both_apply():
    mgr, writer = _make_manager()
    players = make_players(2)
    match = mgr.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=players,
        questions=_fixture(),
    )
    game = match.game

    # Two different pucks, two different keys — both process. (Both
    # locking completes round 1, which resets `locked`, so assert on the
    # persisted round scores instead, one per puck.)
    mgr.on_input(
        match.id,
        InputEvent(puck_index=1, tilt_x=0.0, tilt_y=30.0, button_tap=True),
        event_id="p1-r1",
    )
    mgr.on_input(
        match.id,
        InputEvent(puck_index=2, tilt_x=0.0, tilt_y=30.0, button_tap=True),
        event_id="p2-r1",
    )
    mp1 = writer.match_pucks[(match.id, "uuid-1")]
    mp2 = writer.match_pucks[(match.id, "uuid-2")]
    assert any(s["match_puck_id"] == mp1 and s["event_type"] == "round" for s in writer.scores)
    assert any(s["match_puck_id"] == mp2 and s["event_type"] == "round" for s in writer.scores)
    assert game.round_index == 1, "both inputs applied -> round advanced"


def test_no_event_id_processes_every_time():
    """Legacy pucks that don't send a key get no dedupe — each call
    applies. (Two taps with no key in the same round: the second is
    ignored by the game's own already-locked guard, not by idempotency.)"""
    mgr, writer = _make_manager()
    players = make_players(1)
    match = mgr.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=players,
        questions=_fixture(),
    )
    # Without a key the cache is never consulted; on_input runs its full
    # body. The single puck locking in completes round 1 (which resets
    # `locked`), so assert the input was processed via the persisted
    # round score + the round advance.
    mgr.on_input(
        match.id,
        InputEvent(puck_index=1, tilt_x=0.0, tilt_y=30.0, button_tap=True),
    )
    mp1 = writer.match_pucks[(match.id, "uuid-1")]
    assert any(s["match_puck_id"] == mp1 and s["event_type"] == "round" for s in writer.scores)
    assert match.game.round_index == 1


def test_idempotency_cache_evicts_lru():
    cache = IdempotencyCache(maxsize=2)
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == 1  # touch a so b is now the LRU
    cache.put("c", 3)  # evicts b
    assert cache.get("b") is None
    assert cache.get("a") == 1
    assert cache.get("c") == 3
    assert len(cache) == 2
