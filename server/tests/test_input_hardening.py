"""
Regression tests for input hardening + game-exception containment
(audit findings 0.2, 0.3). The input payload is attacker-controllable from
any LAN device, so event_from_dict must never yield non-finite/poison values
or raise, and a buggy game must never 500 the request or wedge the match.
"""

from __future__ import annotations

import math

import pytest

from runtime import InputEvent, MatchManager, registry
from runtime.inputs import event_from_dict

from conftest import FakeWriter, make_players
from games.speed_pyramid import Question


def test_rejects_nan_and_infinity():
    ev = event_from_dict(1, {"tilt_x": "inf", "tilt_y": "nan", "shake": float("inf")})
    assert math.isfinite(ev.tilt_x) and ev.tilt_x == 0.0
    assert math.isfinite(ev.tilt_y) and ev.tilt_y == 0.0
    assert math.isfinite(ev.shake) and ev.shake == 0.0


def test_rejects_non_numeric_strings_without_raising():
    ev = event_from_dict(1, {"tilt_x": "left", "shake": "hard", "gyro_z": None})
    assert ev.tilt_x == 0.0 and ev.shake == 0.0 and ev.gyro_z == 0.0


def test_clamps_out_of_range():
    ev = event_from_dict(1, {"tilt_x": 1e300, "tilt_y": -1e300, "shake": 99999})
    assert ev.tilt_x == 90.0 and ev.tilt_y == -90.0
    assert ev.shake == 100.0


def test_legacy_tilt_alias_still_works():
    ev = event_from_dict(1, {"tilt": 30.0})
    assert ev.tilt_x == 30.0
    # but a non-numeric legacy alias is coerced, not raised
    assert event_from_dict(1, {"tilt": "x"}).tilt_x == 0.0


def test_non_dict_payload_is_safe():
    ev = event_from_dict(1, None)  # type: ignore[arg-type]
    assert ev.puck_index == 1 and ev.tilt_x == 0.0


class _ExplodingGame:
    """A game whose on_input always raises — stands in for a real bug."""

    slug = "boom"
    min_players = 1
    max_players = 8
    serializable = False

    def __init__(self, players, **opts):
        self.players = players

    def on_input(self, event):
        raise RuntimeError("boom in on_input")

    def get_state(self):
        return {"ok": True}

    def tick(self, dt=0.1):
        from runtime import StateUpdate

        return StateUpdate(state=self.get_state())

    def is_over(self):
        return False

    def final_scores(self):
        return {}


def test_on_input_exception_is_contained(monkeypatch):
    # Register the exploding game, drive a real input, assert no exception
    # escapes and the match stays usable.
    registry.register(_ExplodingGame)
    try:
        mgr = MatchManager(registry=registry, writer=FakeWriter())
        # Build the match with the exploding game directly.
        from runtime.game import Player

        players = make_players(1)
        match = mgr.create(
            location_id="loc", game_slug="boom", table_number=1, players=players
        )
        # This would 500 before the fix; now it returns the last good state.
        update = mgr.on_input(
            match.id, InputEvent(puck_index=1, button_tap=True)
        )
        assert update.state == {"ok": True}
        # The match is NOT wedged — a second input also returns cleanly.
        update2 = mgr.on_input(
            match.id, InputEvent(puck_index=1, button_tap=True)
        )
        assert update2.state == {"ok": True}
    finally:
        registry._games.pop("boom", None)  # don't leak into other tests


def test_speed_pyramid_still_works_after_hardening():
    # Sanity: a real game with real input still plays.
    mgr = MatchManager(registry=registry, writer=FakeWriter())
    match = mgr.create(
        location_id="loc", game_slug="speed_pyramid", table_number=1,
        players=make_players(2),
        questions=[
            Question(id=1, setup="s", question="q",
                     answers={"A": "a", "B": "b", "C": "c", "D": "d"},
                     correct="A", category="T", time_limit_ms=10_000)
        ],
    )
    # north tilt = A, tap to lock
    upd = mgr.on_input(
        match.id, InputEvent(puck_index=1, tilt_x=0.0, tilt_y=30.0, button_tap=True)
    )
    assert isinstance(upd.state, dict)
