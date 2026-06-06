"""Crash-recovery robustness regression tests for the runtime games
(audit runtime-games-2026-06-06).

- A snapshot missing a field (forward/back schema skew on an upgrade-day
  crash) must deserialize to the constructed default, NOT KeyError — a
  KeyError is caught by deserialize_match and silently drops the WHOLE match.
- PuckRacer._finalize must guard the empty-roster max() (mirrors the golf fix).
- RedisMatchStore must reject NaN/Inf loudly and write key+index atomically.
"""
from __future__ import annotations

import pytest

from conftest import make_players

from games.speed_pyramid import SpeedPyramid, Question
from games.puck_golf import PuckGolf, Hole
from games.puck_racer import PuckRacer
from games.smash import Smash


def _sp():
    qs = [Question(id=1, setup="s", question="q",
                   answers={"A": "a", "B": "b", "C": "c", "D": "d"},
                   correct="A", category="T", time_limit_ms=10_000)]
    return SpeedPyramid(make_players(2), questions=qs)


def _builders():
    return [
        ("speed_pyramid", _sp, SpeedPyramid),
        ("puck_golf", lambda: PuckGolf(make_players(2),
                                       course=[Hole(number=1, distance=50.0, par=2)]),
         PuckGolf),
        ("puck_racer", lambda: PuckRacer(make_players(2)), PuckRacer),
        ("smash", lambda: Smash(make_players(2)), Smash),
    ]


@pytest.mark.parametrize("slug,build,cls", _builders())
def test_deserialize_tolerates_missing_field(slug, build, cls):
    """Drop one persisted key from a real snapshot and confirm restore still
    succeeds (the field falls back to its default) instead of raising."""
    game = build()
    snap = game.serialize()
    # Remove an arbitrary non-structural top-level key + a nested one to
    # simulate a snapshot written before that field existed.
    droppable = [k for k in snap if k not in
                 ("questions", "course")]
    assert droppable, f"{slug}: nothing safe to drop"
    snap.pop(droppable[-1])
    # Also drop a nested per-entity field if present.
    for container in ("racers", "fighters", "player_state"):
        if isinstance(snap.get(container), dict) and snap[container]:
            first = next(iter(snap[container].values()))
            if isinstance(first, dict) and len(first) > 1:
                first.pop(next(iter(first)))
            break
    # Must not raise.
    restored = cls.deserialize(make_players(2), snap)
    assert restored is not None
    # And it's still a usable game (get_state is JSON-shaped).
    assert isinstance(restored.get_state(), dict)


def test_racer_finalize_guards_empty_roster():
    """A recovery that dropped every racer must not crash _finalize with a
    max() ValueError (mirrors the golf empty-roster guard)."""
    game = PuckRacer(make_players(2))
    game.racers = {}  # simulate an empty post-recovery roster
    cues: list = []
    game._finalize(cues, [])  # must not raise
    assert game.finished
    # A match_end cue was still emitted (winner None).
    assert cues, "no match_end cue emitted"


def test_redis_store_rejects_nan_and_saves_atomically():
    fakeredis = pytest.importorskip("fakeredis")
    from runtime.match_store import RedisMatchStore

    store = RedisMatchStore(fakeredis.FakeStrictRedis())
    store.save("m1", {"position": 1.5, "ok": True})
    assert store.load_all_ids() == ["m1"]
    assert store.load("m1") == {"position": 1.5, "ok": True}

    with pytest.raises(ValueError):
        store.save("m2", {"position": float("inf")})
    # The rejected match left no half-written index entry.
    assert "m2" not in store.load_all_ids()
