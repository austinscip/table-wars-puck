"""Verify Slice K — 8-player Hub demo renders cleanly on 1920x1080.

Drives 8 pucks through a full match via REST, captures viewport
screenshots of QuestionScreen (mid-question) and ScoreboardScreen
(final). Asserts no element overflows the viewport.

Run with sandbox Flask up on :5002:
    cd ~/table-wars-puck-sandbox/server
    DATABASE_URL= venv/bin/python scripts/diag_8_player.py
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


def pair_n_pucks(n: int) -> tuple[str, str]:
    """Pair n virtual pucks (puck_id 901..900+n) and start the match.
    Returns (lobby_code, session_code)."""
    post("/api/pair/clear")
    code = post("/api/pair/request", {"puck_id": 901})["pair_code"]
    post("/api/pair/confirm", {"puck_id": 901, "code": code})
    for i in range(2, n + 1):
        post("/api/pair/request", {"puck_id": 900 + i})
        post("/api/pair/confirm", {"puck_id": 900 + i, "code": code})
    sc = post("/api/pair/start", {"puck_id": 901})["session_code"]
    return code, sc


def drive_match_full(sc: str, n: int) -> None:
    """Drive 7 rounds with all n pucks answering."""
    for round_idx in range(7):
        lq = post(f"/api/sp/load-question/{sc}")
        if "question" not in lq:
            return
        qid = lq["question"]["id"]
        for pid in range(901, 901 + n):
            post("/api/sp/answer", {
                "session_code": sc,
                "puck_id": pid,
                "question_id": qid,
                "answer": "A" if pid % 2 else "B",
                "response_time_ms": 1500 + (pid - 901) * 200,
            })
        time.sleep(0.2)


def check_overflow(page) -> dict:
    """Capture document layout vs viewport. Return overflow report."""
    return page.evaluate("""() => {
      const vw = window.innerWidth, vh = window.innerHeight;
      const body = document.body;
      return {
        viewport: {w: vw, h: vh},
        document: {sw: body.scrollWidth, sh: body.scrollHeight},
        overflows_h: body.scrollHeight > vh,
        overflows_w: body.scrollWidth > vw,
      };
    }""")


def run() -> int:
    log("Slice K verification — 8 pucks through full match")
    _, sc = pair_n_pucks(8)
    log(f"sc={sc} — 8 pucks paired")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--autoplay-policy=no-user-gesture-required"],
        )
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
        tv = ctx.new_page()
        tv.goto(TV + "/", wait_until="domcontentloaded")
        time.sleep(1.0)

        # Drive first 4 rounds — TV should be on /question/{sc} mid-match.
        for round_idx in range(4):
            lq = post(f"/api/sp/load-question/{sc}")
            if "question" not in lq: break
            qid = lq["question"]["id"]
            for pid in range(901, 909):
                post("/api/sp/answer", {
                    "session_code": sc, "puck_id": pid,
                    "question_id": qid, "answer": "A" if pid % 2 else "B",
                    "response_time_ms": 1500 + (pid - 901) * 200,
                })
            time.sleep(0.3)

        # Navigate TV directly to the question screen so we can sample
        # rendered sidebar at 8 lanes.
        tv.goto(f"{TV}/question/{sc}", wait_until="domcontentloaded")
        time.sleep(2.0)
        mid_state = check_overflow(tv)
        log(f"mid-question (8 lanes) viewport={mid_state['viewport']} doc={mid_state['document']} oh={mid_state['overflows_h']} ow={mid_state['overflows_w']}")
        tv.screenshot(path="/tmp/k_8puck_question.png", full_page=False)

        # Finish the match
        for round_idx in range(4, 7):
            lq = post(f"/api/sp/load-question/{sc}")
            if "question" not in lq: break
            qid = lq["question"]["id"]
            for pid in range(901, 909):
                post("/api/sp/answer", {
                    "session_code": sc, "puck_id": pid,
                    "question_id": qid, "answer": "A" if pid % 2 else "B",
                    "response_time_ms": 1500 + (pid - 901) * 200,
                })
            time.sleep(0.3)
        post(f"/api/sp/load-question/{sc}")  # 409 match-complete

        tv.goto(f"{TV}/scoreboard/{sc}", wait_until="domcontentloaded")
        time.sleep(2.5)
        sb_state = check_overflow(tv)
        log(f"scoreboard (8 players) viewport={sb_state['viewport']} doc={sb_state['document']} oh={sb_state['overflows_h']} ow={sb_state['overflows_w']}")
        tv.screenshot(path="/tmp/k_8puck_scoreboard.png", full_page=False)

        browser.close()

    ok = (not mid_state["overflows_h"] and not mid_state["overflows_w"]
          and not sb_state["overflows_h"] and not sb_state["overflows_w"])
    log(f"RESULT: {'PASS' if ok else 'FAIL'}")
    log("screenshots: /tmp/k_8puck_question.png /tmp/k_8puck_scoreboard.png")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
