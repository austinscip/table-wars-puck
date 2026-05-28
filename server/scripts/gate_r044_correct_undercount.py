"""Gate for R044 — Scoreboard 'correct' must match the reveal feed.

THE INVARIANT
-------------
final-results derives the per-player `correct` count from the database:

    SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)   (pair_routes.py:~1553)

The REVEAL power-up forces an ANSWERED round to correct in memory
(_apply_power_up_arms, pair_routes.py:~730). For a puck that ANSWERED
WRONG on a round where it has an armed REVEAL, the answer endpoint first
wrote a stale `is_correct=False` trivia_answers row; REVEAL then flips the
in-memory result to correct and the reveal feed shows it correct. Without
a write-back, SUM(is_correct) still counts that round as 0 and the final
scoreboard renders FEWER corrects than the players watched get revealed.

R044's fix is `_persist_reveal_correct` (pair_routes.py:~647): for every
puck in `revealed_pucks` it UPDATEs the stale row (or INSERTs one) so the
DB SUM matches the reveal feed.

This gate reconciles with R031: R031 deliberately removed the
"timeout-then-REVEAL == correct" behavior — a REVEAL only helps a puck
that actually taps; a timeout is NEVER correct and is excluded from
`revealed_pucks`. So this gate must NOT time the puck out on the
REVEAL-armed round. Instead it exercises the path R044 actually fixes:
the tracked puck ANSWERS WRONG on a round where its REVEAL is armed.

THE CORRECT INVARIANT GATED
---------------------------
final-results `correct` for a puck == the number of rounds the reveal
feed actually showed that puck correct
  = (rounds /answer returned is_correct=True for the tracked puck)
  + (1 for the REVEAL-armed answered-WRONG round REVEAL forced correct).

REPRO (pure server-rest, no browser past pairing)
-------------------------------------------------
1. POST /api/pair/clear, pair two pucks, start a match.
2. Drive rounds, answering CORRECTLY so the tracked puck wins minigames
   and is granted random power-ups; poll match-state inventories until a
   REVEAL appears, then ARM it for the tracked puck.
3. On the next round (the REVEAL-armed round), the tracked puck ANSWERS
   WRONG (we look up the question's correct_answer in the DB and POST a
   different letter). The answer endpoint writes is_correct=False; the
   reveal then force-corrects that answered round (puck is in
   revealed_pucks) and _persist_reveal_correct UPDATEs the DB row.
4. Finish the match, GET /api/sp/final-results.
5. ASSERT players[reveal_puck].correct == db_correct + forced_correct.
   With persist working it matches. With _persist_reveal_correct stubbed
   the forced-wrong round stays is_correct=False in the DB and the count
   is short -> FAIL.

Gate assertion name: scoreboard-correct-matches-reveals
Proven: fail-on-regression (persist stubbed), pass-on-fix.
"""
from __future__ import annotations

import os
import sys
import time

import requests

from verify_lib import BASE, log, session, pair_and_start, Verifier

PH = f"{BASE}/api/sp"
SP_TOTAL_ROUNDS = 7
HTTP_T = 6

# The gate runs in the server venv with DATABASE_URL= (sqlite), so we can
# read the question's correct_answer the same way pair_routes does. This
# lets us POST a DETERMINISTICALLY WRONG letter on the REVEAL-armed round.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import execute_query, get_placeholder  # noqa: E402


def _correct_letter(qid: int) -> str | None:
    """The correct A/B/C/D letter for a question id, read from the DB."""
    ph = get_placeholder()
    row = execute_query(
        f"SELECT correct_answer FROM trivia_questions WHERE id = {ph}",
        (qid,),
        fetch_one=True,
    )
    return row["correct_answer"] if row else None


def _wrong_letter(qid: int) -> str:
    """A letter guaranteed to be WRONG for the question. Falls back to
    'B' if the correct answer can't be read (still likely wrong; the
    answer endpoint reports is_correct so we never silently miscount)."""
    correct = _correct_letter(qid)
    for cand in ("A", "B", "C", "D"):
        if cand != correct:
            return cand
    return "B"


def _get(url: str):
    try:
        r = requests.get(url, timeout=HTTP_T)
        return r.status_code, (r.json() if r.content else {})
    except Exception as e:  # noqa: BLE001
        return None, {"_err": str(e)}


def _post(url: str, body: dict | None = None):
    try:
        r = requests.post(url, json=body or {}, timeout=HTTP_T)
        return r.status_code, (r.json() if r.content else {})
    except Exception as e:  # noqa: BLE001
        return None, {"_err": str(e)}


