"""
Regression tests for per-game mid-match disconnect handling (Tier 1,
item 1).

Each test drives a real match through the MatchManager — create, real
on_input / tick frames, a heartbeat-driven disconnect, and finalisation —
and asserts the *game* reacted (force-locked, passed the turn, eliminated),
not merely that a PLAYER_LEFT cue was emitted. The bug this guards against
is the silent-puck hang: a game waiting forever on input that will never
arrive.

The disconnect itself goes through the genuine sweep path
(HeartbeatTracker.sweep -> Game.on_puck_disconnected); see
conftest.force_disconnect.
"""

from __future__ import annotations

from runtime import Cue, InputEvent

from conftest import force_disconnect, make_players

from games.speed_pyramid import Question
from games.puck_golf import Hole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Tilt vectors that select each Speed Pyramid answer letter (north=A,
# east=B, south=C, west=D), comfortably above MIN_TILT.
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


def _two_question_fixture():
    return [
        Question(
            id=101,
            setup="s1",
            question="q1",
            answers={"A": "a", "B": "b", "C": "c", "D": "d"},
            correct="A",
            category="Test",
            time_limit_ms=10_000,
        ),
        Question(
            id=102,
            setup="s2",
            question="q2",
            answers={"A": "a", "B": "b", "C": "c", "D": "d"},
            correct="B",
            category="Test",
            time_limit_ms=10_000,
        ),
    ]


def _cue_targets(update, cue):
    return [c.target for c in update.cues if c.cue == cue]


# ---------------------------------------------------------------------------
# Base hook
# ---------------------------------------------------------------------------


def test_base_hook_default_is_noop(manager, writer):
    """A game that doesn't override on_puck_disconnected must not break
    the sweep — the manager still emits PLAYER_LEFT, just no game
    reaction."""
    players = make_players(2)
    match = manager.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=players,
        questions=_two_question_fixture(),
    )
    # Neuter the game's reaction to simulate a game that inherits the
    # default no-op.
    match.game.on_puck_disconnected = lambda puck_index: None

    force_disconnect(manager, match.id, 2)
    update = manager.tick(match.id)

    assert 2 in _cue_targets(update, Cue.PLAYER_LEFT)
    # No reaction => the game state is untouched (puck 2 never locked).
    assert match.game.locked.get(2) is None


# ---------------------------------------------------------------------------
# Speed Pyramid — force-lock TIMEOUT
# ---------------------------------------------------------------------------


def test_speed_pyramid_disconnect_force_locks_and_advances(manager, writer):
    players = make_players(2)
    match = manager.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=players,
        questions=_two_question_fixture(),
    )
    game = match.game

    # Puck 1 answers Q1 correctly; puck 2 stays silent.
    _answer(manager, match.id, 1, "A")
    assert game.round_index == 0
    assert game.locked[1] is not None
    assert game.locked.get(2) is None

    # Puck 2 disconnects. The sweep must force-lock it as TIMEOUT and,
    # since that's the last unlocked puck, advance the round.
    force_disconnect(manager, match.id, 2)
    update = manager.tick(match.id)

    assert 2 in _cue_targets(update, Cue.PLAYER_LEFT)
    assert game.locked[2] is not None, "disconnected puck was not force-locked"
    assert game.locked[2]["tier"] == "TIMEOUT"
    assert game.locked[2]["points"] == 0
    assert game.round_index == 1, "round did not advance after the disconnect"

    # A round score event for puck 2 (0 points) reached the writer.
    mp2 = writer.match_pucks[(match.id, "uuid-2")]
    puck2_rounds = [
        s
        for s in writer.scores
        if s["match_puck_id"] == mp2 and s["event_type"] == "round"
    ]
    assert puck2_rounds and puck2_rounds[-1]["score_total"] == 0

    # The match must still be completable: puck 1 answers Q2; the now-
    # known-disconnected puck 2 is auto-settled so the final round resolves
    # without hanging.
    _answer(manager, match.id, 1, "B")
    assert game.is_over(), "match did not finish with a permanently-gone puck"

    # Finalisation persisted final scores for both pucks; the live player
    # outscores the one who left.
    finals = writer.final_scores(match.id)
    mp1 = writer.match_pucks[(match.id, "uuid-1")]
    assert finals[mp1] > finals[mp2]
    assert finals[mp2] == 0
    assert any(mid == match.id for mid, _ in writer.finished)


# ---------------------------------------------------------------------------
# Puck Golf — pass the turn / retire the puck
# ---------------------------------------------------------------------------


