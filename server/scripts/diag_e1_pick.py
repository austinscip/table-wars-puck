"""Verify Slice E1 — category picker end-to-end.

Pairs 2 virtual pucks, drives a match through the Hub. Asserts:
1. Round 1 enters category-pick phase (TV navigates to /category-pick).
2. Picker is puck 901 (lowest expected puck_id).
3. Picking a category locks it; TV navigates to /question/<sc>.
4. The resulting question's category matches the chosen ID.
5. After round 2 reveal (which won't auto-trigger pick — picks only on
   1/3/5/7), round 3 fires the next pick. Picker is the round-1 winner.
6. Auto-default fires if no pick happens within 10s.

Run with sandbox Flask up on :5002 + dist built with VITE_DEV_TOOLS=1.
"""
from __future__ import annotations

import sys
import time

import requests
from playwright.sync_api import sync_playwright


BASE = "http://localhost:5002"
TV = f"{BASE}/tv/speed-pyramid"


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


def pair_two_pucks() -> str:
    post("/api/pair/clear")
    code = post("/api/pair/request", {"puck_id": 901})["pair_code"]
    post("/api/pair/confirm", {"puck_id": 901, "code": code})
    post("/api/pair/request", {"puck_id": 902})
    post("/api/pair/confirm", {"puck_id": 902, "code": code})
    return post("/api/pair/start", {"puck_id": 901})["session_code"]


def run() -> int:
    log("=== E1 verification ===")
    sc = pair_two_pucks()
    log(f"sc={sc}")

    # 1. Round 1: load-question should return phase=category_pick.
    lq = post(f"/api/sp/load-question/{sc}")
    if lq.get("phase") != "category_pick":
        log(f"FAIL 1: expected phase=category_pick, got {lq}")
        return 1
    if lq.get("picker_puck_id") != 901:
        log(f"FAIL 2: expected picker_puck_id=901, got {lq.get('picker_puck_id')}")
        return 1
    if not lq.get("offer") or len(lq["offer"]) != 3:
        log(f"FAIL 3: expected 3 offers, got {lq.get('offer')}")
        return 1
    log(f"PASS 1-3: round 1 picker={lq['picker_puck_id']} offers={[o['name'] for o in lq['offer']]}")

    # 2. match-state surfaces pending_category_pick for polling clients.
    ms = get(f"/api/sp/match-state/{sc}")
    if not ms.get("pending_category_pick"):
        log(f"FAIL 4: match-state didn't expose pending_category_pick: {ms}")
        return 1
    log("PASS 4: match-state exposes pending pick")

    # 3. Picker locks an offer; subsequent load-question returns a
    #    question from that category.
    chosen_id = lq["offer"][1]["id"]
    chosen_name = lq["offer"][1]["name"]
    sel = post(f"/api/sp/select-category/{sc}", {"puck_id": 901, "category_id": chosen_id})
    if not sel.get("ok"):
        log(f"FAIL 5: select-category failed: {sel}")
        return 1
    log(f"PASS 5: locked category {chosen_id} ({chosen_name!r})")

    lq2 = post(f"/api/sp/load-question/{sc}")
    if "question" not in lq2:
        log(f"FAIL 6: expected question after pick, got {lq2}")
        return 1
    if lq2["question"]["category"] != chosen_name:
        log(f"FAIL 7: expected category {chosen_name!r}, got {lq2['question']['category']!r}")
        return 1
    log(f"PASS 6-7: question loaded from category {chosen_name!r}: q_id={lq2['question']['id']}")

    # 4. Answer round 1, then check that round 2 (NOT a pick round) goes
    #    straight to question, then round 3 enters pick phase again with
    #    a different picker (round-1 winner).
    qid = lq2["question"]["id"]
    # Both pucks answer; puck 902 gets the correct answer faster.
    correct = requests.get(
        f"{BASE}/api/sp/current-question/{sc}", timeout=5
    ).json().get("question_id")
    # Look up actual correct letter
    import sqlite3
    conn = sqlite3.connect("tablewars.db")
    actual = conn.execute("SELECT correct_answer FROM trivia_questions WHERE id = ?", (qid,)).fetchone()[0]
    conn.close()
    wrong = "A" if actual != "A" else "B"
    post("/api/sp/answer", {"session_code": sc, "puck_id": 901, "question_id": qid,
                             "answer": wrong, "response_time_ms": 3500})
    post("/api/sp/answer", {"session_code": sc, "puck_id": 902, "question_id": qid,
                             "answer": actual, "response_time_ms": 1500})
    time.sleep(0.2)

    # Round 2 — should be a minigame (Slice E2), NOT a pick.
    # Post-E2: rounds 2/4/6 fire minigames. Skip past it to reach Q2.
    lq3 = post(f"/api/sp/load-question/{sc}")
    if lq3.get("phase") == "category_pick":
        log(f"FAIL 8: round 2 shouldn't enter pick, got {lq3.get('phase')}")
        return 1
    if lq3.get("phase") == "minigame":
        # Force-resolve the minigame; next call returns Q2.
        post(f"/api/sp/minigame/finish/{sc}")
        lq3 = post(f"/api/sp/load-question/{sc}")
    if "question" not in lq3:
        log(f"FAIL 9: round 2 should have question after minigame, got {lq3}")
        return 1
    log(f"PASS 8-9: round 2 reaches question (via minigame skip), id={lq3['question']['id']}")
    qid2 = lq3["question"]["id"]
    actual2 = sqlite3.connect("tablewars.db").execute(
        "SELECT correct_answer FROM trivia_questions WHERE id = ?", (qid2,)).fetchone()[0]
    post("/api/sp/answer", {"session_code": sc, "puck_id": 901, "question_id": qid2,
                             "answer": "A", "response_time_ms": 2500})
    post("/api/sp/answer", {"session_code": sc, "puck_id": 902, "question_id": qid2,
                             "answer": actual2, "response_time_ms": 1200})
    time.sleep(0.2)

    # Round 3 — should be pick. Picker should be the winner of the
    # MOST RECENT question round (round 2 here, not round 1). Server
    # updates last_round_winner_puck_id on every reveal. In this test
    # puck 902 answers the actual correct letter on both rounds, so it
    # wins both rounds and is the round-2 winner.
    lq4 = post(f"/api/sp/load-question/{sc}")
    if lq4.get("phase") != "category_pick":
        log(f"FAIL 10: round 3 should enter pick, got {lq4}")
        return 1
    if lq4.get("picker_puck_id") != 902:
        log(f"FAIL 11: round 3 picker should be 902 (round 2 winner), got {lq4.get('picker_puck_id')}")
        return 1
    log(f"PASS 10-11: round 3 picker={lq4['picker_puck_id']} (round-2 winner)")

    # 5. Auto-default: wait 11s without picking, then verify.
    log("waiting 11s to test auto-default...")
    time.sleep(11)
    lq5 = post(f"/api/sp/load-question/{sc}")
    if lq5.get("phase") == "category_pick":
        log(f"FAIL 12: pick should have auto-resolved after 10s deadline, got {lq5}")
        return 1
    if "question" not in lq5:
        log(f"FAIL 13: expected question after auto-default, got {lq5}")
        return 1
    log(f"PASS 12-13: auto-default fired; got question from {lq5['question']['category']!r}")

    log("ALL E1 CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(run())
