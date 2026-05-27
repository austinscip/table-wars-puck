"""Diagnostic: drive a full match to MATCH_ENDED, then exercise both
'Play again' (in-Hub tap) and 'Reset all' (Hub button) flows and verify
the second match accepts answers.

User-reported symptom: after completing a game and starting a new one
the Hub does not let me choose answers, even after clicking 'Reset all'.

Two suspect mechanisms:
  1. usePuckState.ts line ~331: setState({kind:'MATCH_ENDED'}) + early
     return kills the polling timer. After MATCH_ENDED -> Play again ->
     IN_GAME_IDLE, polling is dead and the puck never transitions to
     ANSWERING for match-2 Q1.
  2. server sp_reset() (and _clear_lobby) don't clear _QUESTION_TRACKER,
     so /api/sp/current-question returns the OLD qid for the old session.
     New session would have its own key though, so probably fine for
     Reset all (new session_code) but stale for Play again (same sc).

Run with sandbox Flask up on :5002 and dist/ built with VITE_DEV_TOOLS=1.
"""
from __future__ import annotations

import json
import sys
import time

import requests
from playwright.sync_api import sync_playwright, Page, Request, Response


BASE = "http://localhost:5002"
TV = f"{BASE}/tv/speed-pyramid"
HUB = f"{TV}/dev/hub"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def reset_state() -> None:
    requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)


def attach_log(page: Page, label: str, sink: list[dict]) -> None:
    def on_req(req: Request) -> None:
        if any(x in req.url for x in ("/api/sp/answer", "/api/sp/load-question",
                                       "/api/sp/reset", "/api/pair/clear",
                                       "/api/sp/current-question")):
            sink.append({"label": label, "phase": "req", "url": req.url,
                         "body": req.post_data, "ts": time.time()})
            short = req.url.split(BASE)[-1]
            log(f"{label} -> {req.method} {short} body={req.post_data}")
    def on_resp(resp: Response) -> None:
        if any(x in resp.url for x in ("/api/sp/answer", "/api/sp/load-question",
                                        "/api/sp/reset", "/api/pair/clear",
                                        "/api/sp/current-question")):
            try:
                body = resp.text()
            except Exception as e:
                body = f"<text err: {e}>"
            sink.append({"label": label, "phase": "resp", "url": resp.url,
                         "status": resp.status, "body": body[:400],
                         "ts": time.time()})
            short = resp.url.split(BASE)[-1]
            log(f"{label} <- {resp.status} {short} body={body[:160]}")
    page.on("request", on_req)
    page.on("response", on_resp)


def puck_row(page: Page, idx: int):
    return page.locator("main > div").nth(idx)


def puck_state_text(page: Page, idx: int) -> str:
    try:
        return puck_row(page, idx).locator("span.text-cyan-300").first.inner_text(timeout=1000)
    except Exception:
        return ""


def wait_for(page: Page, idx: int, substr: str, timeout_s: float = 10) -> str:
    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        last = puck_state_text(page, idx)
        if substr in last:
            return last
        time.sleep(0.2)
    return last


def pair_via_hub(hub: Page) -> None:
    """Drive pair flow through the Hub: puck1 host, puck2 joiner, host start."""
    log("pairing flow")
    puck_row(hub, 0).get_by_role("button", name="Hold 1s").click()
    time.sleep(0.5)
    puck_row(hub, 0).locator("button", has_text="Confirm").click()
    time.sleep(0.8)
    puck_row(hub, 1).get_by_role("button", name="Hold 1s").click()
    time.sleep(0.8)
    puck_row(hub, 0).get_by_role("button", name="Start match").click()
    time.sleep(1.2)


def get_sc() -> str | None:
    ls = requests.get(f"{BASE}/api/pair/lobby-state", timeout=5).json()
    return ls.get("session_code")


