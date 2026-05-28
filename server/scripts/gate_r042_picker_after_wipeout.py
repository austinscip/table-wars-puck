"""Gate for R042 — who-picks-next must NOT reuse a stale non-zero winner
after an all-zero (wipeout) round.

THE BUG
-------
pair_routes._maybe_emit_reveal only updates last_round_winner_puck_id
when the round's best score is positive:

    if best_pid is not None and best_pts > 0:        # line 1549-1550
        state["last_round_winner_puck_id"] = best_pid

It is NEVER reset on a wipeout (every puck wrong or timed out — common in
a bar). _build_pick_offer (lines 737-744) only falls back to the lowest-
expected puck when last_round_winner_puck_id is FALSY:

    if next_round == 1 or not state.get("last_round_winner_puck_id"):
        picker = expected[0] ...
    else:
        picker = int(state["last_round_winner_puck_id"])

So once any prior round had a positive scorer, a later all-zero round
leaves the SAME stale winner as the next picker instead of the documented
"fall back to lowest expected" reset. The in-code comment (line 1535)
and the implementation disagree.

WHAT THIS GATE DOES (pure server REST against :5002)
----------------------------------------------------
Drives a 2-puck match entirely through the REST API (no browser):

  Round 1 (pick phase, no prior winner -> picker=lowest expected=1):
    puck 2 answers CORRECTLY, puck 1 times out. Round 1 winner = 2,
    so last_round_winner_puck_id := 2.
  Round 2 (minigame phase, then a QUESTION round):
    NEITHER puck answers -> force-reveal marks both TIMEOUT (0 pts).
    This is the WIPEOUT round. Minigame resolution does NOT touch
    last_round_winner_puck_id, so the only winner-tracking signal for
    the round-3 pick is this wipeout.
  Round 3 (pick phase): GET match-state.pending_category_pick.picker_puck_id.

DECISIVE ASSERTION
------------------
After a wipeout, the next picker must reflect the wipeout policy
(lowest expected = puck 1), NOT the stale round-1 winner (puck 2).

  - CURRENT build: picker == 2 (stale winner) -> FAIL.
  - FIXED build  : picker == 1 (lowest expected reset) -> PASS.

Gate assertion name: wipeout-round-resets-picker
Proven: fail-on-current expected; pass-on-fix.
"""
from __future__ import annotations

import sqlite3
import sys
import time

import requests

from verify_lib import BASE, log, Verifier

# Absolute path to the dev SQLite DB so we can read the active question's
# correct_answer (needed to deterministically make puck 2 WIN round 1).
# Read-only; we never write it. This does NOT touch any narration MP3.
_DB_PATH = "/Users/austinscipione/table-wars-puck-sandbox/server/tablewars.db"

HOST_PUCK = 1
JOINER_PUCK = 2
LETTERS = ("A", "B", "C", "D")


def _post(path: str, body: dict | None = None):
    return requests.post(f"{BASE}{path}", json=body or {}, timeout=8)


def _get(path: str):
    return requests.get(f"{BASE}{path}", timeout=8)


def _match_state(sc: str) -> dict:
    try:
        return _get(f"/api/sp/match-state/{sc}").json()
    except Exception:
        return {}


def _correct_answer_for(qid: int) -> str | None:
    """Read the correct_answer column for a question id straight from the
    dev DB. Read-only single-row SELECT."""
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT correct_answer FROM trivia_questions WHERE id = ?",
            (int(qid),),
        ).fetchone()
        conn.close()
        return row["correct_answer"] if row else None
    except Exception as e:
        log(f"  DB read failed for qid={qid}: {e}")
        return None


def _pair_two_pucks(v: Verifier) -> str | None:
    """Pair host(1) + joiner(2) and start the match — all via REST.
    Returns session_code or None."""
    _post("/api/pair/clear")
    time.sleep(0.2)
    r_host = _post("/api/pair/request", {"puck_id": HOST_PUCK})
    if r_host.status_code != 200:
        v.inconclusive("pair-host", f"request host -> {r_host.status_code}")
        return None
    code = r_host.json().get("pair_code")
    # Joiner is added to the lobby on /request (no dial step for joiners).
    r_join = _post("/api/pair/request", {"puck_id": JOINER_PUCK})
    if r_join.status_code != 200:
        v.inconclusive("pair-joiner", f"request joiner -> {r_join.status_code}")
        return None
    # Host confirms its dial to register itself as a player.
    r_conf = _post("/api/pair/confirm", {"puck_id": HOST_PUCK, "code": code})
    if r_conf.status_code != 200:
        v.inconclusive("pair-confirm", f"confirm host -> {r_conf.status_code}")
        return None
    r_start = _post("/api/pair/start", {"puck_id": HOST_PUCK})
    if r_start.status_code != 200:
        v.inconclusive("pair-start", f"start -> {r_start.status_code} {r_start.text[:120]}")
        return None
    sc = r_start.json().get("session_code")
    return sc


def _resolve_pick_phase(sc: str, payload: dict) -> bool:
    """Lock in the first offered category as the designated picker.
    Returns True on success."""
    picker = payload.get("picker_puck_id")
    offer = payload.get("offer") or []
    if picker is None or not offer:
        return False
    r = _post(f"/api/sp/select-category/{sc}",
              {"puck_id": int(picker), "category_id": int(offer[0]["id"])})
    return r.status_code == 200 and r.json().get("ok") is True


