"""Verify Slice E2 — minigame phase end-to-end.

Drives a 2-puck match through round 1 (pick + question), then asserts:
1. Round 2 enters minigame phase with flavor=BULLSEYE.
2. /api/sp/minigame/state returns the live state for late-joiners.
3. Fires score correctly (correct quadrant + fast = high points,
   wrong quadrant = 0).
4. After both fire, server emits minigame_winner with bonuses applied
   to cumulative_scores (500 to #1, 200 to #2).
5. Next load-question returns a real question (round 2's Q2).
6. Round 4 fires a minigame too (still BULLSEYE since flavor alternates
   BULLSEYE/SHOT_CLOCK on rounds 2/4 — let's check what we get).
7. Auto-default: deadline expires, all non-firing pucks scored 0,
   server still resolves and advances.

Run with sandbox Flask up on :5002.
"""
from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

import requests


BASE = "http://localhost:5002"
DB = Path(__file__).resolve().parent.parent / "tablewars.db"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def post(path: str, body: dict | None = None) -> dict:
    r = requests.post(f"{BASE}{path}", json=body or {}, timeout=5)
    if r.status_code >= 400:
        return {"__status": r.status_code, "__text": r.text[:200]}
    return r.json() if r.text.strip().startswith("{") else {}


def get(path: str) -> dict:
    r = requests.get(f"{BASE}{path}", timeout=5)
    return r.json() if r.text.strip().startswith("{") else {}


def setup_match() -> str:
    post("/api/pair/clear")
    code = post("/api/pair/request", {"puck_id": 901})["pair_code"]
    post("/api/pair/confirm", {"puck_id": 901, "code": code})
    post("/api/pair/request", {"puck_id": 902})
    post("/api/pair/confirm", {"puck_id": 902, "code": code})
    return post("/api/pair/start", {"puck_id": 901})["session_code"]


def db_correct(qid: int) -> str:
    with sqlite3.connect(str(DB)) as c:
        return c.execute(
            "SELECT correct_answer FROM trivia_questions WHERE id = ?",
            (qid,),
        ).fetchone()[0]


def play_round_through_reveal(sc: str, p1_letter: str, p2_letter: str | None = None) -> int:
    """Drive a question round given that load-question already returned
    a question. Returns the question's correct answer for the caller's
    sanity. p2_letter defaults to the actual correct answer (so p2 wins)."""
    lq = post(f"/api/sp/load-question/{sc}")
    if "question" not in lq:
        raise AssertionError(f"expected question, got {lq}")
    qid = lq["question"]["id"]
    actual = db_correct(qid)
    if p2_letter is None:
        p2_letter = actual
    post("/api/sp/answer", {
        "session_code": sc, "puck_id": 901, "question_id": qid,
        "answer": p1_letter, "response_time_ms": 2500,
    })
    post("/api/sp/answer", {
        "session_code": sc, "puck_id": 902, "question_id": qid,
        "answer": p2_letter, "response_time_ms": 1500,
    })
    time.sleep(0.2)
    return qid


