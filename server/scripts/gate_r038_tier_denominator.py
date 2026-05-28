"""Gate for R038 — scoreboard tier denominator must be ROUNDS PLAYED,
not the count of answered DB rows.

The bug (server/pair_routes.py sp_final_results, derive_tier 1407-1417):

    rows = SELECT ... COUNT(*) AS answered ... FROM trivia_answers ...
    def derive_tier(total, answered):
        avg = total / answered          # <-- answered = COUNT(*) DB rows
        ...

The ONLY thing that writes a trivia_answers row is sp_answer (1944,
record_answer), which runs ONLY when a puck POSTs /api/sp/answer. A
round the puck lets TIME OUT never reaches sp_answer — _maybe_emit_reveal
fills an in-memory TIMEOUT entry (1506-1518) but writes NO DB row. A
WRONG answer, by contrast, DOES POST /answer and so inserts a 0-point
row.

Result: two pucks with IDENTICAL real performance get DIFFERENT tiers
purely because of how their non-scoring rounds happened. With 4 correct
of 7 (4 x 1000 = 4000 pts):
  - non-scoring rounds were TIMEOUTS -> answered=4 -> avg 4000/4 = 1000 -> LEGENDARY
  - non-scoring rounds were WRONG    -> answered=7 -> avg 4000/7 ~  571 -> EXPERT
The denominator is non-deterministic w.r.t. what the players actually did.

This gate drives TWO real REST matches (kind: server-rest) to the
scoreboard with identical 4-of-7 correct performance:
  Match A — the 3 non-scoring rounds TIME OUT (never POST /answer;
            resolved with /force-reveal so NO DB row is written).
  Match B — the 3 non-scoring rounds submit a guaranteed-WRONG answer
            (POST /answer -> a 0-point DB row).
Then it GETs /api/sp/final-results for both and asserts the derived
`tier` is EQUAL for the single player across both matches.

Correct answers for the 4 scoring rounds are read directly from the
trivia_questions table (read-only DB query) so the two matches earn the
SAME total points — the ONLY thing differing between them is the DB-row
count of the non-scoring rounds, which is exactly what the bug keys off.

The fix (fixSketch): derive_tier divides by rounds actually played
(avg = total / max(1, total_rounds)). A timeout then counts as a
0-point round identical to a wrong answer, so both matches land on the
SAME tier and this gate flips to PASS.

Decisive assertion name: tier-denominator-is-rounds-played
Proven: fail-on-current expected; pass-on-fix.
"""
from __future__ import annotations

import os
import sys
import time

import requests

# scripts/ lives under the server package dir — make the server modules
# importable so we can read each question's correct answer (read-only).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from verify_lib import BASE, log, Verifier  # noqa: E402

from database import execute_query, get_placeholder  # noqa: E402


HOST_PUCK = 1
TOTAL_ROUNDS = 7
# Round indices (1-based) that earn points in BOTH matches. The other
# rounds (the complement) are the "non-scoring" rounds that differ in
# HOW they fail: timeout (Match A) vs wrong answer (Match B).
SCORING_ROUNDS = {1, 2, 3, 4}
ALL_ROUNDS = set(range(1, TOTAL_ROUNDS + 1))
NON_SCORING_ROUNDS = ALL_ROUNDS - SCORING_ROUNDS  # {5, 6, 7}

# Answer fast so every correct answer lands in the same (top) tier in
# BOTH matches -> identical per-correct points -> identical totals.
FAST_RT_MS = 600

_WRONG_FALLBACK = {"A": "B", "B": "A", "C": "A", "D": "A"}


def _correct_answer_for(question_id: int) -> str | None:
    ph = get_placeholder()
    row = execute_query(
        f"SELECT correct_answer FROM trivia_questions WHERE id = {ph}",
        (question_id,),
        fetch_one=True,
    )
    return row["correct_answer"] if row else None


def _pair_single_host() -> str | None:
    """Pair a single host puck purely over REST and start the match.
    Returns the session_code (real trivia_sessions row) or None."""
    requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)
    r = requests.post(f"{BASE}/api/pair/request",
                      json={"puck_id": HOST_PUCK}, timeout=8).json()
    code = r.get("pair_code")
    if not code:
        return None
    # Host confirms its own dial (joiners are optional; a single-puck
    # lobby is enough to create the session + expected_pucks={host}).
    requests.post(f"{BASE}/api/pair/confirm",
                  json={"puck_id": HOST_PUCK, "code": code}, timeout=8)
    started = requests.post(f"{BASE}/api/pair/start",
                            json={"puck_id": HOST_PUCK}, timeout=8).json()
    return started.get("session_code")


