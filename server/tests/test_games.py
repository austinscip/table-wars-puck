"""
Tier 4 game-correctness regressions.
"""

from __future__ import annotations

from runtime import InputEvent

from conftest import make_players

from games.smash import Smash, ARENA_X


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
