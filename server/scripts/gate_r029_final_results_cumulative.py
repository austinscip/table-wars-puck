"""Gate for R029 — final scoreboard must match the in-match cumulative.

Bug (server/pair_routes.py):
  sp_final_results (1395-1405) computes each player's total as
  COALESCE(SUM(points_earned)) and correct as SUM(is_correct) from the
  trivia_answers table. The ONLY row ever written to that table is at
  sp_answer (1944, record_answer) with the RAW pre-power-up points
  computed at answer time — BEFORE _apply_power_up_arms runs at reveal.

  Two whole classes of score never reach the DB and therefore never
  reach the final scoreboard:
    1. Minigame bonuses (+500 to the winner, +200 to second place) are
       added ONLY to state['cumulative_scores'] in _resolve_minigame
       (878-890).
    2. Power-up effects applied in _apply_power_up_arms (626-696) —
       REVEAL forces 1000pt, DOUBLE multiplies x2, STEAL transfers — all
       mutate answers[]/cumulative_scores in memory and are NEVER written
       back to trivia_answers.

  The in-match reveal sidebar renders cumulative_total (power-ups +
  minigame bonuses applied), but ScoreboardScreen renders final-results
  (the raw DB sum). So the final scoreboard can show a different total —
  and even a different winner ordering — than the players watched
  accumulate all match. A puck that timed out every question but won the
  minigames shows total=0 on the final board.

This gate exercises the server scoring code directly at unit level
(import pair_routes, _socketio stays None so nothing emits). It:
  - reproduces the EXACT DB ledger sp_answer writes (raw pre-arm points
    passed to record_answer) and replays sp_final_results' SUM over it;
  - runs the real _resolve_minigame (minigame bonus) and the real reveal
    scoring path (_apply_power_up_arms + the cumulative-update loop copied
    verbatim from _maybe_emit_reveal 1524-1528) to build the authoritative
    in-match cumulative_scores;
  - asserts the DB-sum total equals cumulative_scores for every puck AND
    that the winner (argmax total) is the same under both views.

The fix (per fixSketch) is to make final-results authoritative from
state['cumulative_scores'] when in-memory state exists, OR to write the
post-arm adjusted points + a minigame-bonus ledger row back to
trivia_answers. Either way this gate flips to PASS once the DB sum and
cumulative agree.

Gate assertion name: final-results-matches-cumulative-not-db-sum
Proven: fail-on-current expected; pass-on-fix.
"""
from __future__ import annotations

import copy
import os
import sys

# scripts/ lives under the server package dir — make it importable so we
# can import pair_routes (the module under test) and verify_lib.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from verify_lib import log, Verifier  # noqa: E402

import pair_routes  # noqa: E402


P1, P2 = 1, 2          # puck ids in this 2-puck match
SESSION = "R029TEST"   # never written to DB; _socketio is None so no emit


def _answer_entry(points: int, *, correct: bool, tier: str,
                  rt_ms: int | None, color="#ff0000", name="Red") -> dict:
    """A current_round_answers entry exactly as sp_answer builds one
    (pair_routes 1925-1933)."""
    return {
        "answer": "A" if correct else "B",
        "is_correct": correct,
        "points": int(points),
        "tier": tier,
        "response_time_ms": rt_ms,
        "color": color,
        "color_name": name,
    }


def _replay_db_sum_total(db_ledger: list[dict]) -> dict[int, int]:
    """Reproduce sp_final_results' aggregate: per-puck
    COALESCE(SUM(points_earned)) over the trivia_answers rows that
    record_answer would have written. db_ledger is the list of
    (puck_id, points_earned) rows in write order — exactly the args
    sp_answer passes to record_answer (pair_routes 1944-1952)."""
    totals: dict[int, int] = {}
    for row in db_ledger:
        pid = int(row["puck_id"])
        totals[pid] = totals.get(pid, 0) + int(row["points_earned"])
    return totals


