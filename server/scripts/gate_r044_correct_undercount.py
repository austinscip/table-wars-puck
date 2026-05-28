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
    dict (with 'id' and 'answers') once a real question is active, else None.
    Resolves between-rounds phases as needed."""
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
    power-up grants happen; arms the FIRST granted REVEAL and times its puck
    out on the next round so the REVEAL forces an in-memory correct with no
    matching DB row. Returns a dict describing what was exercised:
        {"reveal_puck": int|None, "db_correct": int, "forced": int}
    The power-up grant TYPE is random (1 of 4), so a single match may grant
    no REVEAL; the caller retries until one is granted."""
    _post(f"{PH}/reset/{sc}")
    time.sleep(0.4)

    # We always engineer pucks[0] to win the minigames (perfect fire), so the
    # power-up — and thus the REVEAL we arm — always lands on pucks[0]. Track
    # that puck's DB-correct answers across EVERY round (not just after the
    # REVEAL is armed) so expected_correct = real DB-correct + forced rounds.
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
    if True:
        while cur_q is not None and guard < 30:
            guard += 1
            qid = int(cur_q["id"])
            st = _match_state(sc)
            rnd = int(st.get("round", 0))
            log(f"round {rnd}: qid={qid}")

            # If this is the round AFTER we armed REVEAL on the tracked puck,
            # deliberately let it TIME OUT (skip its answer) so the bug
            # surfaces: REVEAL forces is_correct=True in memory but no DB row
            # exists.
            timeout_target = (reveal_puck is not None
                              and reveal_armed_round == rnd)

            for pid in pucks:
                if timeout_target and pid == tracked_puck:
                    log(f"  puck {pid}: TIMING OUT (REVEAL armed) — no answer")
                    continue
                # Answer 'A'. Track the tracked puck's DB-correct answers on
                # every round it actually answers (the only rounds that write
                # a DB row); the timed-out forced round writes none on the
                # buggy build.
                code, ar = _answer(sc, pid, qid, "A")
                if code == 200 and pid == tracked_puck and ar.get("is_correct"):
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

            # Between-rounds: advance one step at a time so we can FIRE the
            # minigame (granting power-ups) and ARM a granted REVEAL while
            # the between-rounds phase is still open. Each load-question
            # either opens a phase, returns a question, or completes.
            nxt = None
            adv_deadline = time.time() + 40
            while time.time() < adv_deadline:
                code, j = _post(f"{PH}/load-question/{sc}")
                if code == 409 and j.get("error") == "match_complete":
                    nxt = None
                    break
                phase = j.get("phase")
                if phase in ("category_pick", "minigame"):
                    # FIRST, while this between-rounds phase is still open,
                    # try to ARM a REVEAL that an EARLIER minigame granted
                    # (the grant lands during a minigame, which resolves
                    # immediately on firing, so it can only be armed during a
                    # SUBSEQUENT pick/minigame window).
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
                                log(f"  ARMED REVEAL for puck {pid}; will "
                                    f"time out on round {reveal_armed_round}")
                    # Then resolve the phase (picks: select; minigames: FIRE
                    # so a winner is granted a power-up for a later window).
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
    # real expected pucks (load_expected_pucks reads the DB rows pairing
    # creates). No match driving via the browser past that point.
    with session() as (hub, tv):
        sc = pair_and_start(hub, tv, goto_question=False)
        if not sc:
            v.inconclusive("setup", "no session_code after pairing")
            return v.report()
        log(f"session_code={sc}")

        # Discover the two paired puck ids from the lobby (pairing creates
        # them; ids are whatever the DB assigned, conventionally 1 and 2).
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
        # REVEAL is granted+armed and a forced-correct timeout round runs.
        # P(no REVEAL in 3 grants) = (3/4)^3 ~= 0.42, so ~8 attempts gives
        # >99.99% reliability.
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
                "REVEAL armed but the forced-correct timeout round was not "
                "exercised (no reveal feed correct to compare)")
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
