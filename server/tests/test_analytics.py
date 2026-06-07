"""Tests for the PostHog product-analytics plumbing (master-plan step 63).

The guarantees the runtime relies on: it's a safe no-op when unconfigured (no
key / no SDK), it never raises into gameplay, and when configured it forwards
non-PII match-lifecycle events. Mirrors test_logging's Sentry posture.
"""
from __future__ import annotations

from runtime import analytics
from runtime import InputEvent, MatchManager, registry
from runtime.analytics import capture, init_analytics, reset_for_test

from conftest import FakeWriter, make_players
from games.speed_pyramid import Question


def test_init_noops_without_key(monkeypatch):
    reset_for_test()
    monkeypatch.delenv("POSTHOG_API_KEY", raising=False)
    assert init_analytics() is False


def test_capture_is_safe_noop_when_off(monkeypatch):
    reset_for_test()
    monkeypatch.delenv("POSTHOG_API_KEY", raising=False)
    init_analytics()
    # Must not raise even though analytics is off.
    capture("loc", "match_created", {"game_slug": "speed_pyramid"})


def test_capture_forwards_to_client_when_configured(monkeypatch):
    """With a fake PostHog client installed, capture forwards non-PII props."""
    reset_for_test()
    sent: list = []

    class _FakeClient:
        def capture(self, distinct_id, event, properties):
            sent.append((distinct_id, event, properties))

    monkeypatch.setattr(analytics, "_CLIENT", _FakeClient())
    capture("venue-1", "match_finished", {"game_slug": "puck_golf", "player_count": 2})
    assert sent == [("venue-1", "match_finished",
                     {"game_slug": "puck_golf", "player_count": 2})]


def test_match_lifecycle_emits_events(monkeypatch):
    """A real match through the MatchManager fires match_created + match_finished
    with only non-PII properties (game/table/count/duration — no puck content)."""
    reset_for_test()
    events: list = []

    class _FakeClient:
        def capture(self, distinct_id, event, properties):
            events.append((event, properties))

    monkeypatch.setattr(analytics, "_CLIENT", _FakeClient())

    writer = FakeWriter()
    mgr = MatchManager(registry=registry, writer=writer)
    qs = [
        Question(id=1, setup="s", question="q",
                 answers={"A": "a", "B": "b", "C": "c", "D": "d"},
                 correct="A", category="T", time_limit_ms=10_000),
    ]
    match = mgr.create(location_id="venue-1", game_slug="speed_pyramid",
                       table_number=3, players=make_players(2), questions=qs)
    # Drive the single round to completion (both answer -> match finishes).
    tx, ty = (0.0, 30.0)  # 'A'
    mgr.on_input(match.id, InputEvent(puck_index=1, tilt_x=tx, tilt_y=ty, button_tap=True))
    mgr.on_input(match.id, InputEvent(puck_index=2, tilt_x=tx, tilt_y=ty, button_tap=True))
    assert match.game.is_over()

    names = [e for e, _ in events]
    assert "match_created" in names
    assert "match_finished" in names
    created_props = dict(events)[("match_created")] if False else \
        next(p for e, p in events if e == "match_created")
    assert created_props["game_slug"] == "speed_pyramid"
    assert created_props["table_number"] == 3
    assert created_props["player_count"] == 2
    # No PII / content keys leaked into the analytics props.
    for _e, props in events:
        keys = set(props)
        assert not (keys & {"name", "answer", "phone", "token", "puck_uuid"})
