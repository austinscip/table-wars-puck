"""Verify the BULLSEYE 'no results' chain is resolved by the R020 aim fix.

'Bullseye had no results' happens because firing without aiming defaults
to quadrant A; unless the target is A, every fire misses and scores 0, so
no winner is awarded — the results panel shows only 'no bonus'. R020
restored the Variant B D-pad so a puck can actually aim at the target.

This drives a Variant B match to the round-2 BULLSEYE, reads the target
quadrant, AIMS puck 1 at it via the matching D-pad button, fires, and
asserts the minigame produces a real winner (a +500 bonus row in the TV
results). If aiming were still broken, the target would be missed and no
bonus would be awarded.

Gate assertion name: bullseye-aim-produces-a-winner
Run with sandbox Flask up on :5002.
"""
from __future__ import annotations

import re
import sys
import time

import requests
from playwright.sync_api import sync_playwright, Page


BASE = "http://localhost:5002"
TV = f"{BASE}/tv/speed-pyramid"
HUB = f"{TV}/dev/hub?variant=B"

# VariantB D-pad: ▲=N=A, ▶=E=B, ▼=S=C, ◀=W=D
TARGET_TO_DPAD = {"A": "▲", "B": "▶", "C": "▼", "D": "◀"}


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
        puck_row(hub, 0).get_by_role("button", name="TAP", exact=True).click(); time.sleep(1.2)
        sc = requests.get(f"{BASE}/api/pair/lobby-state", timeout=5).json().get("session_code")
        if not sc:
            log("INCONCLUSIVE: no session_code"); browser.close(); return 2
        tv.goto(f"{TV}/question/{sc}", wait_until="domcontentloaded")

        # Advance to round-2 BULLSEYE.
        target = None
        deadline = time.time() + 30
        while time.time() < deadline:
            s1, s2 = puck_state(hub, 0), puck_state(hub, 1)
            if "mg/BULLSEYE" in s1 or "mg/BULLSEYE" in s2:
                # Read target from the TV ("AIM AT X").
                txt = tv.evaluate("() => document.body.innerText")
                m = re.search(r"AIM AT ([ABCD])", txt)
                target = m.group(1) if m else None
                break
            if "pick category" in s1 or "pick category" in s2:
                picker = 0 if "pick category" in s1 else 1
                btns = puck_row(hub, picker).locator("button")
                for i in range(btns.count()):
                    t = (btns.nth(i).inner_text() or "").strip()
                    if t and t not in ("Hold 1s", "Hold 3s", "TAP", "×", "▲", "◀", "▶", "▼", "A", "B", "C", "D"):
                        try: btns.nth(i).click(force=True, timeout=2000)
                        except Exception: pass
                        break
                time.sleep(1.2); continue
            if s1.startswith("Q") and s2.startswith("Q"):
                for idx in (0, 1):
                    try: puck_row(hub, idx).get_by_role("button", name="A", exact=True).click(force=True, timeout=2000)
                    except Exception: pass
                time.sleep(2.0); continue
            time.sleep(0.4)

        if not target:
            log("INCONCLUSIVE: never reached BULLSEYE or couldn't read target")
            browser.close(); return 2
        log(f"BULLSEYE target = {target}")

        # Aim BOTH pucks at the target via the matching D-pad, then fire.
        dpad = TARGET_TO_DPAD[target]
        for idx in (0, 1):
            try:
                puck_row(hub, idx).get_by_role("button", name=dpad, exact=True).first.click(timeout=2000)
            except Exception as e:
                log(f"  puck{idx+1} aim click failed: {e!r}")
        time.sleep(0.4)
        for idx in (0, 1):
            try:
                puck_row(hub, idx).get_by_role("button", name="TAP", exact=True).click(timeout=2000)
            except Exception as e:
                log(f"  puck{idx+1} fire failed: {e!r}")

        # Watch the TV results.
        results_txt = ""
        for _ in range(30):
            txt = tv.evaluate("() => document.body.innerText")
            if "RESULTS" in txt:
                results_txt = txt.replace("\n", " ")
                if "+500" in txt:
                    break
            time.sleep(0.2)
        browser.close()

    log(f"results text: {results_txt[:160]!r}")
    has_winner = "+500" in results_txt or "🥇" in results_txt
    log("")
    if has_winner:
        log("RESULT: PASS — aiming at the target produced a real winner (+500).")
        log("        gate: bullseye-aim-produces-a-winner")
        return 0
    log("RESULT: FAIL — no winner awarded even after aiming at the target.")
    return 1


if __name__ == "__main__":
    sys.exit(run())