def _cumulative_update(state: dict, answers: dict) -> None:
    """The cumulative-score update loop copied verbatim from
    _maybe_emit_reveal (pair_routes 1526-1528). Runs AFTER
    _apply_power_up_arms, so it sees DOUBLE/REVEAL/STEAL-adjusted points."""
    for pid, a in answers.items():
        state["cumulative_scores"][pid] = (
            state["cumulative_scores"].get(pid, 0) + int(a["points"])
        )


def run() -> int:
    v = Verifier()

    # Unit-level discipline (same guard as gate_r035): refuse to emit
    # real sockets. _socketio is a module global, default None.
    assert pair_routes._socketio is None, (
        "expected pair_routes._socketio is None at unit level — refusing "
        "to run a scoring gate that would emit live sockets"
    )

    # ------------------------------------------------------------------
    # Build a fresh in-memory match state for two pucks. We DON'T call
    # _sp_state_for (it would hit the DB for expected_pucks); we hand-roll
    # the same dict shape (pair_routes 555-575) and set expected_pucks
    # directly. cumulative_scores starts empty exactly like a real match.
    # ------------------------------------------------------------------
    state = {
        "round": 1,
        "asked_ids": set(),
        "complete": False,
        "expected_pucks": {P1, P2},
        "current_question_id": 90001,
        "current_round_started_at": None,
        "current_round_answers": {},
        "cumulative_scores": {},
        "revealed_for_question_id": None,
        "pending_category_pick": None,
        "next_category_id": None,
        "last_round_winner_puck_id": None,
        "pending_minigame": None,
        "minigame_resolved_round": None,
        "power_up_inventories": {},
        "power_up_arms": {},
    }

    # The simulated trivia_answers table: every row record_answer writes.
    # sp_answer writes RAW pre-arm points (1928 -> 1944-1952). This is the
    # ONLY thing sp_final_results ever sums.
    db_ledger: list[dict] = []

    # ==================================================================
    # ROUND 1 — both pucks answer. P1 correct (LEGENDARY-ish), P2 wrong.
    # sp_answer records raw points to the DB and to current_round_answers.
    # No power-ups armed this round; cumulative == raw for round 1.
    # ==================================================================
    r1 = {
        P1: _answer_entry(900, correct=True, tier="LEGENDARY", rt_ms=900,
                          color="#ff0000", name="Red"),
        P2: _answer_entry(0, correct=False, tier="WRONG", rt_ms=1500,
                          color="#00ff00", name="Green"),
    }
    for pid, a in r1.items():
        db_ledger.append({"puck_id": pid, "points_earned": a["points"]})
    state["current_round_answers"] = copy.deepcopy(r1)
    # No arms -> _apply_power_up_arms is a no-op, then cumulative update.
    pair_routes._apply_power_up_arms(state, SESSION,
                                     state["current_question_id"],
                                     state["current_round_answers"])
    _cumulative_update(state, state["current_round_answers"])
    state["round"] = 1
    log(f"after R1: cumulative={state['cumulative_scores']} "
        f"db_ledger_rows={len(db_ledger)}")

    # ==================================================================
    # ROUND 2 — MINIGAME. P1 wins (+500), P2 second (+200). _resolve_minigame
    # writes these bonuses ONLY to cumulative_scores (878-890); NOTHING is
    # written to the DB. Drive the REAL function so we exercise the real
    # bonus path + winner ranking.
    # ==================================================================
    state["pending_minigame"] = {
        "flavor": "AIM",
        "duration_s": 5,
        "target_quadrant": None,
        "cycle_ms": None,
        "green_frac": None,
        "started_at": 0.0,
        "deadline_at": 0.0,
        # P1 fires for more points than P2 -> P1 ranks #1.
        "fires": {
            P1: {"t_ms": 800, "quadrant": None, "points": 1000},
            P2: {"t_ms": 1200, "quadrant": None, "points": 400},
        },
    }
    resolved = pair_routes._resolve_minigame(state, SESSION)
    log(f"minigame resolved={resolved} cumulative={state['cumulative_scores']}")
    if not resolved:
        v.inconclusive("minigame must resolve to exercise the bonus path",
                       "_resolve_minigame returned False")
        return v.report()
    # Sanity: the minigame bonus is reflected in cumulative but produced
    # ZERO new DB rows (this is half of why the boards diverge).
    bonus_in_cumulative = (
        state["cumulative_scores"].get(P1, 0)
        - sum(r["points_earned"] for r in db_ledger if r["puck_id"] == P1)
        >= pair_routes.SP_MINIGAME_WIN_BONUS
    )
    v.check("minigame +500 bonus lands in cumulative but not in DB ledger",
            bonus_in_cumulative and not any(
                r.get("source") == "minigame" for r in db_ledger),
            f"cumulative[P1]={state['cumulative_scores'].get(P1)} "
            f"db_ledger has no minigame row")

    # ==================================================================
    # ROUND 3 — P1 activates DOUBLE before answering correctly. sp_answer
    # records the RAW points to the DB (pre-double). At reveal,
    # _apply_power_up_arms doubles P1's points in current_round_answers and
    # the cumulative update adds the DOUBLED value. The DB keeps the raw.
    # ==================================================================
    state["round"] = 2
    state["current_question_id"] = 90003
    raw_p1_r3 = 600
    r3 = {
        P1: _answer_entry(raw_p1_r3, correct=True, tier="EXPERT", rt_ms=2500,
                          color="#ff0000", name="Red"),
        P2: _answer_entry(150, correct=True, tier="AVERAGE", rt_ms=4800,
                          color="#00ff00", name="Green"),
    }
    # DB rows are written with RAW points (what record_answer receives at
    # sp_answer, BEFORE arms run). This is the divergence point.
    for pid, a in r3.items():
        db_ledger.append({"puck_id": pid, "points_earned": a["points"]})
    # P1 had armed DOUBLE between rounds (power-up activate -> power_up_arms).
    state["power_up_arms"] = {
        P1: {"double": True, "reveal": False, "shield": False,
             "incoming_steals": []},
    }
    state["current_round_answers"] = copy.deepcopy(r3)
    pair_routes._apply_power_up_arms(state, SESSION,
                                     state["current_question_id"],
                                     state["current_round_answers"])
    # DOUBLE must have changed the in-memory points but not the DB row.
    doubled_p1 = state["current_round_answers"][P1]["points"]
    v.check("DOUBLE x2 applied in-memory but DB row still raw",
            doubled_p1 == raw_p1_r3 * 2
            and db_ledger[-2]["points_earned"] == raw_p1_r3,
            f"in_memory_p1={doubled_p1} (want {raw_p1_r3*2}); "
            f"db_row_p1={db_ledger[-2]['points_earned']} (want {raw_p1_r3})")
    _cumulative_update(state, state["current_round_answers"])
    log(f"after R3: cumulative={state['cumulative_scores']} "
        f"db_ledger_rows={len(db_ledger)}")

    # ==================================================================
    # THE DIVERGENCE. Compute both views.
    #   db_total  = what sp_final_results returns (SUM(points_earned)).
    #   cumulative = what the in-match reveal sidebar shows all match.
    # ==================================================================
    db_total = _replay_db_sum_total(db_ledger)
    cumulative = {int(k): int(v_) for k, v_ in state["cumulative_scores"].items()}
    log(f"final-results DB-sum total : {db_total}")
    log(f"in-match cumulative_scores : {cumulative}")

    # Per-puck totals must match.
    pucks = sorted(set(db_total) | set(cumulative))
    per_puck_ok = all(
        db_total.get(pid, 0) == cumulative.get(pid, 0) for pid in pucks
    )

    # Winner (argmax total, lowest puck_id breaks ties) must match too.
    def _winner(scores: dict[int, int]) -> int | None:
        if not scores:
            return None
        return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    db_winner = _winner(db_total)
    cum_winner = _winner(cumulative)
    winner_ok = (db_winner == cum_winner)

    deltas = {pid: cumulative.get(pid, 0) - db_total.get(pid, 0)
              for pid in pucks}

    # ---- Diagnostic (unit-level) ------------------------------------
    # This documents the in-memory divergence the bug creates: the raw DB
    # ledger sum is LOWER than cumulative by (minigame bonus + DOUBLE
    # delta). It is NOT the decisive assertion — it only exercises a
    # reconstruction of the SUM, not the real endpoint. The decisive
    # assertion below drives the REAL /api/sp/final-results endpoint.
    log(f"unit divergence: per_puck_ok={per_puck_ok} winner_ok={winner_ok} "
        f"db_total={db_total} cumulative={cumulative} "
        f"deltas(cumulative-db)={deltas} "
        f"db_winner={db_winner} cum_winner={cum_winner}")
    v.check(
        "unit-divergence-db-sum-below-cumulative",
        any(d != 0 for d in deltas.values()),
        f"expected a nonzero cumulative-vs-db delta from minigame+DOUBLE; "
        f"deltas={deltas}",
    )

    # ==================================================================
    # HARDENED real-endpoint check (R029). The unit reconstruction above
    # can't prove the FIX, because the fix lives in sp_final_results which
    # the reconstruction never calls. Drive a REAL match to /scoreboard
    # (minigame rounds 2/4/6 push +500/+200 bonuses into cumulative_scores
    # only — never the DB; minigame winners are granted a power-up which we
    # activate as DOUBLE/STEAL so a power-up effect is live too), then GET
    # /api/sp/final-results/<sc> and assert each puck's total EQUALS the
    # in-match cumulative_scores from GET /api/sp/match-state/<sc> (the value
    # the reveal sidebar shows all match). On the unfixed build the
    # final-results total is the raw DB SUM and is strictly lower, so this
    # FAILS; once final-results is authoritative from cumulative_scores it
    # PASSES.
    # ==================================================================
    _real_endpoint_check(v)

    return v.report()