def _advance_to_question(sc: str, v: Verifier, max_steps: int = 12):
    """Repeatedly POST load-question, auto-resolving any pick / minigame
    phase, until a real `question` payload comes back. Returns the
    question dict (with id) or None."""
    for _ in range(max_steps):
        r = _post(f"/api/sp/load-question/{sc}")
        if r.status_code == 409:
            # match_complete or similar — surface to caller.
            return None
        if r.status_code != 200:
            log(f"  load-question -> HTTP {r.status_code} {r.text[:120]}")
            return None
        data = r.json()
        phase = data.get("phase")
        if phase == "category_pick":
            if not _resolve_pick_phase(sc, data):
                return None
            time.sleep(0.2)
            continue
        if phase == "minigame":
            # Force the minigame to resolve immediately (no fires), then
            # loop back to load-question to advance into the question.
            _post(f"/api/sp/minigame/finish/{sc}")
            time.sleep(0.2)
            continue
        q = data.get("question")
        if q and q.get("id"):
            return q
        time.sleep(0.2)
    return None


def run() -> int:
    v = Verifier()

    sc = _pair_two_pucks(v)
    if not sc:
        return v.report()
    log(f"paired host=1 joiner=2 -> session_code={sc}")

    ms = _match_state(sc)
    expected_note = (
        f"questions_asked={ms.get('questions_asked')} round={ms.get('round')}"
    )
    log(f"initial match-state: exists={ms.get('exists')} {expected_note}")

    # ------------------------------------------------------------------
    # ROUND 1 — make puck 2 the winner (puck 1 times out, puck 2 correct).
    # ------------------------------------------------------------------
    q1 = _advance_to_question(sc, v)
    if not q1:
        v.inconclusive("setup-round1-question",
                       "could not drive to round-1 question")
        return v.report()
    qid1 = int(q1["id"])
    correct1 = _correct_answer_for(qid1)
    if correct1 not in LETTERS:
        v.inconclusive(
            "setup-round1-correct-answer",
            f"could not read correct_answer for qid={qid1} (got {correct1!r}); "
            "cannot guarantee a non-zero round-1 winner")
        return v.report()
    # Start the timer so the answer scores against a real window, then have
    # ONLY puck 2 answer (correctly). Puck 1 stays silent -> 0 pts.
    _post(f"/api/sp/start-timer/{sc}")
    r_ans = _post("/api/sp/answer", {
        "session_code": sc, "puck_id": JOINER_PUCK,
        "question_id": qid1, "answer": correct1, "response_time_ms": 800,
    })
    ans_body = {}
    try:
        ans_body = r_ans.json()
    except Exception:
        pass
    log(f"round1: puck 2 answered '{correct1}' -> HTTP {r_ans.status_code} "
        f"is_correct={ans_body.get('is_correct')} points={ans_body.get('points')}")
    winner_established = bool(ans_body.get("is_correct")) and int(ans_body.get("points") or 0) > 0
    if not winner_established:
        v.inconclusive(
            "setup-round1-winner",
            f"puck 2 did not score positive on round 1 "
            f"(is_correct={ans_body.get('is_correct')} points={ans_body.get('points')}); "
            "cannot establish the stale non-zero winner the bug needs")
        return v.report()
    # Force the reveal so round 1 closes with puck 2 as the lone scorer.
    _post(f"/api/sp/force-reveal/{sc}")
    time.sleep(0.3)
    log("round1 closed: winner = puck 2 (last_round_winner_puck_id should be 2)")

    # ------------------------------------------------------------------
    # ROUND 2 — minigame phase, then a WIPEOUT question round.
    # Neither puck answers; force-reveal marks both TIMEOUT (0 pts).
    # ------------------------------------------------------------------
    q2 = _advance_to_question(sc, v)
    if not q2:
        v.inconclusive("setup-round2-question",
                       "could not drive to round-2 question")
        return v.report()
    qid2 = int(q2["id"])
    log(f"round2: qid={qid2} — leaving BOTH pucks silent to force a wipeout")
    _post(f"/api/sp/start-timer/{sc}")
    # No answers at all. force=True marks every expected puck TIMEOUT/0.
    r_fr = _post(f"/api/sp/force-reveal/{sc}")
    log(f"round2 force-reveal (wipeout) -> HTTP {r_fr.status_code} {r_fr.text[:100]}")
    time.sleep(0.3)

    # ------------------------------------------------------------------
    # ROUND 3 — pick phase. Its picker is decided by the winner of the
    # round-2 wipeout. Drive load-question until the pending pick appears,
    # then read picker_puck_id from match-state.
    # ------------------------------------------------------------------
    picker = None
    pick_payload = None
    for _ in range(12):
        r = _post(f"/api/sp/load-question/{sc}")
        if r.status_code == 200 and r.json().get("phase") == "category_pick":
            pick_payload = r.json()
            picker = pick_payload.get("picker_puck_id")
            break
        # If load-question slipped past the pick (e.g. auto-resolved), the
        # pending pick is still surfaced by match-state for a moment.
        ms3 = _match_state(sc)
        pp = ms3.get("pending_category_pick")
        if pp:
            pick_payload = pp
            picker = pp.get("picker_puck_id")
            break
        time.sleep(0.25)

    if picker is None:
        v.inconclusive(
            "wipeout-round-resets-picker",
            "could not reach the round-3 category-pick phase to read "
            "picker_puck_id; bug condition not exercised")
        return v.report()

    log(f"round3 pick offer: picker_puck_id={picker} "
        f"offer={[o.get('id') for o in (pick_payload.get('offer') or [])]}")

    # Decisive assertion: after the wipeout, the picker must be the lowest
    # expected puck (1), NOT the stale round-1 winner (2).
    v.check(
        "wipeout-round-resets-picker",
        int(picker) == HOST_PUCK,
        f"round-3 picker_puck_id={picker} (expected {HOST_PUCK}=lowest after "
        f"wipeout; current build leaves stale round-1 winner {JOINER_PUCK} "
        "because _maybe_emit_reveal never resets last_round_winner_puck_id "
        "on a 0-point round)",
    )

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