def drive_full_match_rest(sc: str, fresh_start: bool = True) -> None:
    """Drive a 7-round match via REST. Now (E1/E2) the flow alternates
    question rounds with category picks (rounds 1/3/5/7) and minigames
    (rounds 2/4/6), so the drive loop iterates more than 7 times.

    fresh_start: call sp_reset first to zero round counters.
    """
    if fresh_start:
        requests.post(f"{BASE}/api/sp/reset/{sc}", timeout=5)
    # Up to ~18 phases: 4 picks + 7 questions + 3 minigames + slop.
    for _ in range(25):
        lq = requests.post(f"{BASE}/api/sp/load-question/{sc}", timeout=5).json()
        phase = lq.get("phase")
        if phase == "category_pick":
            picker = lq["picker_puck_id"]
            cat = lq["offer"][0]["id"]
            requests.post(f"{BASE}/api/sp/select-category/{sc}", json={
                "puck_id": picker, "category_id": cat
            }, timeout=5)
            continue
        if phase == "minigame":
            requests.post(f"{BASE}/api/sp/minigame/finish/{sc}", timeout=5)
            continue
        if "question" not in lq:
            log(f"  drive aborting: unexpected response {lq!r}")
            return
        qid = lq["question"]["id"]
        requests.post(f"{BASE}/api/sp/answer", json={
            "session_code": sc, "puck_id": 1, "question_id": qid,
            "answer": "A", "response_time_ms": 1000,
        }, timeout=5)
        requests.post(f"{BASE}/api/sp/answer", json={
            "session_code": sc, "puck_id": 2, "question_id": qid,
            "answer": "B", "response_time_ms": 1500,
        }, timeout=5)
        time.sleep(0.2)
    final = requests.post(f"{BASE}/api/sp/load-question/{sc}", timeout=5)
    log(f"final load-question status={final.status_code} body={final.text[:120]}")


