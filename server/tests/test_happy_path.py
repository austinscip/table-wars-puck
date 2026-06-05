"""
Happy-path regression tests — a normal match (no disconnect) still plays
through the MatchManager and finalises correctly for each game.

These guard the disconnect-handling refactor: the disconnect work touched
Speed Pyramid's on_input/tick round resolution and Puck Golf's turn
rotation, so these confirm ordinary play is unchanged.
"""

from __future__ import annotations

from runtime import InputEvent

from conftest import make_players

from games.speed_pyramid import Question
from games.puck_golf import Hole


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


def test_speed_pyramid_full_match_no_disconnect(manager, writer):
    players = make_players(2)
    questions = [
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
    match = manager.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=players,
        questions=questions,
    )
    game = match.game

    # Round 1: puck 1 correct (A), puck 2 wrong (C). Round advances only
    # once both have locked.
    _answer(manager, match.id, 1, "A")
    assert game.round_index == 0
    _answer(manager, match.id, 2, "C")
    assert game.round_index == 1

    # Round 2: puck 1 wrong (A), puck 2 correct (B). Match ends.
    _answer(manager, match.id, 1, "A")
    _answer(manager, match.id, 2, "B")
    assert game.is_over()

    finals = writer.final_scores(match.id)
    mp1 = writer.match_pucks[(match.id, "uuid-1")]
    mp2 = writer.match_pucks[(match.id, "uuid-2")]
    # Each scored exactly one correct answer, so both have a positive
    # total and a final score row.
    assert finals[mp1] > 0 and finals[mp2] > 0
    assert any(mid == match.id for mid, _ in writer.finished)


def test_puck_golf_turn_alternates(manager, writer):
    players = make_players(2)
    match = manager.create(
        location_id="loc",
        game_slug="puck_golf",
        table_number=1,
        players=players,
        course=[Hole(number=1, distance=200.0, par=4)],
    )
    game = match.game

    assert game.get_state()["current_turn_puck_index"] == 1
    # Puck 1 takes a weak shot (low power, won't hole out at 200 yds).
    manager.on_input(
        match.id,
        InputEvent(puck_index=1, tilt_x=0.0, tilt_y=30.0, shake=10.0, button_tap=True),
    )
    assert game.get_state()["current_turn_puck_index"] == 2, "turn did not pass"

    manager.on_input(
        match.id,
        InputEvent(puck_index=2, tilt_x=0.0, tilt_y=30.0, shake=10.0, button_tap=True),
    )
    assert game.get_state()["current_turn_puck_index"] == 1, "turn did not return"
    assert not game.is_over()