def test_puck_golf_disconnect_passes_turn_and_finishes(manager, writer):
    players = make_players(2)
    match = manager.create(
        location_id="loc",
        game_slug="puck_golf",
        table_number=1,
        players=players,
        course=[Hole(number=1, distance=50.0, par=2)],
    )
    game = match.game

    # Puck 1 holds the turn (turn_queue=[1,2], index 0). Disconnect it.
    assert game.get_state()["current_turn_puck_index"] == 1
    force_disconnect(manager, match.id, 1)
    update = manager.tick(match.id)

    assert 1 in _cue_targets(update, Cue.PLAYER_LEFT)
    assert game.player_state[1].disconnected
    assert game.player_state[1].hole_done
    assert (
        game.get_state()["current_turn_puck_index"] == 2
    ), "turn did not pass to the live puck"

    # Puck 2 sinks the hole in one stroke (aim north toward the cup at
    # (0,50), power ~35 -> ~49 yards) and the match finalises.
    manager.on_input(
        match.id,
        InputEvent(puck_index=2, tilt_x=0.0, tilt_y=30.0, shake=44.0, button_tap=True),
    )
    assert game.player_state[2].hole_done
    assert game.is_over()
    assert any(mid == match.id for mid, _ in writer.finished)


def test_puck_golf_all_disconnect_finalises(manager, writer):
    players = make_players(2)
    match = manager.create(
        location_id="loc",
        game_slug="puck_golf",
        table_number=1,
        players=players,
        course=[Hole(number=1, distance=50.0, par=2)],
    )
    game = match.game

    force_disconnect(manager, match.id, 1)
    manager.tick(match.id)
    assert not game.is_over()

    force_disconnect(manager, match.id, 2)
    manager.tick(match.id)
    assert game.is_over(), "match did not finalise after every puck left"
    assert any(mid == match.id for mid, _ in writer.finished)


# ---------------------------------------------------------------------------
# Puck Racer — mark eliminated, frozen out of contention
# ---------------------------------------------------------------------------


def test_puck_racer_disconnect_eliminates_and_race_resolves(manager, writer):
    players = make_players(2)
    match = manager.create(
        location_id="loc",
        game_slug="puck_racer",
        table_number=1,
        players=players,
    )
    game = match.game

    # Both throttle; puck 1 disconnects early and must freeze while puck 2
    # drives to the finish line. Puck 2's input is refreshed periodically
    # so its own heartbeat stays alive across the race.
    manager.on_input(match.id, InputEvent(puck_index=1, button_hold=True))
    manager.on_input(match.id, InputEvent(puck_index=2, button_hold=True))

    disconnected = False
    for t in range(400):
        if t == 10:
            force_disconnect(manager, match.id, 1)
            disconnected = True
        if t % 15 == 0:
            manager.on_input(match.id, InputEvent(puck_index=2, button_hold=True))
        manager.tick(match.id)
        if game.is_over():
            break

    assert disconnected
    assert game.racers[1].disconnected, "puck 1 was not eliminated on disconnect"
    assert not game.racers[1].finished, "a disconnected racer must not 'finish'"
    assert game.racers[2].finished, "live racer never reached the line"
    assert game.racers[2].position > game.racers[1].position
    assert game.is_over()

    finals = writer.final_scores(match.id)
    mp1 = writer.match_pucks[(match.id, "uuid-1")]
    mp2 = writer.match_pucks[(match.id, "uuid-2")]
    assert finals[mp2] > finals[mp1], "the racer who left should not win"
    assert any(mid == match.id for mid, _ in writer.finished)


# ---------------------------------------------------------------------------
# Smash — mark eliminated, last fighter standing wins
# ---------------------------------------------------------------------------


def test_smash_disconnect_eliminates_and_ends_match(manager, writer):
    players = make_players(2)
    match = manager.create(
        location_id="loc",
        game_slug="smash",
        table_number=1,
        players=players,
    )
    game = match.game

    # A couple of real frames, then puck 1 leaves. With one fighter left
    # standing, the brawl must end with puck 2 the winner.
    manager.on_input(match.id, InputEvent(puck_index=1, tilt_x=10.0, button_tap=True))
    manager.on_input(match.id, InputEvent(puck_index=2, tilt_x=-10.0))

    force_disconnect(manager, match.id, 1)
    update = manager.tick(match.id)

    assert 1 in _cue_targets(update, Cue.PLAYER_ELIMINATED)
    assert game.fighters[1].eliminated, "disconnected fighter not eliminated"
    assert game.is_over()
    assert game.winner_index == 2

    finals = writer.final_scores(match.id)
    mp2 = writer.match_pucks[(match.id, "uuid-2")]
    assert mp2 in finals
    assert any(mid == match.id for mid, _ in writer.finished)
