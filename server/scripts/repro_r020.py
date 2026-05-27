"""R020 reproduction — VariantB BULLSEYE minigame D-pad aim controls.

Drives the Hub in Variant B (the "game controller" layout — the one a
player actually uses) through real clicks: pair 2 pucks, start, answer
round 1, then reach the round-2 BULLSEYE minigame and click the ▶
D-pad button to aim.

R020: the D-pad (◀ ▲ ▶ ▼) is `disabled` during MINIGAME because the
variant computes `tiltActive = state.kind === 'IN_GAME_ANSWERING'`,
which excludes minigames. So clicking ▶ does nothing — no
/api/sp/minigame/preview POST fires and the player cannot aim.

PASS condition: clicking ▶ during a BULLSEYE minigame fires a
/api/sp/minigame/preview POST (quadrant B). Before the fix this FAILS;
after the fix it PASSES.

Run with sandbox Flask up on :5002.
"""
from __future__ import annotations

import sys
import time

import requests
from playwright.sync_api import sync_playwright, Page


BASE = "http://localhost:5002"
TV = f"{BASE}/tv/speed-pyramid"
HUB = f"{TV}/dev/hub?variant=B"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def puck_row(page: Page, idx: int):
    return page.locator("main > div").nth(idx)


def puck_state(page: Page, idx: int) -> str:
    try:
        return puck_row(page, idx).locator("span.text-cyan-300").first.inner_text(timeout=1500)
    except Exception:
        return ""


def run() -> int:
    requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)
    preview_posts: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--autoplay-policy=no-user-gesture-required"],
        )
        ctx = browser.new_context(viewport={"width": 1600, "height": 900})
        hub = ctx.new_page()
        tv = ctx.new_page()

        def on_req(req):
            if "/api/sp/minigame/preview" in req.url and req.method == "POST":
                try:
                    import json as _j
                    preview_posts.append(_j.loads(req.post_data or "{}"))
                except Exception:
                    preview_posts.append({})

        hub.on("request", on_req)

        hub.goto(HUB, wait_until="domcontentloaded")
        tv.goto(TV + "/", wait_until="domcontentloaded")
        time.sleep(1.5)

        # ===== PAIR (Variant B: host starts via TAP, no Start button) =====
        log("pairing 2 pucks (variant B)")
        puck_row(hub, 0).get_by_role("button", name="Hold 1s").click()
        time.sleep(0.6)
        puck_row(hub, 0).locator("button", has_text="Confirm").click()
        time.sleep(0.6)
        puck_row(hub, 1).get_by_role("button", name="Hold 1s").click()
        time.sleep(0.8)
        # Host start = TAP while LOBBY_WAITING + is_host.
        puck_row(hub, 0).get_by_role("button", name="TAP", exact=True).click()
        time.sleep(1.5)

        sc = requests.get(f"{BASE}/api/pair/lobby-state", timeout=5).json().get("session_code")
        if not sc:
            log("FAIL early: no session_code after match start")
            browser.close()
            return 1
        log(f"sc={sc} — pointing TV to /question/{sc}")
        tv.goto(f"{TV}/question/{sc}", wait_until="domcontentloaded")
        time.sleep(1.5)

        # ===== advance until round-2 BULLSEYE minigame =====
        found_minigame = False
        for attempt in range(40):
            s1 = puck_state(hub, 0)
            s2 = puck_state(hub, 1)
            log(f"  attempt {attempt}: puck1={s1!r} puck2={s2!r}")

            if "mg/BULLSEYE" in s1 or "mg/BULLSEYE" in s2:
                found_minigame = True
                break

            if "pick category" in s1 or "pick category" in s2:
                picker = 0 if "pick category" in s1 else 1
                cats = puck_row(hub, picker).locator("button").filter(has_text="").all()
                # Category buttons live in the inline picker; click the first
                # that isn't a control button by matching emoji-prefixed text.
                btns = puck_row(hub, picker).locator("button")
                clicked = False
                for i in range(btns.count()):
                    txt = (btns.nth(i).inner_text() or "").strip()
                    if txt and txt not in ("Hold 1s", "Hold 3s", "TAP", "×",
                                           "▲", "◀", "▶", "▼", "A", "B", "C", "D"):
                        try:
                            btns.nth(i).click(force=True, timeout=2000)
                            clicked = True
                            break
                        except Exception:
                            pass
                log(f"  picked category on puck{picker+1}: {clicked}")
                time.sleep(1.5)
                continue

            if s1.startswith("Q") and s2.startswith("Q"):
                log("  answering Q1 — clicking A on both pucks")
                for idx in (0, 1):
                    try:
                        puck_row(hub, idx).get_by_role("button", name="A", exact=True).click(
                            force=True, timeout=2500)
                    except Exception as e:
                        log(f"  WARN puck{idx+1} A click: {e!r}")
                    time.sleep(0.3)
                time.sleep(2.5)
                continue

            time.sleep(0.5)

        if not found_minigame:
            log("RESULT: FAIL — never reached BULLSEYE minigame (setup problem)")
            browser.close()
            return 2

        # ===== R020: click ▶ D-pad to aim during BULLSEYE =====
        log("at BULLSEYE minigame — clicking ▶ D-pad on puck1 to aim")
        preview_posts.clear()
        btn = puck_row(hub, 0).get_by_role("button", name="▶", exact=True).first
        disabled = btn.is_disabled()
        log(f"  ▶ button disabled attribute = {disabled}")
        try:
            btn.click(force=True, timeout=2500)
        except Exception as e:
            log(f"  ▶ click raised: {e!r}")
        time.sleep(1.2)

        hub.screenshot(path="/tmp/r020_hub.png", full_page=True)
        log(f"  preview POSTs after click: {preview_posts}")

        ok = len(preview_posts) > 0
        log("")
        if ok:
            log("RESULT: PASS — ▶ D-pad fired /api/sp/minigame/preview (aim works)")
        else:
            log("RESULT: FAIL — ▶ D-pad did NOT fire a preview POST (R020 present)")
        browser.close()
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
