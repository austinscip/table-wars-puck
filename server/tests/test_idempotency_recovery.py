"""Idempotency-across-restart regression (audit runtime F6).

The in-process IdempotencyCache is wiped by a restart, so a retried input
(same event_id) that was already applied pre-crash would be RE-applied after
recovery — double score / double lock-in. The recent idempotency keys are now
persisted with the match snapshot and re-seeded on recover, so the retry is
deduped. This drives the real persist/recover path, not a re-implementation.
"""
from __future__ import annotations

from runtime import (
    HeartbeatTracker,
    IdempotencyCache,
    InputEvent,
    MatchManager,
    registry,
)
from runtime.match_store import InMemoryMatchStore

from conftest import FakeWriter, make_players
from games.speed_pyramid import Question


_ANSWER_A = dict(tilt_x=0.0, tilt_y=30.0, button_tap=True)  # selects "A"


def _questions():
    return [
        Question(id=1, setup="s", question="q",
                 answers={"A": "a", "B": "b", "C": "c", "D": "d"},
                 correct="A", category="T", time_limit_ms=10_000),
        Question(id=2, setup="s2", question="q2",
                 answers={"A": "a", "B": "b", "C": "c", "D": "d"},
                 correct="B", category="T", time_limit_ms=10_000),
    ]


def _manager(store, idem, writer):
    return MatchManager(
        registry=registry, writer=writer, store=store,
        idempotency=idem, heartbeat=HeartbeatTracker(),
    )


def test_retry_after_restart_is_deduped(monkeypatch):
    store = InMemoryMatchStore()
    m1 = _manager(store, IdempotencyCache(), FakeWriter())
    match = m1.create(
        location_id="loc", game_slug="speed_pyramid", table_number=1,
        players=make_players(2), questions=_questions(),
    )
    # Puck 1 answers round 1 correctly under event_id "e1" — scores + persists.
    m1.on_input(match.id, InputEvent(puck_index=1, **_ANSWER_A), event_id="e1")
    assert m1.matches[match.id].game.scores[1] > 0
    # The snapshot the store holds carries the idempotency key.
    saved = store.load(match.id)
    assert any(k.endswith(":e1") for k in saved.get("idempotency_keys", []))

    # Simulate a restart: brand-new manager + EMPTY idempotency cache, same store.
    m2 = _manager(store, IdempotencyCache(), FakeWriter())
    assert match.id in m2.recover()
    game2 = m2.matches[match.id].game
    score_after_recovery = game2.scores[1]
    assert score_after_recovery > 0  # the original answer survived

    # The puck retries the SAME logical event after the restart. It must be
    # deduped — NOT re-applied as a second answer.
    m2.on_input(match.id, InputEvent(puck_index=1, **_ANSWER_A), event_id="e1")
    assert game2.scores[1] == score_after_recovery, "retry was re-applied after restart"
    # And puck 1 is still only locked once for the round (no double lock-in).
    assert game2.round_index == 0  # round didn't advance off a phantom re-answer


def test_new_event_after_restart_still_applies(monkeypatch):
    """Sanity: recovery must not over-dedupe — a genuinely new event_id still
    applies after a restart."""
    store = InMemoryMatchStore()
    m1 = _manager(store, IdempotencyCache(), FakeWriter())
    match = m1.create(
        location_id="loc", game_slug="speed_pyramid", table_number=1,
        players=make_players(2), questions=_questions(),
    )
    m1.on_input(match.id, InputEvent(puck_index=1, **_ANSWER_A), event_id="e1")

    m2 = _manager(store, IdempotencyCache(), FakeWriter())
    m2.recover()
    game2 = m2.matches[match.id].game
    # Puck 2 answers (new event) -> round resolves and advances.
    m2.on_input(match.id, InputEvent(puck_index=2, **_ANSWER_A), event_id="e2")
    assert game2.round_index == 1, "a new post-restart event must still apply"