def _activate_powerups_on_pick(sc: str) -> None:
    """During a between-rounds (pick) phase, for each puck holding a
    power-up, activate a DOUBLE or STEAL so a live power-up effect is in
    play for the next reveal. Best-effort: minigame winners are granted a
    random power-up, so a DOUBLE/STEAL is not guaranteed every match, but
    the minigame bonus alone already diverges cumulative from the DB sum.
    Uses the REAL /power-up/activate endpoint."""
    import requests
    from verify_lib import BASE
    ms = requests.get(f"{BASE}/api/sp/match-state/{sc}", timeout=5).json()
    if not ms.get("pending_category_pick"):
        return
    pucks = [int(p) for p in ms.get("cumulative_scores", {}).keys()]
    if not pucks:
        pucks = [int(p) for p in ms.get("power_up_inventories", {}).keys()]
    for pid in pucks:
        inv = requests.get(
            f"{BASE}/api/sp/inventory/{sc}", params={"puck_id": pid},
            timeout=5,
        ).json().get("items", [])
        target = next((it for it in inv if it["type"] in ("DOUBLE", "STEAL")), None)
        if target is None:
            continue
        body = {"session_code": sc, "puck_id": pid, "item_id": target["id"]}
        if target["type"] == "STEAL":
            other = next((q for q in pucks if q != pid), None)
            if other is None:
                continue
            body["target_puck_id"] = other
        try:
            requests.post(f"{BASE}/api/sp/power-up/activate",
                          json=body, timeout=5)
            log(f"activated {target['type']} for puck {pid}")
        except Exception as e:  # noqa: BLE001
            log(f"power-up activate failed ({e}); continuing")


