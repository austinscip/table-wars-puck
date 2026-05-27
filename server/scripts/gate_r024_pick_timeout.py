"""Gate for R024 — category-pick timeout must auto-advance the match.

Drives a real match to the round-1 category pick on the TV and then does
NOTHING (no pick) for the full deadline. The match MUST auto-advance to a
question instead of hanging at 0s. The existing e2e_full_match always
CLICKS a category, so it never exercised this timeout path — which is
exactly the bug the user hit ("round 3 category pick went to 0s and
stopped completely").

Gate assertion name: pick-timeout-auto-advances-to-question

Run with sandbox Flask up on :5002.
"""
from __future__ import annotations

import sys
import time

import requests
from playwright.sync_api import sync_playwright, Page


BASE = "http://localhost:5002"
TV = f"{BASE}/tv/speed-pyramid"
HUB = f"{TV}/dev/hub"


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def puck_row(page: Page, idx: int):
    return page.locator("main > div").nth(idx)


def run() -> int:
    requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        ctx = browser.new_context(viewport={"width": 1600, "height": 900})
        hub = ctx.new_page()
        tv = ctx.new_page()
        hub.goto(HUB, wait_until="domcontentloaded")
        tv.goto(TV + "/", wait_until="domcontentloaded")
        time.sleep(0.8)

        puck_row(hub, 0).get_by_role("button", name="Hold 1s").click(); time.sleep(0.5)
        puck_row(hub, 0).locator("button", has_text="Confirm").click(); time.sleep(0.6)
        puck_row(hub, 1).get_by_role("button", name="Hold 1s").click(); time.sleep(0.8)
        puck_row(hub, 0).get_by_role("button", name="Start match").click(); time.sleep(1.2)
        sc = requests.get(f"{BASE}/api/pair/lobby-state", timeout=5).json().get("session_code")
        if not sc:
            log("FAIL: no session_code"); browser.close(); return 1
        tv.goto(f"{TV}/question/{sc}", wait_until="domcontentloaded")

        # Wait for the TV to land on the category-pick screen (round 1).
        on_pick = False
        for _ in range(40):
            if "/category-pick/" in tv.evaluate("() => location.pathname"):
                on_pick = True
                break
            time.sleep(0.25)
        if not on_pick:
            log(f"INCONCLUSIVE: TV never reached category-pick (route={tv.evaluate('() => location.pathname')})")
            browser.close(); return 2
        log("TV is on category-pick — now doing NOTHING, letting it time out")

        # Do not pick. Watch the route. With the fix it must reach /question
        # shortly after the 10s deadline. Allow deadline + generous margin.
        deadline = time.time() + 16
        reached_q = False
        last = ""
        while time.time() < deadline:
            last = tv.evaluate("() => location.pathname")
            if "/question/" in last:
                reached_q = True
                break
            time.sleep(0.3)

        # Confirm a real question is actually active (not just the route).
        q_active = False
        if reached_q:
            for _ in range(12):
                cq = requests.get(f"{BASE}/api/sp/current-question/{sc}", timeout=4).json()
                if cq.get("active") and cq.get("question_id"):
                    q_active = True
                    break
                time.sleep(0.4)

        browser.close()

    log("")
    if reached_q and q_active:
        log("RESULT: PASS — pick timeout auto-advanced to an active question.")
        log("        gate: pick-timeout-auto-advances-to-question")
        return 0
    log(f"RESULT: FAIL — match hung at the pick (route={last}, reached_q={reached_q}, q_active={q_active})")
    return 1


if __name__ == "__main__":
    sys.exit(run())