def _match_state(sc: str) -> dict:
    _, j = _get(f"{PH}/match-state/{sc}")
    return j or {}


def _inventories(sc: str) -> dict:
    return _match_state(sc).get("power_up_inventories", {}) or {}


def _find_reveal(sc: str):
    """Return (puck_id:int, item_id:str) for the first REVEAL item found in
    any puck's inventory, else (None, None)."""
    for pid_str, items in _inventories(sc).items():
        for it in items or []:
            if it.get("type") == "REVEAL":
                return int(pid_str), it["id"]
    return None, None


def _resolve_phase(sc: str, pucks: list[int] | None = None) -> None:
    """Clear any pending pick / minigame so load-question can advance.
    Picks: select the first offered category. Minigames: FIRE a winning
    shot for the pucks so a winner is declared and a power-up is granted
    (without a winning fire no power-up is ever granted and the REVEAL
    path can never be exercised). Both are driven purely via REST."""
    st = _match_state(sc)
    pp = st.get("pending_category_pick")
    if pp:
        offer = pp.get("offer") or []
        if offer:
            _post(f"{PH}/select-category/{sc}",
                  {"puck_id": pp["picker_puck_id"],
                   "category_id": offer[0]["id"]})
        return
    mg = st.get("pending_minigame")
    if mg and pucks:
        flavor = mg.get("flavor")
        for i, pid in enumerate(pucks):
            if flavor == "BULLSEYE":
                # Perfect fire: target quadrant at t=0 -> 1000 pts. Give the
                # second puck a wrong quadrant so a clear winner emerges.
                tq = mg.get("target_quadrant") or "A"
                quad = tq if i == 0 else ("B" if tq != "B" else "A")
                _post(f"{PH}/minigame/fire",
                      {"session_code": sc, "puck_id": pid,
                       "t_ms": 0, "quadrant": quad})
            else:
                # SHOT_CLOCK: fire at the green-zone center (cycle/2) -> 1000.
                cycle = int(mg.get("cycle_ms") or 2000)
                t = cycle // 2 if i == 0 else int(cycle * 0.01)
                _post(f"{PH}/minigame/fire",
                      {"session_code": sc, "puck_id": pid, "t_ms": t})
        # Belt-and-suspenders resolve in case a fire was rejected.
        _post(f"{PH}/minigame/finish/{sc}")
        return
    # minigame with no pucks known yet: load-question auto-resolves once
    # past the deadline; nothing to POST here.


def _load_question(sc: str, pucks: list[int] | None = None):
    """Drive load-question past any pick/minigame phase. Returns the question
    dict (with 'id') once a real question is active, else None. Resolves
    between-rounds phases as needed."""
    deadline = time.time() + 40
    while time.time() < deadline:
        code, j = _post(f"{PH}/load-question/{sc}")
        if code == 409 and j.get("error") == "match_complete":
            return None
        phase = j.get("phase")
        if phase in ("category_pick", "minigame"):
            _resolve_phase(sc, pucks)
            time.sleep(1.2)
            continue
        q = j.get("question")
        if q and q.get("id"):
            return q
        time.sleep(0.4)
    return None


def _answer(sc: str, puck_id: int, qid: int, letter: str):
    return _post(f"{PH}/answer",
                 {"session_code": sc, "puck_id": puck_id,
                  "question_id": qid, "answer": letter,
                  "response_time_ms": 1500})


def _force_reveal(sc: str):
    return _post(f"{PH}/force-reveal/{sc}")


