"""
Game-state serialization round-trips (durable match state).

Each test drives a game partway, serializes it, round-trips through JSON
(proving it's persistable), deserializes into a fresh instance, and
asserts the gameplay state survived AND play continues correctly. This is
what lets an active match survive a server restart and is the foundation
for sharing match state across workers.
"""

from __future__ import annotations

import json

from runtime import InputEvent

from conftest import make_players

from games.speed_pyramid import SpeedPyramid, Question
from games.puck_golf import PuckGolf, Hole
from games.puck_racer import PuckRacer
from games.smash import Smash, ARENA_X


def _roundtrip(game):
    """serialize -> json -> deserialize into a fresh instance of the same
    class, with the same players."""
    data = game.serialize()
    data = json.loads(json.dumps(data))  # must be JSON-safe
    return type(game).deserialize(game.players, data)


# --- Speed Pyramid ---

def test_speed_pyramid_survives_serialization():
    qs = [
        Question(id=1, setup="s", question="q",
                 answers={"A": "a", "B": "b", "C": "c", "D": "d"},
                 correct="A", category="T", time_limit_ms=10_000),
        Question(id=2, setup="s2", question="q2",
                 answers={"A": "a", "B": "b", "C": "c", "D": "d"},
                 correct="B", category="T", time_limit_ms=10_000),
    ]
    game = SpeedPyramid(players=make_players(2), questions=qs)
    # Puck 1 answers Q1 correctly (tilt north = A, tap).
    game.on_input(InputEvent(puck_index=1, tilt_y=30.0, button_tap=True))
    assert game.scores[1] > 0
    assert game.round_index == 0

    restored = _roundtrip(game)
    # Gameplay state preserved.
    assert restored.scores == game.scores
    assert restored.round_index == game.round_index
    assert restored.locked[1] is not None and restored.locked.get(2) is None
    assert len(restored.questions) == 2

    # Play continues on the restored game: puck 2 answers Q1 -> round
    # advances, then both answer Q2 -> match finishes.
    restored.on_input(InputEvent(puck_index=2, tilt_y=30.0, button_tap=True))
    assert restored.round_index == 1
    restored.on_input(InputEvent(puck_index=1, tilt_x=30.0, button_tap=True))
    restored.on_input(InputEvent(puck_index=2, tilt_x=30.0, button_tap=True))
    assert restored.is_over()


# --- Puck Racer ---

def test_puck_racer_survives_serialization():
    game = PuckRacer(players=make_players(2))
    game.on_input(InputEvent(puck_index=1, button_hold=True))
    for _ in range(20):
        game.tick()
    pos_before = {i: r.position for i, r in game.racers.items()}

    restored = _roundtrip(game)
    assert restored.tick_count == game.tick_count
    assert {i: r.position for i, r in restored.racers.items()} == pos_before
    assert restored.racers[1].throttle_held is True

    # Continues advancing from where it left off.
    p1 = restored.racers[1].position
    restored.tick()
    assert restored.racers[1].position > p1


# --- Smash ---

def test_smash_survives_serialization():
    game = Smash(players=make_players(3))
    game.fighters[1].kos_landed = 2
    game.fighters[2].stocks = 1
    for _ in range(15):
        game.tick()

    restored = _roundtrip(game)
    assert restored.tick_count == game.tick_count
    assert restored.fighters[1].kos_landed == 2
    assert restored.fighters[2].stocks == 1
    # Win condition still reachable: eliminate everyone but one.
    restored.fighters[2].x = ARENA_X[0] - 100  # ring out p2 repeatedly...
    # Force p2 + p3 out so only p1 remains.
    restored.fighters[2].stocks = 1
    restored.fighters[3].stocks = 1
    restored.fighters[2].x = ARENA_X[1] + 100
    restored.fighters[3].x = ARENA_X[1] + 100
    restored.tick()
    assert restored.is_over()


# --- Puck Golf ---

def test_puck_golf_survives_serialization():
    game = PuckGolf(players=make_players(2), course=[Hole(number=1, distance=200.0, par=4)])
    # Puck 1 takes a weak shot (won't hole out), turn passes to 2.
    game.on_input(InputEvent(puck_index=1, tilt_y=30.0, shake=10.0, button_tap=True))
    assert game.get_state()["current_turn_puck_index"] == 2
    strokes_before = list(game.player_state[1].holes_strokes)

    restored = _roundtrip(game)
    assert restored.hole_index == game.hole_index
    assert restored.turn_index == game.turn_index
    assert restored.player_state[1].holes_strokes == strokes_before
    assert restored.get_state()["current_turn_puck_index"] == 2

    # Puck 2 plays on the restored game.
    restored.on_input(InputEvent(puck_index=2, tilt_y=30.0, shake=10.0, button_tap=True))
    assert restored.get_state()["current_turn_puck_index"] == 1


def test_non_serializable_game_raises_by_default():
    # The base contract: a game that doesn't opt in raises clearly.
    import pytest
    from runtime.game import Game

    class Dummy(Game):
        slug = "dummy"
        def __init__(self, players, **o): self.players = players
        def on_input(self, e): ...
        def get_state(self): return {}
        def is_over(self): return False
        def final_scores(self): return {}

    d = Dummy(players=make_players(1))
    assert d.serializable is False
    with pytest.raises(NotImplementedError):
        d.serialize()
