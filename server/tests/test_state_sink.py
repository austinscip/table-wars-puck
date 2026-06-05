"""
Regression tests for the local-first TV push seam (ADR 0004): the
MatchManager's `state_sink` and the per-match `snapshot_seq`.

Drives a REAL Speed Pyramid match through the MatchManager and asserts on
the genuine on_input/tick path — not a re-implementation. The three
load-bearing guarantees:

1. Every state-changing input/tick pushes exactly one frame to the local
   sink; quiet ticks and idempotent replays push nothing.
2. `snapshot_seq` is strictly increasing across the whole match, and the
   seq the LOCAL sink sees equals the seq written to the CLOUD snapshot for
   the same frame — so the TV's local-vs-cloud failover reconciliation can
   never render an older frame over a newer one.
3. The sink is invoked OUTSIDE the per-match lock (so a socket write never
   holds the game lock). Proven by a probe thread that must be able to
   acquire the match lock during the emit.
"""

from __future__ import annotations

import threading

from runtime import InputEvent, MatchManager, registry as game_registry

from conftest import FakeWriter, make_players

from games.speed_pyramid import Question


_LETTER_TILT = {
    "A": (0.0, 30.0),
    "B": (30.0, 0.0),
    "C": (0.0, -30.0),
    "D": (-30.0, 0.0),
}


def _answer(manager, match_id, puck_index, letter):
    tx, ty = _LETTER_TILT[letter]
    return manager.on_input(
        match_id,
        InputEvent(puck_index=puck_index, tilt_x=tx, tilt_y=ty, button_tap=True),
    )


def _questions():
    return [
        Question(
            id=1,
            setup="s1",
            question="q1",
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
            correct="B",
            category="T",
            time_limit_ms=10_000,
        ),
    ]


class RecordingSink:
    """Records every local-push envelope and, for each, whether the
    per-match lock was free (acquirable by another thread) at the moment of
    emit — the outside-the-lock proof."""

    def __init__(self, manager: MatchManager) -> None:
        self.manager = manager
        self.envelopes: list[dict] = []
        self.lock_free_during_emit: list[bool] = []

    def __call__(self, envelope: dict) -> None:
        self.envelopes.append(envelope)
        lock = self.manager._lock_for(envelope["match_id"])
        result: dict[str, bool] = {}

        def probe() -> None:
            got = lock.acquire(blocking=False)
            result["free"] = got
            if got:
                lock.release()

        t = threading.Thread(target=probe)
        t.start()
        t.join()
        self.lock_free_during_emit.append(result["free"])


def _manager_with_sink() -> tuple[MatchManager, FakeWriter, RecordingSink]:
    writer = FakeWriter()
    manager = MatchManager(registry=game_registry, writer=writer)
    sink = RecordingSink(manager)
    manager.state_sink = sink
    return manager, writer, sink


def test_every_input_pushes_one_frame_with_increasing_seq():
    manager, writer, sink = _manager_with_sink()
    match = manager.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=make_players(2),
        questions=_questions(),
    )

    # Four answers drive the match to completion (2 rounds × 2 pucks).
    _answer(manager, match.id, 1, "A")
    _answer(manager, match.id, 2, "C")
    _answer(manager, match.id, 1, "A")
    _answer(manager, match.id, 2, "B")
    assert match.game.is_over()

    # Every input is a state change → one emit each.
    assert len(sink.envelopes) == 4

    seqs = [e["snapshot"]["snapshot_seq"] for e in sink.envelopes]
    # Strictly increasing across the whole match.
    assert seqs == sorted(seqs)
    assert len(set(seqs)) == len(seqs)

    # Each emitted frame was persisted to the cloud with the SAME seq, so
    # local and cloud agree on ordering for failover reconciliation.
    cloud_seqs = {
        snap["snapshot_seq"]
        for _mid, snap in writer.snapshots
        if "snapshot_seq" in snap
    }
    assert set(seqs) == cloud_seqs


def test_envelope_shape_is_symmetrical_with_cloud():
    manager, _writer, sink = _manager_with_sink()
    match = manager.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=make_players(2),
        questions=_questions(),
    )
    _answer(manager, match.id, 1, "A")

    env = sink.envelopes[-1]
    # {status, snapshot} mirrors the cloud row (status column + snapshot
    # jsonb); the seq lives inside `snapshot` in both paths.
    assert env["match_id"] == match.id
    assert env["status"] == "active"
    assert "snapshot_seq" in env["snapshot"]
    assert isinstance(env["snapshot"], dict)


def test_emit_happens_outside_the_match_lock():
    manager, _writer, sink = _manager_with_sink()
    match = manager.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=make_players(2),
        questions=_questions(),
    )
    _answer(manager, match.id, 1, "A")
    _answer(manager, match.id, 2, "C")

    assert sink.lock_free_during_emit, "no frames emitted"
    # The lock must be free during EVERY emit — a regression that moves the
    # sink call back inside the locked section would hold the lock here.
    assert all(sink.lock_free_during_emit)


def test_idempotent_replay_pushes_no_frame():
    manager, _writer, sink = _manager_with_sink()
    # A manager with idempotency so a retried event_id replays.
    from runtime import IdempotencyCache

    manager.idempotency = IdempotencyCache()
    match = manager.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=make_players(2),
        questions=_questions(),
    )

    ev = InputEvent(puck_index=1, tilt_x=0.0, tilt_y=30.0, button_tap=True)
    manager.on_input(match.id, ev, event_id="evt-1")
    emitted_after_first = len(sink.envelopes)
    # Same logical event replays — no new side effects, no new frame.
    manager.on_input(match.id, ev, event_id="evt-1")
    assert len(sink.envelopes) == emitted_after_first


def test_no_sink_is_a_noop():
    # Default manager has no state_sink — gameplay still works, no crash.
    writer = FakeWriter()
    manager = MatchManager(registry=game_registry, writer=writer)
    match = manager.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=make_players(2),
        questions=_questions(),
    )
    _answer(manager, match.id, 1, "A")
    # snapshot_seq still advances on the match even with no sink.
    assert match.snapshot_seq >= 1
