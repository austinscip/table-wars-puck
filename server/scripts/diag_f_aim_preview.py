"""Verify Slice F — BULLSEYE aim preview reticles.

Drives a 2-puck match to round 2 (BULLSEYE minigame), POSTs aim
preview from each puck, checks the TV receives the corresponding
`minigame_aim_preview` socket events.

Run with sandbox Flask up on :5002.
"""
from __future__ import annotations

import json
import sys
import threading
import time

import requests
import socketio  # noqa: F401 — used via SimpleClient


BASE = "http://localhost:5002"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def post(path: str, body: dict | None = None) -> dict:
    r = requests.post(f"{BASE}{path}", json=body or {}, timeout=5)
    return r.json() if r.text.strip().startswith("{") else {}


def setup_and_drive_to_bullseye() -> str:
    """Pair 2 pucks, play round 1, force-load round 2 (which is
    BULLSEYE minigame). Return session_code with minigame pending."""
    post("/api/pair/clear")
    code = post("/api/pair/request", {"puck_id": 901})["pair_code"]
    post("/api/pair/confirm", {"puck_id": 901, "code": code})
    post("/api/pair/request", {"puck_id": 902})
    post("/api/pair/confirm", {"puck_id": 902, "code": code})
    sc = post("/api/pair/start", {"puck_id": 901})["session_code"]
    # Round 1 pick + Q1
    lq = post(f"/api/sp/load-question/{sc}")
    post(f"/api/sp/select-category/{sc}", {
        "puck_id": lq["picker_puck_id"],
        "category_id": lq["offer"][0]["id"],
    })
    lq2 = post(f"/api/sp/load-question/{sc}")
    qid = lq2["question"]["id"]
    post("/api/sp/answer", {"session_code": sc, "puck_id": 901,
                            "question_id": qid, "answer": "A",
                            "response_time_ms": 1000})
    post("/api/sp/answer", {"session_code": sc, "puck_id": 902,
                            "question_id": qid, "answer": "B",
                            "response_time_ms": 1500})
    time.sleep(0.3)
    # Round 2 — should open BULLSEYE minigame
    mg = post(f"/api/sp/load-question/{sc}")
    if mg.get("phase") != "minigame" or mg.get("flavor") != "BULLSEYE":
        raise AssertionError(f"expected BULLSEYE minigame, got {mg}")
    return sc


def run() -> int:
    import socketio as sio
    log("=== F verification ===")
    sc = setup_and_drive_to_bullseye()
    log(f"sc={sc}, BULLSEYE minigame active")

    # Connect a socket client to receive minigame_aim_preview events
    client = sio.SimpleClient()
    client.connect(BASE)
    client.emit("join_session_room", {"session_code": sc})
    received = []

    def listener():
        while True:
            try:
                ev = client.receive(timeout=3)
                if ev and ev[0] == "minigame_aim_preview":
                    received.append(ev[1])
            except Exception:
                break

    t = threading.Thread(target=listener, daemon=True)
    t.start()
    time.sleep(0.5)

    # Puck 901 aims at B, then C
    r1 = post("/api/sp/minigame/preview", {
        "session_code": sc, "puck_id": 901, "quadrant": "B",
    })
    log(f"  puck 901 preview B: {r1}")
    time.sleep(0.3)
    r2 = post("/api/sp/minigame/preview", {
        "session_code": sc, "puck_id": 902, "quadrant": "D",
    })
    log(f"  puck 902 preview D: {r2}")
    time.sleep(0.3)
    r3 = post("/api/sp/minigame/preview", {
        "session_code": sc, "puck_id": 901, "quadrant": "C",
    })
    log(f"  puck 901 preview C: {r3}")
    time.sleep(1.0)

    client.disconnect()

    log(f"received {len(received)} minigame_aim_preview events:")
    for e in received:
        print(f"  {e}")

    # Assertions
    pucks_seen = {e.get("puck_id") for e in received}
    quads_by_puck: dict = {}
    for e in received:
        quads_by_puck.setdefault(e["puck_id"], []).append(e["quadrant"])

    ok = True
    if 901 not in pucks_seen or 902 not in pucks_seen:
        log(f"FAIL: expected both pucks in events, got {pucks_seen}")
        ok = False
    if quads_by_puck.get(901, [])[-1] != "C":
        log(f"FAIL: last 901 quadrant should be C, got {quads_by_puck.get(901)}")
        ok = False
    if quads_by_puck.get(902, []) != ["D"]:
        log(f"FAIL: 902 should have a single D event, got {quads_by_puck.get(902)}")
        ok = False
    # POST when no minigame pending should noop
    post(f"/api/sp/minigame/finish/{sc}")
    noop = post("/api/sp/minigame/preview", {
        "session_code": sc, "puck_id": 901, "quadrant": "A",
    })
    if not noop.get("noop"):
        log(f"FAIL: preview after finish should noop, got {noop}")
        ok = False

    log(f"RESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
