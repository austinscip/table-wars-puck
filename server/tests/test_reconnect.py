"""Regression tests for per-game mid-match RECONNECT handling
(audit runtime-games-2026-06-06).

The mirror of test_disconnect.py: a puck that the heartbeat sweep retired
must be able to rejoin an in-progress match and resume scoring when it
starts talking again, instead of being permanently stranded (and, for
turn-based games, scored zero every remaining round). Each test drives the
real MatchManager path — force a disconnect through the genuine sweep, then
send real input whose heartbeat ping is the reconnect transition.

Resume is wired for the turn-based games (SpeedPyramid, PuckGolf). PuckRacer
and Smash are intentionally non-resumable (real-time / elimination); those
cases assert the deliberate no-op.
"""
from __future__ import annotations

from runtime import Cue, InputEvent

from conftest import force_disconnect, make_players

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


def _cue_targets(update, cue):
    return [c.target for c in update.cues if c.cue == cue]


def _two_question_fixture():
    return [
        Question(id=101, setup="s1", question="q1",
                 answers={"A": "a", "B": "b", "C": "c", "D": "d"},
                 correct="A", category="Test", time_limit_ms=10_000),
        Question(id=102, setup="s2", question="q2",
                 answers={"A": "a", "B": "b", "C": "c", "D": "d"},
                 correct="B", category="Test", time_limit_ms=10_000),
    ]


def test_speed_pyramid_reconnect_resumes_scoring(manager, writer):
    """Puck 2 drops in round 1 (force-locked TIMEOUT), reconnects, then
    answers round 2 correctly and scores — instead of being force-locked
    TIMEOUT forever."""
    players = make_players(2)
    match = manager.create(
        location_id="loc", game_slug="speed_pyramid", table_number=1,
        players=players, questions=_two_question_fixture(),
    )
    game = match.game

    # Round 1 (index 0): puck 1 correct, puck 2 disconnects -> force-locked
    # TIMEOUT -> round advances.
    _answer(manager, match.id, 1, "A")
    force_disconnect(manager, match.id, 2)
    manager.tick(match.id)
    assert game.round_index == 1
    assert 2 in game.disconnected
    assert game.locked[2]["tier"] == "TIMEOUT"  # round 1 missed, stays missed

    # Puck 2 reconnects by answering round 2 (Q2 correct = B). The ping is a
    # reconnect transition -> on_puck_reconnected un-retires it BEFORE the
    # answer is processed.
    update = _answer(manager, match.id, 2, "B")
    assert 2 in _cue_targets(update, Cue.PLAYER_JOINED), "no reconnect cue"
    assert 2 not in game.disconnected, "puck 2 was not un-retired"

    # Puck 1 answers round 2 too -> match completes. Puck 2 scored on the
    # round it played after reconnecting, so its final total is > 0.
    _answer(manager, match.id, 1, "A")  # puck 1 wrong on Q2 (correct=B)
    assert game.is_over()
    finals = writer.final_scores(match.id)
    mp2 = writer.match_pucks[(match.id, "uuid-2")]
    assert finals[mp2] > 0, "reconnected puck must score the round it played"


def test_speed_pyramid_reconnect_is_noop_if_never_disconnected(manager, writer):
    """A normal input (no prior disconnect) must not spuriously fire the
    reconnect hook / cue."""
    players = make_players(2)
    match = manager.create(
        location_id="loc", game_slug="speed_pyramid", table_number=1,
        players=players, questions=_two_question_fixture(),
    )
    update = _answer(manager, match.id, 1, "A")
    assert _cue_targets(update, Cue.PLAYER_JOINED) == []


def test_puck_golf_reconnect_redeals_on_next_hole(manager, writer):
    """A retired golfer that reconnects is dealt back in on the next hole
    instead of being skipped for the rest of the course."""
    players = make_players(2)
    match = manager.create(
        location_id="loc", game_slug="puck_golf", table_number=1,
        players=players,
        course=[Hole(number=1, distance=50.0, par=2),
                Hole(number=2, distance=50.0, par=2)],
    )
    game = match.game

    # Puck 1 (turn holder) disconnects on hole 1 -> retired, turn passes.
    force_disconnect(manager, match.id, 1)
    manager.tick(match.id)
    assert game.player_state[1].disconnected
    assert game.get_state()["current_turn_puck_index"] == 2

    # Puck 1 reconnects (its input ping is the reconnect transition).
    update = manager.on_input(
        match.id, InputEvent(puck_index=1, tilt_x=0.0, tilt_y=5.0))
    assert 1 in _cue_targets(update, Cue.PLAYER_JOINED)
    assert not game.player_state[1].disconnected, "golfer not un-retired"

    # Puck 2 sinks hole 1 -> advance to hole 2 -> the reconnected puck 1 is
    # dealt back in (hole_done reset to False because it's no longer retired).
    manager.on_input(
        match.id,
        InputEvent(puck_index=2, tilt_x=0.0, tilt_y=30.0, shake=44.0,
                   button_tap=True),
    )
    assert game.hole_index == 1, "should have advanced to hole 2"
    assert not game.player_state[1].hole_done, "reconnected golfer not re-dealt"


def test_puck_racer_reconnect_stays_eliminated(manager, writer):
    """Racer is intentionally non-resumable: a reconnect does not revive a
    frozen-out racer."""
    players = make_players(2)
    match = manager.create(
        location_id="loc", game_slug="puck_racer", table_number=1,
        players=players,
    )
    game = match.game
    manager.on_input(match.id, InputEvent(puck_index=1, button_hold=True))
    force_disconnect(manager, match.id, 1)
    manager.tick(match.id)
    assert game.racers[1].disconnected

    # Reconnect attempt — must NOT un-freeze the racer.
    update = manager.on_input(match.id, InputEvent(puck_index=1, button_hold=True))
    assert _cue_targets(update, Cue.PLAYER_JOINED) == []
    assert game.racers[1].disconnected, "racer must stay eliminated (non-resumable)"
