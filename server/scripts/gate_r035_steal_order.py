"""Gate for R035 — STEAL must be order-independent, sum to half, answer-gated.

Bug: server/pair_routes.py _apply_power_up_arms STEAL loop (654-688).
  1. Order-dependence: the STEAL pass iterates `for target_pid, ans in
     answers.items()` and mutates `ans['points']` in place. A later
     target's stolen amount is computed from points an earlier iteration
     already mutated, so a mutual steal (p1<->p2) yields ASYMMETRIC
     results purely from dict insertion (puck_id) order.
  2. Floor-division loss: stolen_each = target_points//2//len(incoming).
     target=100 with 3 stealers -> 100//2//3 = 16 each -> total 48, but
     the contract is "half the target's points" (50). Target keeps 52.
  3. Timed-out firer still steals: TIMEOUT entries are filled into
     `answers` (pair_routes 1506-1518) BEFORE this runs, so a firer that
     did NOTHING all round has a non-None answers[firer] entry and gets
     credited (line 681). A puck that did nothing profits.

This gate exercises _apply_power_up_arms directly (unit-level, no
browser, _socketio stays None) and asserts:
  (a) mutual steal gives identical results regardless of dict key order,
  (b) total stolen from a target == target_points // 2 (not 48),
  (c) a TIMEOUT firer steals 0.

Gate assertion name: steal-order-independent-and-answer-gated
Proven: fail-on-current expected; pass-on-fix.
"""
from __future__ import annotations

import copy
import sys

# Ensure the server package dir is importable (scripts/ lives under it).
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from verify_lib import log, Verifier

import pair_routes


def _ans(points: int, tier: str = "EPIC", correct: bool = True) -> dict:
    """Build a minimal current_round_answers entry."""
    return {
        "answer": "A",
        "is_correct": correct,
        "points": points,
        "tier": tier,
        "response_time_ms": 1200,
        "color": "#ff0000",
        "color_name": "Red",
    }


def _timeout_ans() -> dict:
    """A TIMEOUT entry exactly as pair_routes fills it (1506-1518)."""
    return {
        "answer": None,
        "is_correct": False,
        "points": 0,
        "tier": "TIMEOUT",
        "response_time_ms": None,
        "color": "#00ff00",
        "color_name": "Green",
    }


def _make_state(arms: dict) -> dict:
    return {
        "power_up_arms": copy.deepcopy(arms),
        "cumulative_scores": {},
    }


def _run_steal(answers: dict, arms: dict) -> dict:
    """Apply _apply_power_up_arms (socketio None) to a fresh state and
    return the post-mutation answers (points only)."""
    answers = copy.deepcopy(answers)
    state = _make_state(arms)
    # _socketio is module-global and defaults to None; do not touch it.
    pair_routes._apply_power_up_arms(state, "TESTCODE", 9999, answers)
    return {pid: int(a["points"]) for pid, a in answers.items()}, state


def run() -> int:
    v = Verifier()
    assert pair_routes._socketio is None, \
        "expected _socketio None at unit level — refusing to emit sockets"

    # ---- Case 1: mutual steal p1<->p2, both at 1000pt -----------------
    # p1 fires STEAL at p2; p2 fires STEAL at p1. Symmetric setup.
    # A correct implementation must yield identical final points for both
    # pucks regardless of which order the answers dict is iterated.
    arms_mutual = {
        1: {"double": False, "reveal": False, "shield": False,
            "incoming_steals": [2]},  # p2 steals from p1
        2: {"double": False, "reveal": False, "shield": False,
            "incoming_steals": [1]},  # p1 steals from p2
    }
    answers_a = {1: _ans(1000), 2: _ans(1000)}        # p1 first
    answers_b = {2: _ans(1000), 1: _ans(1000)}        # p2 first (reversed)

    res_a, _ = _run_steal(answers_a, arms_mutual)
    res_b, _ = _run_steal(answers_b, arms_mutual)
    log(f"mutual order A (p1 first): {res_a}")
    log(f"mutual order B (p2 first): {res_b}")

    order_independent = (res_a == res_b)

    # ---- Case 2: floor-division — total stolen must be target//2 ------
    # target p9 has 100pt, three firers (p1,p2,p3) all steal from it.
    # Contract: half of 100 == 50 transferred total. Current build:
    # 100//2//3 = 16 each -> 48 total, target keeps 52.
    arms_three = {
        9: {"double": False, "reveal": False, "shield": False,
            "incoming_steals": [1, 2, 3]},
    }
    answers_three = {
        9: _ans(100), 1: _ans(0, tier="WRONG", correct=False),
        2: _ans(0, tier="WRONG", correct=False),
        3: _ans(0, tier="WRONG", correct=False),
    }
    res_three, _ = _run_steal(answers_three, arms_three)
    target_after = res_three[9]
    total_stolen = 100 - target_after
    firers_total = res_three[1] + res_three[2] + res_three[3]
    log(f"three-stealers: target_after={target_after} "
        f"total_stolen={total_stolen} firers_total={firers_total}")
    half_correct = (total_stolen == 50 and firers_total == 50)

    # ---- Case 3: TIMEOUT firer must steal 0 ---------------------------
    # p2 armed STEAL at p1 but then TIMED OUT (did nothing). pair_routes
    # fills a TIMEOUT entry for p2 BEFORE this runs, so answers[2] exists
    # with tier TIMEOUT. A puck that did nothing must NOT profit.
    arms_timeout = {
        1: {"double": False, "reveal": False, "shield": False,
            "incoming_steals": [2]},  # p2 (timed out) steals from p1
    }
    answers_timeout = {1: _ans(800), 2: _timeout_ans()}
    res_to, state_to = _run_steal(answers_timeout, arms_timeout)
    timeout_firer_points = res_to[2]
    # The non-answerer could be credited either via firer_ans["points"]
    # (it has an entry) or the cumulative side-channel; check both.
    side_channel = int(state_to["cumulative_scores"].get(2, 0))
    log(f"timeout firer: round_points={timeout_firer_points} "
        f"side_channel={side_channel} target_after={res_to[1]}")
    timeout_gated = (timeout_firer_points == 0 and side_channel == 0
                     and res_to[1] == 800)

    # ---- Decisive assertion -------------------------------------------
    ok = order_independent and half_correct and timeout_gated
    v.check(
        "steal-order-independent-and-answer-gated",
        ok,
        f"order_independent={order_independent} "
        f"(A={res_a} B={res_b}); "
        f"half_correct={half_correct} (total_stolen={total_stolen}, "
        f"want 50); "
        f"timeout_gated={timeout_gated} "
        f"(firer_round={timeout_firer_points}, side={side_channel}, "
        f"target_after={res_to[1]}, want firer 0 / target 800)",
    )

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