def run() -> int:
    reset_state()
    log("state cleared")

    network: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        hub = ctx.new_page()
        tv = ctx.new_page()
        attach_log(hub, "HUB", network)
        attach_log(tv, "TV ", network)

        hub.goto(HUB, wait_until="domcontentloaded")
        tv.goto(TV + "/", wait_until="domcontentloaded")
        time.sleep(1.0)

        # ===== MATCH 1 =====
        pair_via_hub(hub)
        sc1 = get_sc()
        log(f"match1 sc={sc1}")
        drive_full_match_rest(sc1)
        time.sleep(2.0)

        s1 = puck_state_text(hub, 0)
        s2 = puck_state_text(hub, 1)
        log(f"after match1 puck1: {s1!r}")
        log(f"after match1 puck2: {s2!r}")

        # ===== TEST A: 'Play again' (in-hub MATCH_ENDED tap) =====
        log("--- TEST A: Play again on puck1 ---")
        try:
            puck_row(hub, 0).get_by_role("button", name="Play again").click(timeout=3000)
            log("Play again click: dispatched")
        except Exception as e:
            log(f"Play again click err: {e!r}")
        time.sleep(1.5)
        log(f"playAgain post-tap puck1: {puck_state_text(hub, 0)!r}")
        log(f"playAgain post-tap puck2: {puck_state_text(hub, 1)!r}")

        # TV would call load-question. Drive it via REST too.
        sc2 = get_sc()
        log(f"sc after Play again: {sc2}")
        if sc2:
            r = requests.post(f"{BASE}/api/sp/load-question/{sc2}", timeout=5)
            log(f"playAgain Q1 load status={r.status_code} body={r.text[:160]}")
        time.sleep(1.5)
        log(f"playAgain Q1 puck1: {puck_state_text(hub, 0)!r}")
        log(f"playAgain Q1 puck2: {puck_state_text(hub, 1)!r}")

        # Try to click answer A on Q1 of match 2 (Play again path).
        log("playAgain Q1: click puck1 A")
        try:
            puck_row(hub, 0).get_by_role("button", name="A", exact=True).click(timeout=3000)
            log("playAgain Q1 puck1 A click: dispatched")
        except Exception as e:
            log(f"playAgain Q1 puck1 A click err: {e!r}")
        time.sleep(1.0)

        # ===== TEST B: 'Reset all' fresh new match =====
        log("--- TEST B: Reset all then re-pair ---")
        hub.get_by_role("button", name="Reset all").click()
        time.sleep(0.6)
        log(f"after reset puck1: {puck_state_text(hub, 0)!r}")
        log(f"after reset puck2: {puck_state_text(hub, 1)!r}")

        pair_via_hub(hub)
        sc3 = get_sc()
        log(f"match3 sc={sc3}")
        if sc3:
            r = requests.post(f"{BASE}/api/sp/load-question/{sc3}", timeout=5)
            log(f"resetAll Q1 load status={r.status_code} body={r.text[:160]}")
        time.sleep(1.5)
        log(f"resetAll Q1 puck1: {puck_state_text(hub, 0)!r}")
        log(f"resetAll Q1 puck2: {puck_state_text(hub, 1)!r}")

        log("resetAll Q1: click puck1 A")
        try:
            puck_row(hub, 0).get_by_role("button", name="A", exact=True).click(timeout=3000)
            log("resetAll Q1 puck1 A click: dispatched")
        except Exception as e:
            log(f"resetAll Q1 puck1 A click err: {e!r}")
        time.sleep(1.0)

        # ===== TEST C: loop Play again N times to prove unlimited matches =====
        # Server clears the lobby on match-complete, so get_sc() returns
        # None after the first match. The session_code itself persists,
        # though — sp_reset operates on it directly. Capture once and reuse.
        # In production the TV's ScoreboardScreen drives /load-question on
        # match_reset; here we drive it via REST.
        log("--- TEST C: 5x Play again loop ---")
        sc_persist = sc3  # captured before Reset all? actually sc3 is post-reset; recapture now.
        sc_persist = get_sc()
        log(f"  loop session sc={sc_persist}")
        match_loop_ok = True
        for i in range(5):
            log(f"-- loop iter {i+1} (sc={sc_persist}) --")
            if not sc_persist:
                log(f"  iter {i+1} no session_code, abort")
                match_loop_ok = False
                break
            drive_full_match_rest(sc_persist)
            time.sleep(1.2)
            s1 = puck_state_text(hub, 0)
            s2 = puck_state_text(hub, 1)
            log(f"  iter {i+1} end-of-match puck1={s1!r} puck2={s2!r}")
            if "MATCH ENDED" not in s1 or "MATCH ENDED" not in s2:
                log(f"  iter {i+1} FAIL — pucks not in MATCH ENDED")
                match_loop_ok = False
                break
            try:
                puck_row(hub, 0).get_by_role("button", name="Play again").click(timeout=3000)
            except Exception as e:
                log(f"  iter {i+1} Play again click err: {e!r}")
                match_loop_ok = False
                break
            time.sleep(1.2)
            # Drive Q1 of the new match. Post-E1 the first load-question
            # returns a category-pick phase, not a question. Auto-select
            # the first offer so the puck flow continues to a Q.
            lq = requests.post(f"{BASE}/api/sp/load-question/{sc_persist}", timeout=5).json()
            if lq.get("phase") == "category_pick":
                requests.post(f"{BASE}/api/sp/select-category/{sc_persist}", json={
                    "puck_id": lq["picker_puck_id"],
                    "category_id": lq["offer"][0]["id"],
                }, timeout=5)
                requests.post(f"{BASE}/api/sp/load-question/{sc_persist}", timeout=5)
            time.sleep(1.5)
            s1 = puck_state_text(hub, 0)
            s2 = puck_state_text(hub, 1)
            log(f"  iter {i+1} new-match Q1 puck1={s1!r} puck2={s2!r}")
            if "ANSWERING" not in s1 or "ANSWERING" not in s2:
                log(f"  iter {i+1} FAIL — pucks not in ANSWERING after Play again")
                match_loop_ok = False
                break
            try:
                puck_row(hub, 0).get_by_role("button", name="A", exact=True).click(timeout=3000)
                puck_row(hub, 1).get_by_role("button", name="B", exact=True).click(timeout=3000)
            except Exception as e:
                log(f"  iter {i+1} ABCD click err: {e!r}")
                match_loop_ok = False
                break
            time.sleep(1.0)
        log(f"--- TEST C result: {'PASS' if match_loop_ok else 'FAIL'} ---")

        # Network summary
        ans_events = [e for e in network if "/api/sp/answer" in e["url"]]
        log(f"===== /api/sp/answer events ({len(ans_events)}) =====")
        for e in ans_events[-10:]:
            print(json.dumps(e, indent=2))

        hub.screenshot(path="/tmp/diag_match2_hub.png", full_page=True)
        tv.screenshot(path="/tmp/diag_match2_tv.png", full_page=True)
        log("screenshots: /tmp/diag_match2_hub.png /tmp/diag_match2_tv.png")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(run())