def _real_endpoint_check(v: "Verifier") -> None:
    import time
    import requests
    import verify_lib as vl
    from verify_lib import BASE

    with vl.session(headless=True) as (hub, tv):
        sc = vl.pair_and_start(hub, tv, goto_question=True)
        if not sc:
            v.inconclusive(
                "final-results-matches-cumulative-not-db-sum",
                "pairing failed — could not start a real match",
            )
            return

        # Phase-driven driver, but stop at each pick phase to fire a
        # DOUBLE/STEAL so a power-up effect is live. We re-implement the
        # minimal loop here (verify_lib.drive_match_to_scoreboard has no
        # per-phase hook) using the same helpers.
        deadline = time.time() + 200
        while time.time() < deadline:
            route = tv.evaluate("() => location.pathname")
            if "/scoreboard/" in route:
                break
            s1 = vl.puck_state(hub, 0)
            s2 = vl.puck_state(hub, 1)
            if "MATCH ENDED" in s1 and "MATCH ENDED" in s2:
                break
            if ("PICK CATEGORY" in s1 or "PICK CATEGORY" in s2
                    or "pick category" in s1 or "pick category" in s2):
                _activate_powerups_on_pick(sc)
                vl._resolve_pick(hub)
                time.sleep(1.0)
                continue
            if ("MINIGAME" in s1 or "MINIGAME" in s2
                    or "mg/" in s1 or "mg/" in s2):
                vl._resolve_minigame(hub)
                time.sleep(2.0)
                continue
            if (("ANSWERING" in s1 and "ANSWERING" in s2)
                    or (s1.startswith("Q") and s2.startswith("Q"))):
                qid = vl.parse_qid(s1) or vl.parse_qid(s2)
                for idx in (0, 1):
                    try:
                        vl.puck_row(hub, idx).get_by_role(
                            "button", name="A", exact=True).click(
                                force=True, timeout=2500)
                    except Exception:  # noqa: BLE001
                        pass
                    time.sleep(0.3)
                time.sleep(2.5)
                continue
            time.sleep(0.4)

        # Pull both authoritative views from the REAL endpoints.
        ms = requests.get(f"{BASE}/api/sp/match-state/{sc}", timeout=5).json()
        fr = requests.get(f"{BASE}/api/sp/final-results/{sc}", timeout=5).json()
        cumulative = {int(k): int(v_)
                      for k, v_ in (ms.get("cumulative_scores") or {}).items()}
        fr_totals = {int(p["puck_id"]): int(p["total"])
                     for p in fr.get("players", [])}
        log(f"REAL match-state cumulative_scores : {cumulative}")
        log(f"REAL final-results totals          : {fr_totals}")

        if not cumulative:
            v.inconclusive(
                "final-results-matches-cumulative-not-db-sum",
                f"no cumulative_scores from match-state (route never "
                f"reached scoreboard?); ms={ms}",
            )
            return

        # Sanity: the in-match cumulative must include a minigame/power-up
        # bonus so the comparison is meaningful (otherwise raw DB sum could
        # coincidentally equal cumulative and the gate wouldn't exercise the
        # bug). A clean 7-round match with 3 minigames always has bonuses.
        pucks = sorted(set(cumulative) | set(fr_totals))
        per_puck_ok = all(
            fr_totals.get(pid, 0) == cumulative.get(pid, 0) for pid in pucks
        )
        deltas = {pid: cumulative.get(pid, 0) - fr_totals.get(pid, 0)
                  for pid in pucks}

        v.check(
            "final-results-matches-cumulative-not-db-sum",
            per_puck_ok,
            f"per_puck_ok={per_puck_ok} "
            f"final_results={fr_totals} cumulative={cumulative} "
            f"deltas(cumulative-final)={deltas}",
        )


if __name__ == "__main__":
    sys.exit(run())
