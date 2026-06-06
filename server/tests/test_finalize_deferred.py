"""
Regression for audit 1.5: the synchronous final-score + lifecycle writes must
NOT run under the per-match lock. _finalize/_abandon now do only the in-memory
transition and RETURN the durable writes for the caller to run outside the
lock.
"""

from __future__ import annotations

from runtime import InputEvent, MatchManager, registry

from conftest import FakeWriter, make_players
from games.speed_pyramid import Question


def _match(mgr):
    return mgr.create(
        location_id="loc", game_slug="speed_pyramid", table_number=1,
        players=make_players(2),
        questions=[
            Question(id=1, setup="s", question="q",
                     answers={"A": "a", "B": "b", "C": "c", "D": "d"},
                     correct="A", category="T", time_limit_ms=10_000)
        ],
    )


def test_finalize_defers_writes_instead_of_writing_inline():
    writer = FakeWriter()
    mgr = MatchManager(registry=registry, writer=writer)
    match = _match(mgr)

    deferred = mgr._finalize(match)
    # In-memory transition happened...
    assert match.status == "finished"
    assert match.terminal_at is not None
    # ...but the durable writes did NOT run yet (they're returned, not called
    # under the lock).
    assert writer.finished == []
    assert writer.final_scores(match.id) == {}
    assert len(deferred) >= 1  # finals + the finished write

    # Running the deferred batch (what the public method does outside the
    # lock) performs the writes.
    for w in deferred:
        w()
    assert any(mid == match.id for mid, _ in writer.finished)


def test_abandon_defers_writes():
    writer = FakeWriter()
    mgr = MatchManager(registry=registry, writer=writer)
    match = _match(mgr)
    deferred = mgr._abandon(match)
    assert match.status == "abandoned"
    assert writer.abandoned == []  # not written inline
    for w in deferred:
        w()
    assert any(mid == match.id for mid, _ in writer.abandoned)


def test_end_to_end_finals_still_land_via_public_path():
    # The public on_input path runs the deferred writes after the lock, so a
    # full match still persists finals (end-to-end guarantee preserved).
    writer = FakeWriter()
    mgr = MatchManager(registry=registry, writer=writer)
    match = _match(mgr)
    # One round, both pucks lock in -> match ends.
    mgr.on_input(match.id, InputEvent(puck_index=1, tilt_x=0, tilt_y=30, button_tap=True))
    mgr.on_input(match.id, InputEvent(puck_index=2, tilt_x=0, tilt_y=30, button_tap=True))
    assert match.game.is_over()
    assert any(mid == match.id for mid, _ in writer.finished)
    assert len(writer.final_scores(match.id)) == 2
