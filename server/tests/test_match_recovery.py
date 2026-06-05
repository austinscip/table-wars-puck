"""
Restart-recovery / durable match state.

Manager A creates a match against a store and drives it partway. A FRESH
Manager B (simulating a restart / a different worker) recovers from the
same store and continues the match correctly. Run against both the
in-memory store and a Redis-backed store (fakeredis), proving the state
truly survives the process boundary as JSON.
"""

from __future__ import annotations

import pytest

from runtime import (
    InMemoryMatchStore,
    InputEvent,
    MatchManager,
    RedisMatchStore,
    registry,
)

from conftest import FakeWriter, make_players
from games.speed_pyramid import Question


def _fixture():
    return [
        Question(id=1, setup="s", question="q",
                 answers={"A": "a", "B": "b", "C": "c", "D": "d"},
                 correct="A", category="T", time_limit_ms=10_000),
        Question(id=2, setup="s2", question="q2",
                 answers={"A": "a", "B": "b", "C": "c", "D": "d"},
                 correct="B", category="T", time_limit_ms=10_000),
    ]


def _stores():
    stores = [("memory", InMemoryMatchStore())]
    fakeredis = pytest.importorskip("fakeredis")
    stores.append(("redis", RedisMatchStore(fakeredis.FakeStrictRedis())))
    return stores


@pytest.mark.parametrize("label,store", _stores())
def test_match_recovers_and_continues(label, store):
    # --- Manager A: create + play one round ---
    mgrA = MatchManager(registry=registry, writer=FakeWriter(), store=store)
    match = mgrA.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=make_players(2),
        questions=_fixture(),
    )
    mid = match.id
    mgrA.on_input(mid, InputEvent(puck_index=1, tilt_y=30.0, button_tap=True))
    score_after_q1 = match.game.scores[1]
    assert score_after_q1 > 0

    # --- Manager B: a fresh process recovers from the same store ---
    writerB = FakeWriter()
    mgrB = MatchManager(registry=registry, writer=writerB, store=store)
    assert mgrB.matches == {}
    recovered = mgrB.recover()
    assert mid in recovered

    rmatch = mgrB.matches[mid]
    # Gameplay state carried across the boundary.
    assert rmatch.game.scores[1] == score_after_q1
    assert rmatch.game.round_index == 0
    assert rmatch.match_puck_ids == match.match_puck_ids
    assert rmatch.location_id == "loc"

    # B drives the match to completion.
    mgrB.on_input(mid, InputEvent(puck_index=2, tilt_y=30.0, button_tap=True))
    assert rmatch.game.round_index == 1
    mgrB.on_input(mid, InputEvent(puck_index=1, tilt_x=30.0, button_tap=True))
    mgrB.on_input(mid, InputEvent(puck_index=2, tilt_x=30.0, button_tap=True))
    assert rmatch.game.is_over()

    # Finished match is dropped from the store (not recovered again).
    mgrC = MatchManager(registry=registry, writer=FakeWriter(), store=store)
    assert mgrC.recover() == []


@pytest.mark.parametrize("label,store", _stores())
def test_finished_match_not_recovered(label, store):
    mgr = MatchManager(registry=registry, writer=FakeWriter(), store=store)
    match = mgr.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=make_players(1),
        questions=[Question(id=1, setup="s", question="q",
                            answers={"A": "a", "B": "b", "C": "c", "D": "d"},
                            correct="A", category="T", time_limit_ms=10_000)],
    )
    # Single question -> finishes on the first answer.
    mgr.on_input(match.id, InputEvent(puck_index=1, tilt_y=30.0, button_tap=True))
    assert match.game.is_over()
    # The store no longer holds it.
    fresh = MatchManager(registry=registry, writer=FakeWriter(), store=store)
    assert fresh.recover() == []
