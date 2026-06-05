"""
Regression tests for tick fidelity (gap #5b): timed games must advance by
REAL elapsed seconds (the dt the scheduler measures), not by a fixed
per-tick constant — otherwise a box that can't hold 10 Hz runs Racer/Smash
in slow motion. The scheduler clamps dt so a long stall can't teleport
physics.
"""

from __future__ import annotations

import pytest

from runtime import InputEvent, MatchManager, TickScheduler, registry

from conftest import FakeWriter, make_players

from games.smash import MAX_MATCH_SECONDS


def _manager():
    return MatchManager(registry=registry, writer=FakeWriter())


def test_racer_elapsed_tracks_real_dt_not_tick_count():
    mgr = _manager()
    match = mgr.create(
        location_id="loc", game_slug="puck_racer", table_number=1,
        players=make_players(2),
    )
    g = match.game
    mgr.tick(match.id, dt=0.1)
    mgr.tick(match.id, dt=0.3)
    # Two ticks, but 0.4s of real time — NOT 0.2s (2 * nominal). This is the
    # whole fix: a slow tick advances the race by its real duration.
    assert g.elapsed_s == pytest.approx(0.4)
    assert g.tick_count == 2  # frame counter still counts frames


def test_racer_distance_advances_by_real_time():
    # Anti-slow-motion: under the old tick_count model one tick always moved
    # a fixed amount regardless of real time. Now a longer real tick covers
    # more ground — so a lagging box doesn't run the race in slow motion.
    def run(dt):
        mgr = _manager()
        m = mgr.create(location_id="loc", game_slug="puck_racer",
                       table_number=1, players=make_players(2))
        mgr.on_input(m.id, InputEvent(puck_index=1, button_hold=True))
        mgr.tick(m.id, dt=dt)
        return m.game.racers[1].position

    assert run(0.3) > run(0.1) > 0.0


def test_smash_ends_on_wallclock_timeout():
    mgr = _manager()
    match = mgr.create(
        location_id="loc", game_slug="smash", table_number=1,
        players=make_players(2),
    )
    # A single tick whose real dt exceeds the match cap ends the brawl by
    # match-time — no need for 1800 ticks. (The scheduler would clamp such a
    # dt; here we assert the game honours wall-clock time itself.)
    mgr.tick(match.id, dt=MAX_MATCH_SECONDS + 1.0)
    assert match.game.finished


def test_racer_serialization_roundtrips_elapsed():
    from games.puck_racer import PuckRacer

    mgr = _manager()
    match = mgr.create(
        location_id="loc", game_slug="puck_racer", table_number=1,
        players=make_players(2),
    )
    mgr.tick(match.id, dt=0.37)
    data = match.game.serialize()
    restored = PuckRacer.deserialize(make_players(2), data)
    assert restored.elapsed_s == pytest.approx(0.37)


def test_scheduler_clamps_dt():
    clamp = TickScheduler._clamp_dt
    assert clamp(0.1) == pytest.approx(0.1)         # normal
    assert clamp(0.12) == pytest.approx(0.12)       # mild jitter passes through
    assert clamp(5.0) == TickScheduler.MAX_TICK_DT  # long stall capped
    assert clamp(-1.0) == 0.0                        # clock blip floored