def _load_next_question(sc: str, v: Verifier) -> dict | None:
    """POST /load-question, resolving any category-pick or minigame
    phase, until a real question payload comes back. Returns the
    question dict or None if the match ended / stalled."""
    deadline = time.time() + 30
    while time.time() < deadline:
        resp = requests.post(
            f"{BASE}/api/sp/load-question/{sc}", json={}, timeout=10)
        if resp.status_code == 409:
            # match_complete — no more questions.
            return None
        body = resp.json()
        phase = body.get("phase")
        if phase == "category_pick":
            offer = body.get("offer") or []
            if not offer:
                # No offer to lock — let the deadline auto-default.
                time.sleep(0.3)
                continue
            requests.post(
                f"{BASE}/api/sp/select-category/{sc}",
                json={"puck_id": body.get("picker_puck_id", HOST_PUCK),
                      "category_id": int(offer[0]["id"])},
                timeout=8)
            continue
        if phase == "minigame":
            requests.post(
                f"{BASE}/api/sp/minigame/finish/{sc}", json={}, timeout=8)
            continue
        if body.get("question"):
            return body
        # Unknown shape — brief wait then retry.
        time.sleep(0.3)
    return None


def _drive_match(sc: str, *, non_scoring_mode: str, v: Verifier) -> bool:
    """Drive all 7 rounds for session `sc`.

    SCORING_ROUNDS  -> answer the CORRECT letter, fast (earns points).
    NON_SCORING_ROUNDS:
      non_scoring_mode == 'timeout' -> never POST /answer; /force-reveal
                                       (NO trivia_answers row written).
      non_scoring_mode == 'wrong'   -> POST /answer with a guaranteed
                                       wrong letter (0-point DB row).

    Returns True if all 7 rounds were exercised as intended.
    """
    for rnd in range(1, TOTAL_ROUNDS + 1):
        body = _load_next_question(sc, v)
        if not body or not body.get("question"):
            v.inconclusive(
                f"match[{non_scoring_mode}] reach round {rnd}",
                f"no question payload (body={body})")
            return False
        q = body["question"]
        qid = int(q["id"])
        # Start the countdown so the server has a started_at to measure
        # response time against (mirrors the TV handoff).
        requests.post(f"{BASE}/api/sp/start-timer/{sc}", json={}, timeout=8)

        if rnd in SCORING_ROUNDS:
            correct = _correct_answer_for(qid)
            if correct not in ("A", "B", "C", "D"):
                v.inconclusive(
                    f"match[{non_scoring_mode}] round {rnd} correct-answer lookup",
                    f"qid={qid} correct={correct!r}")
                return False
            ans = requests.post(
                f"{BASE}/api/sp/answer",
                json={"session_code": sc, "puck_id": HOST_PUCK,
                      "question_id": qid, "answer": correct,
                      "response_time_ms": FAST_RT_MS},
                timeout=8).json()
            if not ans.get("is_correct"):
                v.inconclusive(
                    f"match[{non_scoring_mode}] round {rnd} expected-correct answer",
                    f"qid={qid} server says is_correct={ans.get('is_correct')} "
                    f"answer={correct!r}")
                return False
            # Reveal fires automatically once the lone expected puck answered.
        else:
            if non_scoring_mode == "wrong":
                correct = _correct_answer_for(qid)
                wrong = _WRONG_FALLBACK.get(correct or "A", "B")
                ans = requests.post(
                    f"{BASE}/api/sp/answer",
                    json={"session_code": sc, "puck_id": HOST_PUCK,
                          "question_id": qid, "answer": wrong,
                          "response_time_ms": FAST_RT_MS},
                    timeout=8).json()
                if ans.get("is_correct"):
                    v.inconclusive(
                        f"match[wrong] round {rnd} expected-WRONG answer",
                        f"qid={qid} answer {wrong!r} scored correct")
                    return False
            elif non_scoring_mode == "timeout":
                # Deliberately do NOT POST /answer. Force the reveal so
                # the round closes with an in-memory TIMEOUT entry and
                # NO trivia_answers row.
                fr = requests.post(
                    f"{BASE}/api/sp/force-reveal/{sc}", json={}, timeout=8).json()
                if not fr.get("ok"):
                    v.inconclusive(
                        f"match[timeout] round {rnd} force-reveal",
                        f"qid={qid} resp={fr}")
                    return False
            else:
                v.inconclusive("driver config",
                               f"bad non_scoring_mode={non_scoring_mode!r}")
                return False
        # Small settle so the reveal/round transition lands before the
        # next load-question advances the round counter.
        time.sleep(0.4)
    return True


