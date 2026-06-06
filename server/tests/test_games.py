"""
Tier 4 game-correctness regressions.
"""

from __future__ import annotations

from runtime import InputEvent

from conftest import make_players

from games.smash import Smash, ARENA_X
from games.speed_pyramid import SpeedPyramid
from games.puck_golf import PuckGolf


def test_speed_pyramid_threads_exclude_ids_to_db(monkeypatch):
    """exclude_ids reaches get_questions so a caller can dedup recently-seen
    questions across matches."""
    import trivia_database

    captured: dict = {}

    def fake_get_questions(count, category_id=None, difficulty=None, exclude_ids=None):
        captured["count"] = count
        captured["exclude_ids"] = exclude_ids
        return []  # empty -> SpeedPyramid falls back to DEFAULT_QUESTIONS

    monkeypatch.setattr(trivia_database, "get_questions", fake_get_questions)
    SpeedPyramid(players=make_players(1), question_count=5, exclude_ids=[10, 20, 30])
    assert captured["exclude_ids"] == [10, 20, 30]
    assert captured["count"] == 5


def test_smash_ko_credited_to_last_hitter_not_high_ko_player():
    """A 3-way FFA: B already has the most KOs, but A is the one who last
    hit C. The KO must go to A. (The old heuristic credited the surviving
    opponent with the most KOs — i.e. B — which is wrong.)"""
    game = Smash(players=make_players(3))
    fA, fB, fC = game.fighters[1], game.fighters[2], game.fighters[3]

    # B is the current KO leader — the wrong answer the old code would pick.
    fB.kos_landed = 5

    # Put A right next to C, facing it; keep B far away.
    fA.x, fA.y, fA.facing_x, fA.facing_y = 0.0, 0.0, 1.0, 0.0
    fC.x, fC.y = 5.0, 0.0  # within ATTACK_RANGE of A
    fB.x, fB.y = -45.0, 25.0

    # A attacks; C records A as its last hitter.
    game.on_input(InputEvent(puck_index=1, button_tap=True))
    assert fC.last_hit_by == 1

    # Ring C out and tick -> KO resolves.
    fC.x = ARENA_X[1] + 100.0
    game.tick()

    assert fA.kos_landed == 1, "KO should be credited to the last hitter (A)"
    assert fB.kos_landed == 5, "B must not be mis-credited"
    assert fC.last_hit_by is None, "last-hit marker resets after the KO"


def test_smash_self_destruct_credits_no_one():
    """A fighter that walks off the stage with no recent hit credits no
    KO to anyone."""
    game = Smash(players=make_players(2))
    fA, fB = game.fighters[1], game.fighters[2]
    # No one hit B; B just leaves the arena.
    fB.x = ARENA_X[0] - 100.0
    game.tick()
    assert fA.kos_landed == 0


def test_smash_simultaneous_ko_still_credits_a_same_tick_killer():
    """A hits B, then BOTH ring out on the same tick. A must still get the KO
    credit for B even though A also dies this tick (audit games-2026-06-06).
    The old code marked A eliminated mid-loop, so B's KO check saw A as out
    and silently dropped the credit."""
    game = Smash(players=make_players(2))
    fA, fB = game.fighters[1], game.fighters[2]
    fA.stocks = fB.stocks = 1  # one stock each -> ring-out eliminates

    # A is B's last hitter.
    fB.last_hit_by = 1
    # Both off opposite edges so both ring out in the same tick.
    fA.x = ARENA_X[0] - 100.0
    fB.x = ARENA_X[1] + 100.0

    game.tick()

    assert fA.eliminated and fB.eliminated
    assert fA.kos_landed == 1, "A must keep KO credit for B despite dying the same tick"
    assert fB.kos_landed == 0


def test_smash_stale_killer_from_prior_tick_gets_no_credit():
    """If the killer was already eliminated in an EARLIER tick, a later KO
    carrying their stale last_hit_by marker credits no one."""
    game = Smash(players=make_players(3))
    fA, fB, fC = game.fighters[1], game.fighters[2], game.fighters[3]
    fA.eliminated = True  # A left in a previous tick
    fC.last_hit_by = 1    # stale marker pointing at A
    fC.stocks = 1
    fC.x = ARENA_X[1] + 100.0
    game.tick()
    assert fA.kos_landed == 0, "a killer out since a prior tick earns no credit"


def test_puck_golf_winner_with_no_players_does_not_crash():
    """Finishing the course with an empty roster must not raise from max() on
    an empty finals dict (audit games-2026-06-06)."""
    game = PuckGolf(players=[])
    # Force completion of the (skeleton) course and finalisation.
    game.hole_index = len(game.course)
    game._advance_turn()  # drives the finish path that computes the winner
    assert game.finished
    assert game.final_scores() == {}
