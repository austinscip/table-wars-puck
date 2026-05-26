"""Verify Slice E1 — the Hub virtual puck transitions into
CATEGORY_PICKING when the server enters a pick phase, and the picker
puck's pickCategory action locks the choice.

Run with sandbox Flask up on :5002 + dist built with VITE_DEV_TOOLS=1.
"""
from __future__ import annotations

import sys
import time

import requests
from playwright.sync_api import sync_playwright


BASE = "http://localhost:5002"
HUB = f"{BASE}/tv/speed-pyramid/dev/hub"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def post(path: str, body: dict | None = None) -> dict:
    r = requests.post(f"{BASE}{path}", json=body or {}, timeout=5)
    return r.json() if r.text.strip().startswith("{") else {}


def puck_row(page, idx: int):
    return page.locator("main > div").nth(idx)


def puck_state(page, idx: int) -> str:
    try:
        return puck_row(page, idx).locator("span.text-cyan-300").first.inner_text(timeout=1500)
    except Exception:
        return ""


def run() -> int:
    post("/api/pair/clear")
    log("=== E1 Hub verification ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        ctx = browser.new_context(viewport={"width": 1600, "height": 900})
        hub = ctx.new_page()
        hub.goto(HUB, wait_until="domcontentloaded")
        time.sleep(1.5)

        # Pair both pucks via the Hub UI so we're testing the real path.
        puck_row(hub, 0).get_by_role("button", name="Hold 1s").click()
        time.sleep(0.5)
        puck_row(hub, 0).locator("button", has_text="Confirm").click()
        time.sleep(0.6)
        puck_row(hub, 1).get_by_role("button", name="Hold 1s").click()
        time.sleep(0.8)
        puck_row(hub, 0).get_by_role("button", name="Start match").click()
        time.sleep(1.2)
        log(f"after start: puck1={puck_state(hub, 0)!r} puck2={puck_state(hub, 1)!r}")

        # In the real flow the TV (mounted at /question/<sc>) calls
        # load-question, which opens the server's pick phase. The Hub
        # NEVER calls load-question (ADR-0002 — pucks are read-only
        # against round transitions). Simulate the TV here with a
        # direct REST call so the pick phase opens.
        sc = requests.get(f"{BASE}/api/pair/lobby-state").json().get("session_code")
        log(f"sc={sc} — triggering pick phase via load-question (mimics TV)")
        post(f"/api/sp/load-question/{sc}")

        # Polling should transition pucks into CATEGORY_PICKING within
        # ~1.5s (Hub polls match-state every 500ms once in-game).
        for _ in range(20):
            s1 = puck_state(hub, 0)
            s2 = puck_state(hub, 1)
            if "PICK" in s1 and "PICK" in s2:
                break
            time.sleep(0.25)
        log(f"after CATEGORY_PICKING wait: puck1={s1!r} puck2={s2!r}")
        if "PICK" not in s1 or "PICK" not in s2:
            log("FAIL: pucks did not transition to PICK CATEGORY state")
            browser.close()
            return 1
        log("PASS: both pucks in PICK state")

        # Find the category buttons in puck1's row. VariantA renders
        # state.offer with emoji + name slice as button labels.
        cat_buttons = puck_row(hub, 0).locator("button").all()
        log(f"puck1 visible buttons: {[b.inner_text(timeout=500) for b in cat_buttons][:8]}")
        # Click the second category offer. The picker is puck901 in
        # round 1 (Hub renders that as the row clicked).
        try:
            # Find first category button (Variant A renders as emoji + name)
            # The picker is puck1 (id=1 in Hub's puck list which maps to
            # PUCK_COLORS[1] = blue). So clicking on puck_row(0) should
            # land us on the picker.
            picker_row = puck_row(hub, 0)
            # Buttons in PICK state per VariantA:
            # universal: Hold 1s, Hold 3s, ×
            # state: <emoji> <name-slice> (3 of them)
            # Get all buttons; category buttons are after Hold 3s.
            all_btns = picker_row.locator("button").all_inner_texts()
            log(f"all picker_row buttons: {all_btns}")
            # Find a button that looks like a category (has emoji prefix or just isn't a known control).
            controls = {"Hold 1s", "Hold 3s", "×", "Tap (lock)"}
            cat_choices = [b for b in all_btns if b not in controls and "Confirm" not in b]
            log(f"category choices: {cat_choices}")
            if not cat_choices:
                log("FAIL: no category buttons rendered in PICK state")
                browser.close()
                return 1
            # Click the first category
            picker_row.get_by_role("button", name=cat_choices[0], exact=False).click(timeout=3000)
            log(f"PASS: clicked category {cat_choices[0]!r}")
        except Exception as e:
            log(f"FAIL: couldn't click category: {e!r}")
            browser.close()
            return 1

        # After pick, server emits category_picked, puck1 should
        # transition out of PICK to ANSWERING within ~1s once load-question
        # fires (REST drives that, since the test isn't running TV).
        sc = requests.get(f"{BASE}/api/pair/lobby-state").json().get("session_code")
        time.sleep(0.5)
        post(f"/api/sp/load-question/{sc}")  # drive Q1
        time.sleep(1.5)
        s1 = puck_state(hub, 0)
        s2 = puck_state(hub, 1)
        log(f"after pick + load: puck1={s1!r} puck2={s2!r}")
        if "ANSWERING" not in s1 or "ANSWERING" not in s2:
            log("FAIL: pucks did not transition to ANSWERING after pick")
            browser.close()
            return 1
        log("PASS: pucks transitioned to ANSWERING after pick")

        browser.close()
    log("ALL E1 HUB CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(run())