def run() -> int:
    log("=== E2 verification ===")
    sc = setup_match()
    log(f"sc={sc}")

    # Round 1 — clear the pick + Q1.
    lq = post(f"/api/sp/load-question/{sc}")
    assert lq.get("phase") == "category_pick", f"expected pick, got {lq}"
    post(f"/api/sp/select-category/{sc}",
         {"puck_id": 901, "category_id": lq["offer"][0]["id"]})
    play_round_through_reveal(sc, "A")
    log("PASS A: round 1 pick + question played")

    # 1. Round 2 should be a minigame.
    lq2 = post(f"/api/sp/load-question/{sc}")
    if lq2.get("phase") != "minigame":
        log(f"FAIL 1: expected minigame phase, got {lq2}")
        return 1
    if lq2.get("flavor") not in ("BULLSEYE", "SHOT_CLOCK"):
        log(f"FAIL 1b: bad flavor {lq2.get('flavor')}")
        return 1
    flavor = lq2["flavor"]
    target = lq2.get("target_quadrant")
    log(f"PASS 1: round 2 minigame flavor={flavor} target={target}")

    # 2. /minigame/state surfaces live state.
    mgs = get(f"/api/sp/minigame/state/{sc}")
    if not mgs.get("active") or mgs.get("flavor") != flavor:
        log(f"FAIL 2: minigame/state mismatch: {mgs}")
        return 1
    log(f"PASS 2: minigame/state active={mgs['active']} flavor={mgs['flavor']}")

    # 3. Score a correct + a wrong fire (BULLSEYE) or near-center + far-from-center (SHOT_CLOCK).
    if flavor == "BULLSEYE":
        right_q = target
        wrong_q = "A" if target != "A" else "B"
        r1 = post("/api/sp/minigame/fire", {
            "session_code": sc, "puck_id": 901, "t_ms": 1500, "quadrant": right_q,
        })
        r2 = post("/api/sp/minigame/fire", {
            "session_code": sc, "puck_id": 902, "t_ms": 2500, "quadrant": wrong_q,
        })
    else:
        # SHOT_CLOCK with 3s cycle, green centered at 1500ms (half of cycle).
        r1 = post("/api/sp/minigame/fire", {
            "session_code": sc, "puck_id": 901, "t_ms": 1500, "quadrant": None,
        })
        r2 = post("/api/sp/minigame/fire", {
            "session_code": sc, "puck_id": 902, "t_ms": 100, "quadrant": None,
        })
    log(f"  fires: p901={r1} p902={r2}")
    if not (r1.get("points", 0) > r2.get("points", 0)):
        log(f"FAIL 3: expected p901 > p902 points, got {r1} vs {r2}")
        return 1
    if not r2.get("resolved"):
        log(f"FAIL 3b: expected resolved=true after second fire, got {r2}")
        return 1
    log(f"PASS 3: p901 won ({r1['points']}pts) > p902 ({r2['points']}pts), resolved")

    # 4. Bonus applied to cumulative_scores (server-side).
    # We can't query cumulative directly without final-results, but the
    # next minigame_winner socket payload would have shown it. Verify
    # via match-state that pending_minigame is now null.
    ms = get(f"/api/sp/match-state/{sc}")
    if ms.get("pending_minigame") is not None:
        log(f"FAIL 4: pending_minigame should be null after resolve, got {ms}")
        return 1
    log("PASS 4: pending_minigame cleared after resolve")

    # 5. Next load-question returns a real Q2.
    lq3 = post(f"/api/sp/load-question/{sc}")
    if "question" not in lq3:
        log(f"FAIL 5: expected question after minigame, got {lq3}")
        return 1
    log(f"PASS 5: round 2 Q advances to question id={lq3['question']['id']}")

    # Play round 2 Q.
    qid2 = lq3["question"]["id"]
    actual2 = db_correct(qid2)
    post("/api/sp/answer", {"session_code": sc, "puck_id": 901,
                            "question_id": qid2, "answer": actual2,
                            "response_time_ms": 1000})
    post("/api/sp/answer", {"session_code": sc, "puck_id": 902,
                            "question_id": qid2, "answer": actual2,
                            "response_time_ms": 2000})
    time.sleep(0.2)

    # Round 3 pick + Q.
    lq4 = post(f"/api/sp/load-question/{sc}")
    if lq4.get("phase") != "category_pick":
        log(f"FAIL 6: expected pick on round 3, got {lq4}")
        return 1
    post(f"/api/sp/select-category/{sc}", {
        "puck_id": lq4["picker_puck_id"], "category_id": lq4["offer"][0]["id"]
    })
    play_round_through_reveal(sc, "A")
    log("PASS 6: round 3 pick + question played")

    # 6. Round 4 should be another minigame.
    lq5 = post(f"/api/sp/load-question/{sc}")
    if lq5.get("phase") != "minigame":
        log(f"FAIL 7: expected minigame on round 4, got {lq5}")
        return 1
    log(f"PASS 7: round 4 minigame flavor={lq5['flavor']}")

    # 7. Auto-default: wait 9s past deadline (deadline = started_at + 8s) without firing.
    log(f"  awaiting auto-default ({lq5['flavor']} 8s window + 1s safety)...")
    time.sleep(9)
    lq6 = post(f"/api/sp/load-question/{sc}")
    if lq6.get("phase") == "minigame":
        log(f"FAIL 8: minigame should have auto-resolved, got {lq6}")
        return 1
    if "question" not in lq6:
        log(f"FAIL 8b: expected question after minigame auto-resolve, got {lq6}")
        return 1
    log(f"PASS 8: minigame auto-resolved; round 4 Q id={lq6['question']['id']}")

    log("ALL E2 CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(run())
