"""Gate for R030 — Play-Again (sp_reset) must clear prior-match answers.

THE BUG (server-rest):
  sp_reset (pair_routes.py:1442) rebuilds _SP_STATE with a 10-key literal and
  NEVER touches the DB. final-results (pair_routes.py:1384) aggregates
  trivia_answers filtered ONLY by session_id. Play-Again reuses the SAME
  trivia_sessions row, so after a replay final-results SUMs match-1 + match-2
  answers: a puck's `answered` can exceed total_rounds (7) and `total`/`correct`
  are inflated; derive_tier then averages over the combined answered count.

WHAT THIS GATE DOES (purely REST, no browser):
  1. Pair host+joiner and start match A entirely via /api/pair/* (no Hub UI).
  2. Drive match A to completion, answering EVERY round, via:
       POST /api/sp/load-question  (resolving category-pick + minigame phases)
       POST /api/sp/answer         (both pucks)
       POST /api/sp/force-reveal
     Capture final-results -> per-puck `answered` for match A (== 7 each).
  3. POST /api/sp/reset/<code>  (Play-Again).
  4. Drive match B but answer only K (< 7) rounds, then read final-results.
  5. ASSERT each puck's reported `answered` reflects ONLY match B (== K),
     not A+B (== 7+K). On the current build answered is doubled-up
     (e.g. ~7+K, can exceed total_rounds=7) and totals are inflated.

Gate assertion name: play-again-clears-prior-answers
Proven: fail-on-current expected; pass-on-fix.
"""
from __future__ import annotations

import sys
import time

import requests

from verify_lib import BASE, log, Verifier


# ---------------------------------------------------------------------------
# REST driving primitives (no browser — server-rest kind)
# ---------------------------------------------------------------------------

HOST_PUCK = 1
JOINER_PUCK = 2
TIMEOUT = 8
SP_TOTAL_ROUNDS = 7


def _post(path: str, body: dict | None = None) -> requests.Response:
    return requests.post(f"{BASE}{path}", json=body or {}, timeout=TIMEOUT)


def _get(path: str) -> requests.Response:
    return requests.get(f"{BASE}{path}", timeout=TIMEOUT)


def pair_via_rest() -> str | None:
    """Create a lobby + start a match using only /api/pair/* endpoints.
    Returns the session_code (reused across Play-Again), or None on failure."""
    _post("/api/pair/clear", {})
    time.sleep(0.2)
    # Host requests -> creates lobby; joiner requests -> auto-joins.
    r_host = _post("/api/pair/request", {"puck_id": HOST_PUCK})
    if r_host.status_code != 200:
        return None
    pair_code = r_host.json().get("pair_code")
    _post("/api/pair/request", {"puck_id": JOINER_PUCK})
    # Host confirms its dial (joiner is already in the lobby on request).
    _post("/api/pair/confirm", {"puck_id": HOST_PUCK, "code": pair_code})
    # Host starts the match -> creates the trivia session row.
    r_start = _post("/api/pair/start", {"puck_id": HOST_PUCK})
    if r_start.status_code != 200:
        return None
    return r_start.json().get("session_code")


def _resolve_phase(sc: str, payload: dict) -> bool:
    """If load-question returned a category_pick or minigame phase, resolve
    it via REST so the next load-question call advances to the question.
    Returns True if a phase was resolved (caller should re-load)."""
    phase = payload.get("phase")
    if phase == "category_pick":
        picker = payload.get("picker_puck_id")
        offer = payload.get("offer") or []
        if offer:
            _post(f"/api/sp/select-category/{sc}",
                  {"puck_id": picker, "category_id": int(offer[0]["id"])})
        return True
    if phase == "minigame":
        _post(f"/api/sp/minigame/finish/{sc}")
        return True
    return False


def _advance_to_question(sc: str) -> dict | None:
    """POST load-question, resolving any pick/minigame phase, until a real
    question payload (with question.id) is returned. Returns the question
    dict, or None if the match is complete / no question available."""
    for _ in range(8):
        r = _post(f"/api/sp/load-question/{sc}")
        if r.status_code == 409:
            # match_complete
            return None
        if r.status_code != 200:
            time.sleep(0.3)
            continue
        body = r.json()
        if "question" in body and body["question"].get("id"):
            return body["question"]
        if _resolve_phase(sc, body):
            time.sleep(0.3)
            continue
        # Unexpected shape — back off and retry.
        time.sleep(0.3)
    return None


def _answer_question(sc: str, qid: int, pucks: list[int]) -> int:
    """Both pucks answer 'A'. Returns the number of answers the server
    accepted (200) for this question."""
    accepted = 0
    for pid in pucks:
        r = _post("/api/sp/answer", {
            "session_code": sc,
            "puck_id": pid,
            "question_id": qid,
            "answer": "A",
            "response_time_ms": 1500,
        })
        if r.status_code == 200 and r.json().get("ok"):
            accepted += 1
    return accepted


