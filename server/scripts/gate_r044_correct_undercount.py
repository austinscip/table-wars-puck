"""Gate for R044 — Scoreboard 'correct' under-counts REVEAL-forced corrects.

THE BUG
-------
final-results derives the per-player `correct` count from the database:

    SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)   (pair_routes.py:1399)

But the REVEAL power-up forces ans["is_correct"]=True at reveal time
(pair_routes.py:646) and that post-arm value is NEVER written back to
trivia_answers. Worse, a REVEAL on a TIMED-OUT round has no DB row at all
(record_answer only runs inside /api/sp/answer, never for a puck that
never answered). So a round the reveal feed counted as correct contributes
0 to final-results `correct`, and ScoreboardScreen renders {correct}/7 with
FEWER corrects than the players actually saw revealed.

Same DB-as-source-of-truth root as R029, but it hits the `correct` line
independently of the `total`/`answered` lines.

REPRO (pure server-rest, no browser)
-------------------------------------
1. POST /api/pair/clear, pair two pucks, start a match (real session +
   expected_pucks).
2. Drive rounds, answering CORRECTLY so the puck wins and is granted random
   power-ups; poll /api/sp/match-state inventories every between-rounds
   phase until a REVEAL appears in some puck's inventory.
3. The instant a REVEAL is available, POST /api/sp/power-up/activate to ARM
   it for that puck, then on the NEXT round let that puck TIME OUT (do not
   POST /answer for it) and POST /api/sp/force-reveal.
   -> in-memory: that puck's round is_correct=True (REVEAL), reveal feed
      shows a correct. DB: zero rows for that puck/round.
4. Finish the match, GET /api/sp/final-results.
5. ASSERT players[reveal_puck].correct >= (DB-correct rounds + REVEAL-forced
   rounds we armed). On the current build it is short by the number of
   REVEAL-forced timeout rounds -> FAIL. After the fix (derive correct from
   in-memory per-round reveal results, or UPDATE the row post-arm) it
   matches -> PASS.

Gate assertion name: scoreboard-correct-matches-reveals
Proven: fail-on-current expected; pass-on-fix.
"""
from __future__ import annotations

import sys
import time

import requests

from verify_lib import BASE, log, session, pair_and_start, Verifier

PH = f"{BASE}/api/sp"
SP_TOTAL_ROUNDS = 7
HTTP_T = 6


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


def _between_rounds(sc: str) -> bool:
    st = _match_state(sc)
    return bool(st.get("pending_category_pick") or st.get("pending_minigame"))


def _resolve_phase(sc: str) -> None:
    """Clear any pending pick / minigame so load-question can advance.
    Picks: select the first offered category. Minigames: just let the
    deadline lapse (load-question auto-resolves). Both are driven purely
    via REST."""
    st = _match_state(sc)
    pp = st.get("pending_category_pick")
    if pp:
        offer = pp.get("offer") or []
        if offer:
            _post(f"{PH}/select-category/{sc}",
                  {"puck_id": pp["picker_puck_id"],
                   "category_id": offer[0]["id"]})
        return
    # minigame: load-question auto-resolves once past the deadline; nothing
    # to POST here.


def _load_question(sc: str):
    """Drive load-question past any pick/minigame phase. Returns the question
    dict (with 'id' and 'answers') once a real question is active, else None.
    Resolves between-rounds phases as needed."""
    deadline = time.time() + 40
    while time.time() < deadline:
        code, j = _post(f"{PH}/load-question/{sc}")
        if code == 409 and j.get("error") == "match_complete":
            return None
        phase = j.get("phase")
        if phase in ("category_pick", "minigame"):
            _resolve_phase(sc)
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


