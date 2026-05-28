"""Diagnose R028 — scoreboard shows LEGENDARY for a puck with score 0.

Drives a real match, then GETs /api/sp/final-results/<sc> and compares
the server-returned tier to what derive_tier(total, answered) SHOULD
return. If they disagree, there's a code path that emits the wrong tier.
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


def expected_tier(total: int, answered: int) -> str:
    """Mirror of server's derive_tier — what tier should the API return?"""
    if answered == 0:
        return "NONE"
    avg = total / answered
    if avg >= 700: return "LEGENDARY"
    if avg >= 400: return "EXPERT"
    if avg >= 150: return "AVERAGE"
    return "TIMEOUT"


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
        puck_row(hub, 0).locator("button", has_text="Confirm").click(); time.sleep(0.8)
        puck_row(hub, 1).get_by_role("button", name="Hold 1s").click(); time.sleep(1.2)
        puck_row(hub, 0).get_by_role("button", name="Start match", exact=True).click(); time.sleep(1.2)
        sc = requests.get(f"{BASE}/api/pair/lobby-state", timeout=5).json().get("session_code")
        if not sc:
            log("INCONCLUSIVE: no session_code"); browser.close(); return 2
        tv.goto(f"{TV}/question/{sc}", wait_until="domcontentloaded")

        # Drive the match phase-driven. Puck 1 always picks A. Puck 2
        # never answers (so we can see TIMEOUT-style outcomes).
        deadline = time.time() + 200
        while time.time() < deadline:
            if "/scoreboard/" in tv.evaluate("() => location.pathname"):
                break
            s1, s2 = puck_state(hub, 0), puck_state(hub, 1)
            if "MATCH ENDED" in s1 and "MATCH ENDED" in s2:
                break
            if "PICK CATEGORY" in s1 or "PICK CATEGORY" in s2:
                pd = time.time() + 13
                while time.time() < pd:
                    if ("PICK CATEGORY" not in puck_state(hub, 0)
                            and "PICK CATEGORY" not in puck_state(hub, 1)):
                        break
                    for pidx in (0, 1):
                        btns = puck_row(hub, pidx).locator("button[title]")
                        if btns.count() > 0:
                            try: btns.first.click(force=True, timeout=1200)
                            except Exception: pass
                    time.sleep(0.5)
                time.sleep(1.0); continue
            if "MINIGAME" in s1 or "MINIGAME" in s2:
                # Puck 1 fires; puck 2 doesn't (lets it auto-finish).
                for label in ("Fire", "Tap", "TAP"):
                    try:
                        puck_row(hub, 0).get_by_role("button", name=label, exact=False).first.click(timeout=1000); break
                    except Exception: continue
                time.sleep(10.0); continue
            if "ANSWERING" in s1 and "ANSWERING" in s2:
                # Both pucks answer; one picks A and one picks D — D is
                # almost never the right answer for these questions, so
                # puck 2 ends up with many wrong answers + low total.
                for idx, L in ((0, "A"), (1, "D")):
                    try:
                        puck_row(hub, idx).get_by_role("button", name=L, exact=True).click(force=True, timeout=2000)
                    except Exception: pass
                    time.sleep(0.3)
                time.sleep(2.5); continue
            time.sleep(0.4)

        time.sleep(1.5)
        api = requests.get(f"{BASE}/api/sp/final-results/{sc}", timeout=5).json()
        browser.close()

    log(f"raw API response: {api}")
    log("")
    log("=== server-returned vs expected tier ===")
    mismatch = []
    for p in api.get("players", []):
        total = p["total"]
        answered = p["answered"]
        avg = total / answered if answered else 0
        srv = p["tier"]
        exp = expected_tier(total, answered)
        ok = srv == exp
        log(f"  puck {p['puck_id']}: total={total} answered={answered} avg={avg:.1f}  server='{srv}' expected='{exp}'  {'OK' if ok else 'MISMATCH'}")
        if not ok:
            mismatch.append((p['puck_id'], srv, exp))
    log("")
    if mismatch:
        log(f"RESULT: R028 REPRODUCED — {len(mismatch)} tier mismatch(es).")
        return 1
    log("RESULT: tiers match server math — R028 not reproduced this run.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
