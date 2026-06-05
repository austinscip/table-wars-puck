"""
Regression tests for the abandoned-match writer (Tier 1, item 4).

A match where every puck has gone silent AND no input has landed for the
abandon window is finalised as 'abandoned' rather than left 'active'
forever. The window must exceed the heartbeat stale threshold so a brief
blip never reaps a live table.

The abandon sweep is the backstop for a game that does NOT close itself
on disconnect (the per-game adapters close most matches as 'finished'
first); these tests drive that backstop directly.
"""

from __future__ import annotations

from runtime import (
    HeartbeatTracker,
    InputEvent,
    MatchManager,
    registry,
)

from conftest import FakeWriter, force_all_stale, make_players
from games.speed_pyramid import Question


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
        )
    ]


def _manager(abandon_after_s=0.0):
    writer = FakeWriter()
    mgr = MatchManager(
        registry=registry,
        writer=writer,
        heartbeat=HeartbeatTracker(),
        abandon_after_s=abandon_after_s,
    )
    return mgr, writer


def test_all_stale_match_is_abandoned():
    mgr, writer = _manager(abandon_after_s=0.0)
    players = make_players(2)
    match = mgr.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=players,
        questions=_fixture(),
    )
    # Neuter the game's own disconnect reaction so the abandon backstop is
    # what closes the match (otherwise SpeedPyramid would force-lock to a
    # 'finished' result first).
    match.game.on_puck_disconnected = lambda puck_index: None

    force_all_stale(mgr, match.id)
    mgr.tick(match.id)

    assert match.status == "abandoned"
    assert any(mid == match.id for mid, _ in writer.abandoned)
    # An abandoned match writes no final scores — there's no result.
    assert not any(s["event_type"] == "final" for s in writer.scores)
    # It is NOT also recorded as finished.
    assert not any(mid == match.id for mid, _ in writer.finished)


def test_recent_input_blocks_abandon():
    # Long window: even with every puck stale, a match that saw input
    # within the window is not abandoned.
    mgr, writer = _manager(abandon_after_s=120.0)
    players = make_players(2)
    match = mgr.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=players,
        questions=_fixture(),
    )
    match.game.on_puck_disconnected = lambda puck_index: None

    # Fresh input now keeps last_input_at recent.
    mgr.on_input(match.id, InputEvent(puck_index=1))
    force_all_stale(mgr, match.id)
    mgr.tick(match.id)

    assert match.status == "active"
    assert not writer.abandoned


def test_live_puck_blocks_abandon():
    # all_stale is False while at least one puck is fresh, so no abandon
    # even past the window.
    mgr, writer = _manager(abandon_after_s=0.0)
    players = make_players(2)
    match = mgr.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=players,
        questions=_fixture(),
    )
    match.game.on_puck_disconnected = lambda puck_index: None

    force_all_stale(mgr, match.id)
    # Puck 2 pings again — match is no longer all-stale.
    mgr.heartbeat.ping(match.id, 2)
    mgr.tick(match.id)

    assert match.status == "active"
    assert not writer.abandoned