def drive_match(sc: str, *, max_rounds: int, pucks: list[int]) -> int:
    """Drive up to `max_rounds` rounds via REST, answering each with both
    pucks and force-revealing. Returns the number of rounds actually
    answered (== questions each puck answered this match)."""
    rounds_answered = 0
    for _ in range(max_rounds):
        q = _advance_to_question(sc)
        if not q:
            break
        _answer_question(sc, int(q["id"]), pucks)
        # Close the round so the next load-question advances.
        _post(f"/api/sp/force-reveal/{sc}")
        rounds_answered += 1
        time.sleep(0.2)
    return rounds_answered


def _final_results(sc: str) -> dict:
    r = _get(f"/api/sp/final-results/{sc}")
    if r.status_code != 200:
        return {}
    return r.json()


def _answered_by_puck(fr: dict) -> dict[int, dict]:
    return {int(p["puck_id"]): p for p in (fr.get("players") or [])}


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------

def run() -> int:
    v = Verifier()
    pucks = [HOST_PUCK, JOINER_PUCK]

    sc = pair_via_rest()
    if not sc:
        v.inconclusive("setup", "could not pair/start a match via REST")
        return v.report()
    log(f"session_code={sc}")

    # --- Match A: answer every round to completion. ---
    a_rounds = drive_match(sc, max_rounds=SP_TOTAL_ROUNDS, pucks=pucks)
    log(f"match A answered {a_rounds} rounds")
    if a_rounds < SP_TOTAL_ROUNDS:
        v.inconclusive(
            "match A reached completion",
            f"only answered {a_rounds}/{SP_TOTAL_ROUNDS} rounds — cannot "
            f"establish a full prior match to leak")
        return v.report()

    fr_a = _final_results(sc)
    by_a = _answered_by_puck(fr_a)
    if set(by_a) != set(pucks):
        v.inconclusive(
            "match A final-results has both pucks",
            f"players={list(by_a)} expected={pucks}")
        return v.report()
    a_answered = {pid: by_a[pid]["answered"] for pid in pucks}
    log(f"match A final-results answered={a_answered}")
    # Sanity: a full match means each puck answered SP_TOTAL_ROUNDS.
    if not all(a_answered[pid] == SP_TOTAL_ROUNDS for pid in pucks):
        v.inconclusive(
            "match A answered == total_rounds per puck",
            f"answered={a_answered} (expected {SP_TOTAL_ROUNDS} each) — "
            f"baseline not as designed")
        return v.report()

    # --- Play-Again: reset reuses the SAME session_code/session row. ---
    r_reset = _post(f"/api/sp/reset/{sc}")
    if r_reset.status_code != 200 or not r_reset.json().get("ok"):
        v.inconclusive("sp_reset accepted", f"status={r_reset.status_code}")
        return v.report()
    log("sp_reset OK — Play-Again armed")

    # --- Match B: answer only K (< total) rounds. ---
    K = 3
    b_rounds = drive_match(sc, max_rounds=K, pucks=pucks)
    log(f"match B answered {b_rounds} rounds (target K={K})")
    if b_rounds < 1:
        v.inconclusive(
            "match B answered >=1 round",
            "could not answer any question after reset — cannot exercise leak")
        return v.report()

    fr_b = _final_results(sc)
    by_b = _answered_by_puck(fr_b)
    if set(by_b) != set(pucks):
        v.inconclusive(
            "match B final-results has both pucks",
            f"players={list(by_b)} expected={pucks}")
        return v.report()
    b_answered = {pid: by_b[pid]["answered"] for pid in pucks}
    b_total = {pid: by_b[pid]["total"] for pid in pucks}
    log(f"match B final-results answered={b_answered} total={b_total}")

    total_rounds = fr_b.get("total_rounds", SP_TOTAL_ROUNDS)

    # ---- DECISIVE ASSERTION ----------------------------------------------
    # After Play-Again the final-results must aggregate ONLY the replayed
    # match. Each puck answered exactly b_rounds questions in match B, so the
    # reported `answered` must equal b_rounds and must never exceed
    # total_rounds. On the current build sp_reset leaves match-A's
    # trivia_answers rows in place, so final-results SUMs A+B:
    #   answered ≈ SP_TOTAL_ROUNDS + b_rounds  (> total_rounds, doubled).
    only_b = all(b_answered[pid] == b_rounds for pid in pucks)
    within_total = all(b_answered[pid] <= total_rounds for pid in pucks)
    leaked = {pid: b_answered[pid] for pid in pucks
              if b_answered[pid] != b_rounds}

    v.check(
        "play-again-clears-prior-answers",
        only_b and within_total,
        f"after reset+replay: answered={b_answered} (expected "
        f"{b_rounds} each), total_rounds={total_rounds}; "
        f"prior match A answered={a_answered}. "
        + (f"LEAK: pucks {leaked} include prior-match rows."
           if leaked else "clean — only match-B rows counted."))

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
