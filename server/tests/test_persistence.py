"""
Regression tests for the PersistenceQueue (ADR 0004) — the decoupling that
keeps cloud I/O off the 10 Hz tick's critical path.

The guarantees under test:

- Snapshots are asynchronous AND coalesced (latest-wins per match): the
  underlying writer sees nothing until a drain, then sees exactly one
  snapshot per match — the newest. This is what removes the
  cloud-write-under-lock from the tick path.
- Round scores are asynchronous best-effort FIFO (analytics only).
- Finals, lifecycle (finished/abandoned), and create are SYNCHRONOUS — the
  underlying writer has them before the call returns — with bounded retry
  so a transient blip doesn't lose a final score.
- Driven through a REAL match: the manager's input/tick path completes with
  the queue in place; finals land synchronously, snapshots coalesce.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest

from runtime import (
    InputEvent,
    MatchManager,
    PersistenceQueue,
    registry as game_registry,
)

from conftest import FakeWriter, make_players

from games.speed_pyramid import Question


def _snap(seq: int) -> dict:
    return {"snapshot_seq": seq, "state": {"v": seq}}


# ---------------------------------------------------------------------------
# Snapshot lane — async + coalesced
# ---------------------------------------------------------------------------


def test_snapshots_are_async_and_coalesced():
    fake = FakeWriter()
    q = PersistenceQueue(fake)  # not started — drain manually for determinism

    q.update_match_snapshot("m1", _snap(0))
    q.update_match_snapshot("m1", _snap(1))
    q.update_match_snapshot("m1", _snap(2))
    # Nothing reached the cloud yet — the calls only enqueued.
    assert fake.snapshots == []

    q.flush()
    # Exactly one write for m1, and it's the LATEST (coalesced).
    assert len(fake.snapshots) == 1
    mid, snap = fake.snapshots[0]
    assert mid == "m1"
    assert snap["snapshot_seq"] == 2


class _FlakySnapshotWriter(FakeWriter):
    def __init__(self):
        super().__init__()
        self.fail_next = False

    def update_match_snapshot(self, match_id, snapshot):
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("cloud down")
        super().update_match_snapshot(match_id, snapshot)


def test_failed_snapshot_requeues_cues():
    # Audit 2.9: a transient snapshot-write failure must not lose cues — they
    # are re-queued and delivered on the next drain.
    fake = _FlakySnapshotWriter()
    q = PersistenceQueue(fake)
    q.update_match_snapshot(
        "m1", {"snapshot_seq": 0, "cues": [{"cue": "correct", "seq": 0}]}
    )
    fake.fail_next = True
    q.flush()  # write fails -> cues re-queued, nothing landed
    assert fake.snapshots == []
    q.flush()  # retry succeeds
    assert fake.snapshots
    _mid, snap = fake.snapshots[-1]
    assert [c["cue"] for c in snap["cues"]] == ["correct"]  # cue survived


def test_coalescing_accumulates_cues_so_none_are_lost():
    fake = FakeWriter()
    q = PersistenceQueue(fake)
    # Two frames coalesce into one slot; their cues must both survive.
    q.update_match_snapshot(
        "m1", {"snapshot_seq": 0, "cues": [{"cue": "correct", "seq": 0}]}
    )
    q.update_match_snapshot(
        "m1", {"snapshot_seq": 1, "cues": [{"cue": "round_start", "seq": 1}]}
    )
    q.flush()
    assert len(fake.snapshots) == 1
    _mid, snap = fake.snapshots[0]
    # Latest state seq wins...
    assert snap["snapshot_seq"] == 1
    # ...but BOTH cues are present (accumulated, in order).
    assert [c["cue"] for c in snap["cues"]] == ["correct", "round_start"]


def test_snapshots_coalesce_per_match_not_across():
    fake = FakeWriter()
    q = PersistenceQueue(fake)
    q.update_match_snapshot("m1", _snap(5))
    q.update_match_snapshot("m2", _snap(9))
    q.flush()
    written = {mid: snap["snapshot_seq"] for mid, snap in fake.snapshots}
    assert written == {"m1": 5, "m2": 9}


# ---------------------------------------------------------------------------
# Round-score lane — async best-effort FIFO
# ---------------------------------------------------------------------------


def test_round_scores_are_async_fifo():
    fake = FakeWriter()
    q = PersistenceQueue(fake)
    q.insert_score("m1", "mp1", 1, 10, 10, "round")
    q.insert_score("m1", "mp1", 2, 20, 30, "round")
    assert fake.scores == []  # async — nothing yet
    q.flush()
    totals = [s["score_total"] for s in fake.scores]
    assert totals == [10, 30]  # FIFO order preserved


def test_round_backlog_is_bounded():
    fake = FakeWriter()
    q = PersistenceQueue(fake)
    q.MAX_ROUND_BACKLOG = 3  # instance override for the test
    for i in range(5):
        q.insert_score("m1", "mp1", i, 1, i, "round")
    # Oldest two dropped under back-pressure; newest three retained.
    assert q.dropped_round_scores == 2
    q.flush()
    kept = [s["score_total"] for s in fake.scores]
    assert kept == [2, 3, 4]


# ---------------------------------------------------------------------------
# Truth lane — synchronous
# ---------------------------------------------------------------------------


def test_finals_and_lifecycle_are_synchronous():
    fake = FakeWriter()
    q = PersistenceQueue(fake)  # not started — proves no drain needed

    q.insert_score("m1", "mp1", 0, 0, 999, "final")
    # Synchronous: present immediately, before any flush.
    assert any(s["event_type"] == "final" for s in fake.scores)

    now = datetime.now(timezone.utc)
    q.update_match_finished("m1", now)
    assert fake.finished == [("m1", now)]

    q.update_match_abandoned("m2", now)
    assert fake.abandoned == [("m2", now)]


def test_create_match_is_synchronous_passthrough():
    fake = FakeWriter()
    q = PersistenceQueue(fake)
    match_id, mp_ids = q.create_match(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        pucks=[("uuid-1", "host", "P1")],
        snapshot={"seed": True},
    )
    assert match_id and len(mp_ids) == 1
    assert fake.matches[0]["location_id"] == "loc"


class _FlakyWriter(FakeWriter):
    """Fails the first `fail_times` final-score writes, then succeeds."""

    def __init__(self, fail_times: int) -> None:
        super().__init__()
        self._fail_times = fail_times
        self.final_attempts = 0

    def insert_score(self, *args, **kwargs) -> None:
        if kwargs.get("event_type") == "final":
            self.final_attempts += 1
            if self.final_attempts <= self._fail_times:
                raise RuntimeError("transient cloud blip")
        super().insert_score(*args, **kwargs)


def test_final_write_retries_then_succeeds():
    fake = _FlakyWriter(fail_times=2)
    q = PersistenceQueue(fake)
    q.SYNC_RETRY_BASE_S = 0.001  # keep the test fast
    q.insert_score("m1", "mp1", 0, 0, 500, "final")
    # Retried past the two failures; the score landed.
    assert fake.final_attempts == 3
    assert any(s["score_total"] == 500 for s in fake.scores)


class _UniqueViolationWriter(FakeWriter):
    """Raises a Postgres unique-violation (SQLSTATE 23505) on a final insert,
    like a retried final after an ambiguous commit."""

    def insert_score(self, *args, **kwargs):
        if kwargs.get("event_type") == "final":
            exc = RuntimeError("duplicate key value violates unique constraint")
            exc.sqlstate = "23505"  # type: ignore[attr-defined]
            raise exc
        super().insert_score(*args, **kwargs)


def test_final_unique_violation_is_idempotent_success():
    # A duplicate final must be treated as already-landed, NOT retried/raised
    # (audit 1.2) — so total_matches can't inflate on replay.
    fake = _UniqueViolationWriter()
    q = PersistenceQueue(fake)
    q.SYNC_RETRY_BASE_S = 0.001
    # Does not raise; returns as success.
    q.insert_score("m1", "mp1", 0, 0, 500, "final")


def test_final_write_raises_after_exhausting_retries():
    fake = _FlakyWriter(fail_times=99)
    q = PersistenceQueue(fake)
    q.SYNC_RETRY_BASE_S = 0.001
    with pytest.raises(RuntimeError):
        q.insert_score("m1", "mp1", 0, 0, 500, "final")
    assert fake.final_attempts == q.SYNC_RETRIES


# ---------------------------------------------------------------------------
# Background drain thread
# ---------------------------------------------------------------------------


def test_background_thread_drains_without_manual_flush():
    fake = FakeWriter()
    q = PersistenceQueue(fake, drain_interval_s=0.02)
    q.start()
    try:
        q.update_match_snapshot("m1", _snap(7))
        # Poll for the background drain rather than sleeping a fixed time.
        deadline = time.monotonic() + 2.0
        while not fake.snapshots and time.monotonic() < deadline:
            time.sleep(0.01)
        assert fake.snapshots, "background thread did not drain the snapshot"
        assert fake.snapshots[-1][1]["snapshot_seq"] == 7
    finally:
        q.stop()


def test_stop_flushes_pending_work():
    fake = FakeWriter()
    q = PersistenceQueue(fake, drain_interval_s=10.0)  # won't auto-drain
    q.start()
    q.update_match_snapshot("m1", _snap(3))
    q.stop()  # drain=True by default
    assert fake.snapshots and fake.snapshots[-1][1]["snapshot_seq"] == 3


# ---------------------------------------------------------------------------
# Real match through the manager with the queue in place
# ---------------------------------------------------------------------------


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


_LETTER_TILT = {"A": (0.0, 30.0), "B": (30.0, 0.0), "C": (0.0, -30.0)}


def test_real_match_through_persistence_queue():
    fake = FakeWriter()
    q = PersistenceQueue(fake)
    manager = MatchManager(registry=game_registry, writer=q)

    match = manager.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=make_players(2),
        questions=_questions(),
    )
    # create_match is synchronous — the seed row is already in the cloud.
    assert fake.matches and fake.matches[0]["game_slug"] == "speed_pyramid"

    for puck, letter in [(1, "A"), (2, "C"), (1, "A"), (2, "B")]:
        tx, ty = _LETTER_TILT[letter]
        manager.on_input(
            match.id,
            InputEvent(puck_index=puck, tilt_x=tx, tilt_y=ty, button_tap=True),
        )
    assert match.game.is_over()

    # Finals landed synchronously (no flush needed) — leaderboard truth is
    # never stuck in the async queue.
    finals = fake.final_scores(match.id)
    assert len(finals) == 2 and all(v >= 0 for v in finals.values())
    assert any(mid == match.id for mid, _ in fake.finished)

    # Snapshots were async — drain and confirm the latest landed.
    q.flush()
    seqs = [
        snap["snapshot_seq"]
        for mid, snap in fake.snapshots
        if mid == match.id and "snapshot_seq" in snap
    ]
    assert seqs, "no snapshot persisted for the match"