def run() -> int:  # noqa: C901
    v = Verifier()

    # Pure server-rest: we still pair via the Hub helper to register two
    # real expected pucks (load_expected_pucks reads the DB rows pairing
    # creates). No match driving via the browser past that point.
    with session() as (hub, tv):
        sc = pair_and_start(hub, tv, goto_question=False)
        if not sc:
            v.inconclusive("setup", "no session_code after pairing")
            return v.report()
        log(f"session_code={sc}")

        # Reset SP state to a clean round-0 match for this session.
        _post(f"{PH}/reset/{sc}")
        time.sleep(0.4)

        st = _match_state(sc)
        # expected_pucks isn't in match-state; infer from inventories later.
        # We know pairing registered pucks 1 and 2 typically; discover the
        # two puck ids from the answer flow instead. Pair helper pairs puck
        # rows 0 and 1 -> puck_ids are whatever the DB assigned. We learn
        # them from the first round's answer responses.
        pucks: list[int] = []

        reveal_puck: int | None = None
        reveal_armed_round: int | None = None
        # Per-puck running tally of how many rounds the REVEAL feed would
        # mark correct for that puck = DB-correct answers + REVEAL-forced
        # rounds. We only need it for reveal_puck.
        db_correct_for_reveal_puck = 0
        forced_correct_rounds = 0

        # We must learn the two puck ids. Probe candidate ids 1..8 by
        # checking which ones the /answer endpoint accepts (it 409s on a
        # wrong question but 400/ok tells us the puck is in the round). We
        # instead derive pucks from expected via a throwaway question.
        first_q = _load_question(sc)
        if not first_q:
            v.inconclusive("first load-question", "no question returned")
            return v.report()

        # Discover puck ids: try answering as ids 1..8; the SP answer
        # endpoint records by puck_id with no membership check, but only
        # expected pucks matter for reveal. Read expected from load-question
        # payload via a fresh state poll is not exposed; instead use the two
        # ids that pairing creates. Pull them from the lobby state.
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
            # Fall back to the conventional 1,2 assignment.
            pucks = [1, 2]
        log(f"pucks={pucks}")

        # ---- Round loop -------------------------------------------------
        cur_q = first_q
        guard = 0
        while cur_q is not None and guard < 30:
            guard += 1
            qid = int(cur_q["id"])
            st = _match_state(sc)
            rnd = int(st.get("round", 0))
            log(f"round {rnd}: qid={qid}")

            # If this is the round AFTER we armed REVEAL on reveal_puck,
            # deliberately let reveal_puck TIME OUT (skip its answer) so the
            # bug surfaces: REVEAL forces is_correct=True in memory but no
            # DB row exists.
            timeout_target = (reveal_puck is not None
                              and reveal_armed_round == rnd)

            for pid in pucks:
                if timeout_target and pid == reveal_puck:
                    log(f"  puck {pid}: TIMING OUT (REVEAL armed) — no answer")
                    continue
                # Answer 'A'. We don't need correctness for non-reveal pucks;
                # for reveal_puck on non-timeout rounds, track DB correctness.
                code, ar = _answer(sc, pid, qid, "A")
                if code == 200 and pid == reveal_puck and ar.get("is_correct"):
                    db_correct_for_reveal_puck += 1

            # Force the reveal (covers the timed-out puck path too).
            _force_reveal(sc)
            time.sleep(0.5)

            if timeout_target:
                # The reveal just applied the armed REVEAL -> in-memory
                # is_correct=True for reveal_puck this round, but no DB row.
                forced_correct_rounds += 1
                log(f"  REVEAL-forced correct applied for puck "
                    f"{reveal_puck} on round {rnd} (no DB row)")
                reveal_armed_round = None  # one-shot consumed

            # Between-rounds: look for a REVEAL we can arm (only if we
            # haven't already set one up).
            # Advance toward the next round; load-question opens the phase.
            nxt = _load_question(sc)
            if reveal_puck is None:
                # After load-question opened a pick/minigame phase OR before
                # it advanced, inventories may hold a REVEAL grant.
                pid, item_id = _find_reveal(sc)
                if pid is not None and _between_rounds(sc):
                    code, res = _post(
                        f"{PH}/power-up/activate",
                        {"session_code": sc, "puck_id": pid,
                         "item_id": item_id})
                    if code == 200 and res.get("ok", True) is not False:
                        reveal_puck = pid
                        # It arms for the NEXT question's reveal.
                        reveal_armed_round = int(
                            _match_state(sc).get("round", 0)) + 1
                        log(f"  ARMED REVEAL for puck {pid}; will time out "
                            f"on round {reveal_armed_round}")
                        # Resolve the phase so the armed round actually loads.
                        nxt = _load_question(sc)
            cur_q = nxt

        # ---- Finish + assert -------------------------------------------
        # Make sure the match completed so final-results is stable.
        for _ in range(8):
            if _match_state(sc).get("complete"):
                break
            if _load_question(sc) is None:
                break
            time.sleep(0.3)

        if reveal_puck is None:
            v.inconclusive(
                "scoreboard-correct-matches-reveals",
                "no REVEAL power-up was ever granted across the match, so "
                "the REVEAL-forced-correct path could not be exercised "
                "(inconclusive = fail per discipline)")
            return v.report()

        if forced_correct_rounds == 0:
            v.inconclusive(
                "scoreboard-correct-matches-reveals",
                "REVEAL armed but the forced-correct timeout round was not "
                "exercised (no reveal feed correct to compare)")
            return v.report()

        code, fr = _get(f"{PH}/final-results/{sc}")
        if code != 200 or not isinstance(fr, dict):
            v.inconclusive("final-results fetch",
                           f"status={code} body={fr}")
            return v.report()

        players = {int(p["puck_id"]): p for p in fr.get("players", [])}
        rp = players.get(int(reveal_puck))
        if rp is None:
            v.inconclusive(
                "scoreboard-correct-matches-reveals",
                f"reveal_puck {reveal_puck} missing from final-results "
                f"players={list(players.keys())}")
            return v.report()

        reported_correct = int(rp.get("correct", 0))
        # Truth from the reveal feed: every DB-correct round + every
        # REVEAL-forced round counts as a correct the players saw.
        expected_correct = db_correct_for_reveal_puck + forced_correct_rounds

        log(f"reveal_puck={reveal_puck} reported_correct={reported_correct} "
            f"db_correct={db_correct_for_reveal_puck} "
            f"forced_correct={forced_correct_rounds} "
            f"expected_correct={expected_correct}")

        # On the buggy build reported_correct == db_correct_for_reveal_puck
        # (the forced rounds contribute 0), which is strictly less than
        # expected. The fix makes reported_correct == expected_correct.
        v.check(
            "scoreboard-correct-matches-reveals",
            reported_correct >= expected_correct,
            f"final-results correct={reported_correct} but the reveal feed "
            f"showed {expected_correct} corrects for puck {reveal_puck} "
            f"({db_correct_for_reveal_puck} DB-correct + "
            f"{forced_correct_rounds} REVEAL-forced); under-count of "
            f"{expected_correct - reported_correct}")

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
