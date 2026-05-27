"""Verify Slice E2 — the Hub virtual puck transitions into MINIGAME
when the server enters a minigame phase, and tap fires correctly.

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


def post(path: str, body=None) -> dict:
    r = requests.post(f"{BASE}{path}", json=body or {}, timeout=5)
    return r.json() if r.text.strip().startswith("{") else {}


def puck_row(page, idx: int):
    return page.locator("main > div").nth(idx)


def puck_state(page, idx: int) -> str:
    try:
        return puck_row(page, idx).locator("span.text-cyan-300").first.inner_text(timeout=1500)
    except Exception:
        return ""


def drive_match_to_round_2(sc: str) -> None:
    """Round 1 pick + Q1 + answers, leaving server ready to enter
    round 2 minigame on the next load-question call."""
    lq = post(f"/api/sp/load-question/{sc}")
    post(f"/api/sp/select-category/{sc}", {
        "puck_id": lq["picker_puck_id"],
        "category_id": lq["offer"][0]["id"],
    })
    lq2 = post(f"/api/sp/load-question/{sc}")
    qid = lq2["question"]["id"]
    # Need puck IDs that Hub uses (1, 2) — but post_answer needs the
    # actual expected_pucks which are from the lobby pair flow (1, 2
    # given Hub's puck rendering).
    post("/api/sp/answer", {"session_code": sc, "puck_id": 1,
                            "question_id": qid, "answer": "A",
                            "response_time_ms": 1000})
    post("/api/sp/answer", {"session_code": sc, "puck_id": 2,
                            "question_id": qid, "answer": "B",
                            "response_time_ms": 1500})
    time.sleep(0.3)


def run() -> int:
    post("/api/pair/clear")
    log("=== E2 Hub verification ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        ctx = browser.new_context(viewport={"width": 1600, "height": 900})
        hub = ctx.new_page()
        hub.goto(HUB, wait_until="domcontentloaded")
        time.sleep(1.5)

        # Pair both pucks
        puck_row(hub, 0).get_by_role("button", name="Hold 1s").click()
        time.sleep(0.5)
        puck_row(hub, 0).locator("button", has_text="Confirm").click()
        time.sleep(0.6)
        puck_row(hub, 1).get_by_role("button", name="Hold 1s").click()
        time.sleep(0.8)
        puck_row(hub, 0).get_by_role("button", name="Start match").click()
        time.sleep(1.2)

        sc = requests.get(f"{BASE}/api/pair/lobby-state").json()["session_code"]
        log(f"sc={sc}")

        # Drive through round 1
        drive_match_to_round_2(sc)
        log("round 1 done; entering round 2 minigame")

        # Trigger round 2 minigame phase
        post(f"/api/sp/load-question/{sc}")

        # Pucks should transition to MINIGAME within ~1.5s
        for _ in range(20):
            s1 = puck_state(hub, 0)
            s2 = puck_state(hub, 1)
            if "MINIGAME" in s1 and "MINIGAME" in s2:
                break
            time.sleep(0.25)
        log(f"after wait: puck1={s1!r} puck2={s2!r}")
        if "MINIGAME" not in s1 or "MINIGAME" not in s2:
            log("FAIL: pucks did not transition to MINIGAME")
            browser.close()
            return 1
        log("PASS: both pucks in MINIGAME state")

        # Tap puck1 to fire — VariantA's universal TAP button at index
        # depends on the rendered controls; the universal "TAP" is in
        # VariantB. VariantA has no universal TAP but Hold 1s/Hold 3s
        # are universal. Actually VariantA does have a TAP button —
        # let's check.
        try:
            # Click the "Tap (lock)" / "TAP" / "Fire" button — VariantA
            # at MINIGAME state renders... let me just query all
            # buttons and look for one with relevant text.
            buttons = puck_row(hub, 0).locator("button").all_inner_texts()
            log(f"puck1 buttons in MINIGAME: {buttons}")
            tap_btn = None
            for b in buttons:
                if b.upper() in ("TAP", "FIRE", "TAP (LOCK)") or "TAP" in b.upper():
                    tap_btn = b
                    break
            if tap_btn:
                puck_row(hub, 0).get_by_role("button", name=tap_btn).first.click(timeout=3000)
                log(f"PASS: clicked puck1 tap button {tap_btn!r}")
            else:
                log(f"FAIL: no tap button found in MINIGAME state: {buttons}")
                browser.close()
                return 1
        except Exception as e:
            log(f"FAIL: couldn't click tap: {e!r}")
            browser.close()
            return 1

        # Fire puck 2 too
        try:
            puck_row(hub, 1).get_by_role("button", name=tap_btn).first.click(timeout=3000)
        except Exception:
            pass
        time.sleep(1.5)

        # Both should have fired; pucks transition out of MINIGAME
        # (server resolved, polling drops them to IN_GAME_IDLE, then
        # next load-question advance triggers Q2 ANSWERING).
        post(f"/api/sp/load-question/{sc}")
        time.sleep(2.0)
        s1 = puck_state(hub, 0)
        s2 = puck_state(hub, 1)
        log(f"after fires + load: puck1={s1!r} puck2={s2!r}")
        if "ANSWERING" not in s1 or "ANSWERING" not in s2:
            log("FAIL: pucks did not transition to ANSWERING after minigame")
            browser.close()
            return 1
        log("PASS: pucks transitioned to ANSWERING after minigame resolved")

        browser.close()
    log("ALL E2 HUB CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(run())