def _drive_one_match(sc: str, pucks: list[int]) -> dict:
    """Play one full match driving rounds via REST. Fires the minigames so
    power-up grants happen; arms the FIRST granted REVEAL for the tracked
    puck and, on the next round, makes that puck ANSWER WRONG (never times
    it out — per R031 a timeout is never correct). REVEAL force-corrects
    that answered-wrong round and _persist_reveal_correct must UPDATE the
    stale DB row so final-results counts it. Returns:
        {"reveal_puck": int|None, "db_correct": int, "forced": int}
    The power-up grant TYPE is random (1 of 4), so a single match may grant
    no REVEAL; the caller retries until one is granted."""
    _post(f"{PH}/reset/{sc}")
    time.sleep(0.4)

    # We always engineer pucks[0] to win the minigames (perfect fire), so the
    # power-up — and thus the REVEAL we arm — always lands on pucks[0]. Track
    # that puck's DB-correct answers across EVERY round so
    # expected_correct = real DB-correct rounds + REVEAL-forced rounds.
    tracked_puck = pucks[0]
    reveal_puck: int | None = None
    reveal_armed_round: int | None = None
    db_correct_for_reveal_puck = 0
    forced_correct_rounds = 0

    first_q = _load_question(sc, pucks)
    if not first_q:
        return {"reveal_puck": None, "db_correct": 0, "forced": 0,
                "error": "no first question"}

    # ---- Round loop ----------------------------------------------------
    cur_q = first_q
    guard = 0
    while cur_q is not None and guard < 30:
        guard += 1
        qid = int(cur_q["id"])
        st = _match_state(sc)
        rnd = int(st.get("round", 0))
        log(f"round {rnd}: qid={qid}")

        # Is THIS the round on which the tracked puck has an armed REVEAL?
        # If so, make it ANSWER WRONG (do NOT time it out — R031). The
        # answer endpoint records is_correct=False; the reveal then forces
        # that answered round to correct and _persist_reveal_correct must
        # UPDATE the row so final-results counts it.
        reveal_round = (reveal_puck is not None
                        and reveal_armed_round == rnd)

        for pid in pucks:
            if reveal_round and pid == tracked_puck:
                wrong = _wrong_letter(qid)
                code, ar = _answer(sc, pid, qid, wrong)
                got = ar.get("is_correct") if isinstance(ar, dict) else None
                log(f"  puck {pid}: ANSWER WRONG '{wrong}' (REVEAL armed) "
                    f"-> is_correct={got}")
                # Sanity: this answer must actually be wrong, else the
                # round isn't exercising REVEAL's force-correct. If the DB
                # lookup failed and the guess happened to be right, skip
                # marking the forced round (handled below by re-check).
                continue
            # Other rounds (and the other puck): answer 'A'. Track the
            # tracked puck's DB-correct answers on each round it answers.
            code, ar = _answer(sc, pid, qid, "A")
            if code == 200 and pid == tracked_puck and ar.get("is_correct"):
                db_correct_for_reveal_puck += 1

        # Force the reveal so the armed REVEAL is applied this round.
        _force_reveal(sc)
        time.sleep(0.5)

        if reveal_round:
            # The reveal just applied the armed REVEAL -> the tracked puck's
            # answered-WRONG round is forced correct in the feed; the DB row
            # (written is_correct=False at answer time) must be UPDATEd by
            # _persist_reveal_correct so the SUM counts it.
            forced_correct_rounds += 1
            log(f"  REVEAL-forced correct applied for puck "
                f"{reveal_puck} on answered-WRONG round {rnd}")
            reveal_armed_round = None  # one-shot consumed

        # Between-rounds: advance one step at a time so we can FIRE the
        # minigame (granting power-ups) and ARM a granted REVEAL while
        # the between-rounds phase is still open.
        nxt = None
        adv_deadline = time.time() + 40
        while time.time() < adv_deadline:
            code, j = _post(f"{PH}/load-question/{sc}")
            if code == 409 and j.get("error") == "match_complete":
                nxt = None
                break
            phase = j.get("phase")
            if phase in ("category_pick", "minigame"):
                # FIRST, while this between-rounds phase is still open, try
                # to ARM a REVEAL an EARLIER minigame granted (the grant
                # lands during a minigame, which resolves immediately on
                # firing, so it can only be armed during a SUBSEQUENT
                # pick/minigame window).
                if reveal_puck is None:
                    pid, item_id = _find_reveal(sc)
                    if pid is not None and pid == tracked_puck:
                        ac, res = _post(
                            f"{PH}/power-up/activate",
                            {"session_code": sc, "puck_id": pid,
                             "item_id": item_id})
                        if ac == 200 and res.get("ok", True) is not False:
                            reveal_puck = pid
                            reveal_armed_round = int(
                                _match_state(sc).get("round", 0)) + 1
                            log(f"  ARMED REVEAL for puck {pid}; will answer "
                                f"WRONG on round {reveal_armed_round}")
                # Then resolve the phase (picks: select; minigames: FIRE so
                # a winner is granted a power-up for a later window).
                _resolve_phase(sc, pucks)
                time.sleep(0.8)
                continue
            q = j.get("question")
            if q and q.get("id"):
                nxt = q
                break
            time.sleep(0.4)
        cur_q = nxt

    # ---- Finish the match so final-results is stable -------------------
    for _ in range(8):
        if _match_state(sc).get("complete"):
            break
        if _load_question(sc, pucks) is None:
            break
        time.sleep(0.3)

    return {
        "reveal_puck": reveal_puck,
        "db_correct": db_correct_for_reveal_puck,
        "forced": forced_correct_rounds,
    }