def _final_player(sc: str) -> dict | None:
    fr = requests.get(f"{BASE}/api/sp/final-results/{sc}", timeout=8).json()
    players = fr.get("players") or []
    for p in players:
        if int(p.get("puck_id", -1)) == HOST_PUCK:
            return p
    return players[0] if players else None


def run() -> int:
    v = Verifier()

    # ---------------- Match A: non-scoring rounds TIME OUT ----------------
    sc_a = _pair_single_host()
    if not sc_a:
        v.inconclusive("setup match A", "no session_code from /api/pair/start")
        return v.report()
    log(f"Match A session_code={sc_a} — non-scoring rounds TIME OUT "
        f"(no DB row): rounds {sorted(NON_SCORING_ROUNDS)}")
    if not _drive_match(sc_a, non_scoring_mode="timeout", v=v):
        return v.report()
    pa = _final_player(sc_a)

    # ---------------- Match B: non-scoring rounds WRONG ----------------
    sc_b = _pair_single_host()
    if not sc_b:
        v.inconclusive("setup match B", "no session_code from /api/pair/start")
        return v.report()
    log(f"Match B session_code={sc_b} — non-scoring rounds WRONG "
        f"(0-point DB row): rounds {sorted(NON_SCORING_ROUNDS)}")
    if not _drive_match(sc_b, non_scoring_mode="wrong", v=v):
        return v.report()
    pb = _final_player(sc_b)

    if not pa or not pb:
        v.inconclusive("final-results readable for both matches",
                       f"player_A={pa} player_B={pb}")
        return v.report()

    log(f"Match A final: total={pa.get('total')} answered={pa.get('answered')} "
        f"correct={pa.get('correct')} tier={pa.get('tier')!r}")
    log(f"Match B final: total={pb.get('total')} answered={pb.get('answered')} "
        f"correct={pb.get('correct')} tier={pb.get('tier')!r}")

    # Sanity: the two matches must represent IDENTICAL real performance —
    # same total points and same number of correct rounds. If they don't,
    # the comparison isn't apples-to-apples and we must not pass.
    same_total = int(pa.get("total") or 0) == int(pb.get("total") or 0)
    same_correct = int(pa.get("correct") or 0) == int(pb.get("correct") or 0)
    correct_count_ok = int(pa.get("correct") or 0) == len(SCORING_ROUNDS)
    if not (same_total and same_correct and correct_count_ok):
        v.inconclusive(
            "two matches have identical real performance",
            f"same_total={same_total} same_correct={same_correct} "
            f"correct_count_ok={correct_count_ok} "
            f"(A total={pa.get('total')} correct={pa.get('correct')}; "
            f"B total={pb.get('total')} correct={pb.get('correct')}; "
            f"expected correct={len(SCORING_ROUNDS)})")
        return v.report()

    # Belt-and-suspenders: confirm the answered-row counts actually
    # diverge (timeouts wrote no row, wrongs did). If they don't, the
    # bug's trigger condition wasn't exercised -> inconclusive.
    answered_diverges = int(pa.get("answered") or 0) != int(pb.get("answered") or 0)
    if not answered_diverges:
        v.inconclusive(
            "answered DB-row counts diverge between matches",
            f"A.answered={pa.get('answered')} B.answered={pb.get('answered')} "
            "(expected different: timeout writes no row, wrong writes one)")
        return v.report()

    # -------------------- Decisive assertion --------------------
    # Identical real performance MUST yield the same tier. Currently the
    # tier is derived from total/answered, so Match A (answered=4) reads
    # LEGENDARY while Match B (answered=7) reads EXPERT -> FAIL. Once
    # derive_tier divides by rounds played, both read the same tier -> PASS.
    v.check(
        "tier-denominator-is-rounds-played",
        pa.get("tier") == pb.get("tier"),
        f"timeout-match tier={pa.get('tier')!r} (answered={pa.get('answered')}) "
        f"vs wrong-match tier={pb.get('tier')!r} (answered={pb.get('answered')}) "
        f"— identical performance (total={pa.get('total')}, "
        f"correct={pa.get('correct')}/{TOTAL_ROUNDS}) must give the SAME tier")

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
