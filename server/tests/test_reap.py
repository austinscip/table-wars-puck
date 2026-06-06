"""
Regression for audit 1.3/1.4: terminal matches (and their rate-limiter
buckets) must not leak — the reaper evicts them after a grace window.
"""

from __future__ import annotations

import time

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


def _finish(mgr, match):
    mgr.on_input(match.id, InputEvent(puck_index=1, tilt_x=0, tilt_y=30, button_tap=True))
    mgr.on_input(match.id, InputEvent(puck_index=2, tilt_x=0, tilt_y=30, button_tap=True))
    assert match.game.is_over()


def test_active_match_is_not_reaped():
    mgr = MatchManager(registry=registry, writer=FakeWriter(), reap_grace_s=0.0)
    match = _match(mgr)
    assert mgr.reap_terminal() == 0
    assert match.id in mgr.matches


def test_terminal_match_reaped_after_grace():
    reaped_ids = []
    mgr = MatchManager(
        registry=registry, writer=FakeWriter(),
        reap_grace_s=0.0,  # evict immediately once terminal
        on_match_reaped=reaped_ids.append,
    )
    match = _match(mgr)
    _finish(mgr, match)
    assert match.id in mgr.matches  # still resident right after finish
    n = mgr.reap_terminal()
    assert n == 1
    assert match.id not in mgr.matches  # evicted
    assert reaped_ids == [match.id]  # callback fired (drops rate buckets)


def test_terminal_match_kept_within_grace():
    mgr = MatchManager(registry=registry, writer=FakeWriter(), reap_grace_s=999.0)
    match = _match(mgr)
    _finish(mgr, match)
    assert mgr.reap_terminal() == 0  # within grace -> kept
    assert match.id in mgr.matches


def test_reap_drops_rate_limiter_buckets():
    from runtime import RateLimiter

    rl = RateLimiter()
    mgr = MatchManager(
        registry=registry, writer=FakeWriter(), reap_grace_s=0.0,
        on_match_reaped=lambda mid: rl.drop(f"{mid}:"),
    )
    match = _match(mgr)
    _finish(mgr, match)
    # Simulate input traffic having created buckets for this match.
    rl.allow(f"{match.id}:1")
    rl.allow(f"{match.id}:2")
    assert any(k.startswith(f"{match.id}:") for k in rl._buckets)
    mgr.reap_terminal()
    assert not any(k.startswith(f"{match.id}:") for k in rl._buckets)