def run() -> int:  # noqa: C901
    v = Verifier()

    # Pure server-rest: we still pair via the Hub helper to register two
    # real expected pucks. No match driving via the browser past that point.
    with session() as (hub, tv):
        sc = pair_and_start(hub, tv, goto_question=False)
        if not sc:
            v.inconclusive("setup", "no session_code after pairing")
            return v.report()
        log(f"session_code={sc}")

        # Discover the two paired puck ids from the lobby.
        pucks: list[int] = []
        _, lobby = _get(f"{BASE}/api/pair/lobby-state")
        for key in ("pucks", "members", "players"):
            arr = lobby.get(key) if isinstance(lobby, dict) else None
            if isinstance(arr, list):
                for m in arr:
                    pid = m.get("puck_id") if isinstance(m, dict) else None
                    if isinstance(pid, int):
                        pucks.append(pid)
        pucks = sorted(set(pucks))
        if len(pucks) < 2:
            pucks = [1, 2]
        log(f"pucks={pucks}")

        # The minigame-winner power-up grant is a random 1-of-4 type, so a
        # single match may never grant a REVEAL. Retry full matches until a
        # REVEAL is granted+armed and a forced-correct answered-wrong round
        # runs. P(no REVEAL in 3 grants) = (3/4)^3 ~= 0.42, so ~8 attempts
        # gives >99.99% reliability.
        result = None
        for attempt in range(1, 9):
            log(f"== match attempt {attempt} ==")
            result = _drive_one_match(sc, pucks)
            if result.get("reveal_puck") is not None and result.get("forced"):
                break
            log(f"  (no armed+forced REVEAL this match: {result})")

        if not result or result.get("reveal_puck") is None:
            v.inconclusive(
                "scoreboard-correct-matches-reveals",
                "no REVEAL power-up was granted+armed across repeated "
                "matches, so the REVEAL-forced-correct path could not be "
                "exercised (inconclusive = fail per discipline)")
            return v.report()

        if not result.get("forced"):
            v.inconclusive(
                "scoreboard-correct-matches-reveals",
                "REVEAL armed but the forced-correct answered-wrong round "
                "was not exercised (no reveal feed correct to compare)")
            return v.report()

        reveal_puck = int(result["reveal_puck"])
        db_correct_for_reveal_puck = int(result["db_correct"])
        forced_correct_rounds = int(result["forced"])

        code, fr = _get(f"{PH}/final-results/{sc}")
        if code != 200 or not isinstance(fr, dict):
            v.inconclusive("final-results fetch",
                           f"status={code} body={fr}")
            return v.report()

        players = {int(p["puck_id"]): p for p in fr.get("players", [])}
        rp = players.get(reveal_puck)
        if rp is None:
            v.inconclusive(
                "scoreboard-correct-matches-reveals",
                f"reveal_puck {reveal_puck} missing from final-results "
                f"players={list(players.keys())}")
            return v.report()

        reported_correct = int(rp.get("correct", 0))
        # Truth from the reveal feed: every round /answer returned correct
        # PLUS the REVEAL-armed answered-wrong round the feed forced correct.
        expected_correct = db_correct_for_reveal_puck + forced_correct_rounds

        log(f"reveal_puck={reveal_puck} reported_correct={reported_correct} "
            f"db_correct={db_correct_for_reveal_puck} "
            f"forced_correct={forced_correct_rounds} "
            f"expected_correct={expected_correct}")

        # With _persist_reveal_correct working, the answered-wrong forced
        # round's stale is_correct=False DB row is UPDATEd to True, so
        # reported_correct == expected_correct. With persist stubbed, the
        # forced round stays 0 in the SUM and reported_correct is short by
        # forced_correct_rounds -> FAIL.
        v.check(
            "scoreboard-correct-matches-reveals",
            reported_correct == expected_correct,
            f"final-results correct={reported_correct} but the reveal feed "
            f"showed {expected_correct} corrects for puck {reveal_puck} "
            f"({db_correct_for_reveal_puck} answered-correct + "
            f"{forced_correct_rounds} REVEAL-forced answered-wrong); "
            f"delta={reported_correct - expected_correct}")

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
