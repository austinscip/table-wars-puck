"""Verify bug 17 + 18 fixes:

  17: Clicking 'Back to start' at MATCH_ENDED should (a) clear the
      server lobby, (b) emit lobby_cancelled, (c) make the TV bounce
      from /scoreboard to /title.

  18: Reset all + re-pair afterward should land cleanly with no stale
      session/lobby state.

Run with sandbox Flask up on :5002 + dist built with VITE_DEV_TOOLS=1.
"""
from __future__ import annotations

import json
import sys
import time

import requests
from playwright.sync_api import sync_playwright, Page


BASE = "http://localhost:5002"
TV = f"{BASE}/tv/speed-pyramid"
HUB = f"{TV}/dev/hub"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def post(path, body=None):
    r = requests.post(f"{BASE}{path}", json=body or {}, timeout=5)
    return r


def drive_match_to_end_rest(sc: str) -> None:
    post(f"/api/sp/reset/{sc}")
    for r in range(7):
        lq = post(f"/api/sp/load-question/{sc}").json()
        if "question" not in lq: return
        qid = lq["question"]["id"]
        post("/api/sp/answer", {"session_code": sc, "puck_id": 1,
            "question_id": qid, "answer": "A", "response_time_ms": 1000})
        post("/api/sp/answer", {"session_code": sc, "puck_id": 2,
            "question_id": qid, "answer": "B", "response_time_ms": 1500})
        time.sleep(0.1)
    post(f"/api/sp/load-question/{sc}")  # 409 match-complete


def pair_via_hub(hub: Page) -> None:
    hub.locator("main > div").nth(0).get_by_role("button", name="Hold 1s").click()
    time.sleep(0.5)
    hub.locator("main > div").nth(0).locator("button", has_text="Confirm").click()
    time.sleep(0.6)
    hub.locator("main > div").nth(1).get_by_role("button", name="Hold 1s").click()
    time.sleep(0.8)
    hub.locator("main > div").nth(0).get_by_role("button", name="Start match").click()
    time.sleep(1.0)


def tv_path(tv: Page) -> str:
    return tv.evaluate("() => location.pathname")


def run() -> int:
    post("/api/pair/clear")
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        ctx = b.new_context()
        hub = ctx.new_page()
        tv = ctx.new_page()

        hub.goto(HUB, wait_until="domcontentloaded")
        tv.goto(TV + "/", wait_until="domcontentloaded")
        time.sleep(1.5)

        # ===== BUG 17 fix: Back to start -> TV bounces to title =====
        log("BUG 17 fix: pair + run match + Back to start")
        pair_via_hub(hub)
        sc = requests.get(f"{BASE}/api/pair/lobby-state").json()["session_code"]
        log(f"  sc={sc}")
        drive_match_to_end_rest(sc)
        time.sleep(2.0)
        log(f"  TV path post match: {tv_path(tv)}")  # should be /scoreboard/{sc}
        log(f"  puck1 state: {hub.locator('main > div').nth(0).locator('span.text-cyan-300').first.inner_text()}")

        hub.locator("main > div").nth(0).get_by_role("button", name="Back to start").click()
        time.sleep(1.5)
        tv_path_after = tv_path(tv)
        puck1_after = hub.locator('main > div').nth(0).locator('span.text-cyan-300').first.inner_text()
        lobby_after = requests.get(f"{BASE}/api/pair/lobby-state").json()
        log(f"  TV path after Back to start: {tv_path_after!r}")
        log(f"  puck1 state: {puck1_after!r}")
        log(f"  server lobby: {lobby_after}")
        bug17_ok = (tv_path_after.rstrip("/") == "/tv/speed-pyramid"
                    and puck1_after == "IDLE"
                    and not lobby_after.get("active"))
        log(f"  BUG 17 fix result: {'PASS' if bug17_ok else 'FAIL'}")

        # ===== BUG 18 fix: Reset all -> re-pair -> works cleanly =====
        log("BUG 18 fix: pair + run match + Reset all + re-pair")
        # Reset state since we've already cleared via Back to start
        pair_via_hub(hub)
        sc = requests.get(f"{BASE}/api/pair/lobby-state").json()["session_code"]
        log(f"  sc2={sc}")
        drive_match_to_end_rest(sc)
        time.sleep(2.0)
        log(f"  TV path post match2: {tv_path(tv)}")

        hub.get_by_role("button", name="Reset all").click()
        time.sleep(1.5)
        log(f"  TV path post Reset all: {tv_path(tv)!r}")
        log(f"  puck1 state: {hub.locator('main > div').nth(0).locator('span.text-cyan-300').first.inner_text()!r}")
        log(f"  puck2 state: {hub.locator('main > div').nth(1).locator('span.text-cyan-300').first.inner_text()!r}")

        # Now re-pair
        log("  re-pair")
        pair_via_hub(hub)
        sc3 = requests.get(f"{BASE}/api/pair/lobby-state").json().get("session_code")
        log(f"  sc3={sc3}")
        # Drive Q1
        if sc3:
            requests.post(f"{BASE}/api/sp/load-question/{sc3}", timeout=5)
        time.sleep(3.0)  # allow TV to walk title -> countdown -> question
        s1 = hub.locator('main > div').nth(0).locator('span.text-cyan-300').first.inner_text()
        s2 = hub.locator('main > div').nth(1).locator('span.text-cyan-300').first.inner_text()
        log(f"  match2 Q1 puck1={s1!r} puck2={s2!r}")
        tv_match3 = tv_path(tv)
        log(f"  TV path on new match Q1: {tv_match3!r}")
        # The TV can be at /countdown/{sc} (transitional) or /question/{sc}
        # depending on when we sample — both indicate the new match started.
        bug18_ok = (
            "ANSWERING" in s1 and "ANSWERING" in s2
            and (f"/question/{sc3}" in tv_match3 or f"/countdown/{sc3}" in tv_match3)
        )
        log(f"  BUG 18 fix result: {'PASS' if bug18_ok else 'FAIL'}")

        log(f"OVERALL: BUG17={'PASS' if bug17_ok else 'FAIL'} BUG18={'PASS' if bug18_ok else 'FAIL'}")
        b.close()
    return 0 if (bug17_ok and bug18_ok) else 1


if __name__ == "__main__":
    sys.exit(run())
