"""Diagnose 'bullseye minigame had no results'.

Hypothesis: the minigame_winner socket is one-shot. If both pucks fire
before the TV's MinigameScreen has mounted + subscribed (or it resolves
between the minigameState check and the socket subscription), the TV
misses the event and never renders WinnerPanel — or minigameState
already returns active:false and the TV jumps straight to /question.
Result: the player sees no results.

This drives a real match to the round-2 BULLSEYE, fires both pucks as
fast as possible (worst case for the race), and samples the TV route +
visible text to see whether 'RESULTS' / a WinnerPanel ever appears or the
TV skips it.

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


def puck_state(page: Page, idx: int) -> str:
    try:
        return puck_row(page, idx).locator("span.text-cyan-300").first.inner_text(timeout=1500)
    except Exception:
        return ""


def run() -> int:
    requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)
    saw_minigame_route = False
    saw_results_text = False
    timeline: list[tuple[str, str]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        ctx = browser.new_context(viewport={"width": 1600, "height": 900})
        hub = ctx.new_page()
        tv = ctx.new_page()
        hub.goto(HUB, wait_until="domcontentloaded")
        tv.goto(TV + "/", wait_until="domcontentloaded")
        time.sleep(0.8)
        tv.mouse.click(800, 450); time.sleep(0.4)

        puck_row(hub, 0).get_by_role("button", name="Hold 1s").click(); time.sleep(0.5)
        puck_row(hub, 0).locator("button", has_text="Confirm").click(); time.sleep(0.6)
        puck_row(hub, 1).get_by_role("button", name="Hold 1s").click(); time.sleep(0.8)
        puck_row(hub, 0).get_by_role("button", name="Start match").click(); time.sleep(1.2)
        sc = requests.get(f"{BASE}/api/pair/lobby-state", timeout=5).json().get("session_code")
        if not sc:
            log("INCONCLUSIVE: no session_code"); browser.close(); return 2
        tv.goto(f"{TV}/question/{sc}", wait_until="domcontentloaded")

        def snap():
            try:
                route = tv.evaluate("() => location.pathname")
                txt = tv.evaluate("() => document.body.innerText").replace("\n", " ")[:120]
            except Exception:
                return
            timeline.append((route, txt))

        fired = False
        deadline = time.time() + 40
        while time.time() < deadline:
            snap()
            route = timeline[-1][0] if timeline else ""
            if "/minigame/" in route:
                nonlocal_saw = True
            s1, s2 = puck_state(hub, 0), puck_state(hub, 1)

            if "MINIGAME" in s1 or "MINIGAME" in s2:
                if not fired:
                    log("pucks in MINIGAME — firing both as fast as possible")
                    for idx in (0, 1):
                        for label in ("Fire", "Tap", "TAP"):
                            try:
                                puck_row(hub, idx).get_by_role("button", name=label, exact=False).first.click(timeout=1000); break
                            except Exception: continue
                    fired = True
                time.sleep(0.1); continue

            if "PICK CATEGORY" in s1 or "PICK CATEGORY" in s2:
                picker = 0 if "PICK CATEGORY" in s1 else 1
                cats = puck_row(hub, picker).locator("button[title]")
                if cats.count() > 0:
                    try: cats.first.click(force=True, timeout=2500)
                    except Exception: pass
                time.sleep(0.6); continue

            if fired and ("ANSWERING" in s1 or "Q" in s1):
                # We've passed the minigame into the next question.
                for _ in range(6):
                    snap(); time.sleep(0.1)
                break

            time.sleep(0.15)

        browser.close()

    # Analyze the timeline.
    for route, txt in timeline:
        if "/minigame/" in route:
            saw_minigame_route = True
            if "RESULTS" in txt or "+500" in txt or "+200" in txt:
                saw_results_text = True

    log("")
    log("===== TV minigame timeline (route → visible text) =====")
    shown = [t for t in timeline if "/minigame/" in t[0]]
    for route, txt in shown[:25]:
        log(f"   {route.split('/')[-2]}: {txt!r}")
    log("")
    log(f"saw minigame route: {saw_minigame_route}   saw RESULTS panel: {saw_results_text}")
    if saw_minigame_route and not saw_results_text:
        log("RESULT: REPRODUCED — TV showed the minigame but NEVER the results panel")
        return 1
    if not saw_minigame_route:
        log("RESULT: INCONCLUSIVE — TV never on the minigame screen")
        return 2
    log("RESULT: results panel DID show — race not reproduced this run")
    return 0


if __name__ == "__main__":
    sys.exit(run())
