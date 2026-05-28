"""Screenshot every TV phase so I (or the user) can see the actual
current visual state of the product. Saves PNGs under /tmp/sp_tour/.

Drives a real match through the Hub and captures the TV at each phase:
title, lobby, countdown (best-effort), category-pick, minigame-bullseye,
question-answering, question-reveal, scoreboard.
"""
from __future__ import annotations

import os
import sys
import time

import requests
from playwright.sync_api import sync_playwright, Page


BASE = "http://localhost:5002"
TV = f"{BASE}/tv/speed-pyramid"
HUB = f"{TV}/dev/hub"
OUT = "/tmp/sp_tour"


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def puck_row(page: Page, idx: int):
    return page.locator("main > div").nth(idx)


def puck_state(page: Page, idx: int) -> str:
    try:
        return puck_row(page, idx).locator("span.text-cyan-300").first.inner_text(timeout=1500)
    except Exception:
        return ""


def shot(page: Page, name: str) -> str:
    path = os.path.join(OUT, f"{name}.png")
    page.screenshot(path=path, full_page=True)
    log(f"  saved {path}")
    return path


def run() -> int:
    os.makedirs(OUT, exist_ok=True)
    requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
        hub = ctx.new_page()
        tv = ctx.new_page()
        hub.goto(HUB, wait_until="domcontentloaded")
        tv.goto(TV + "/", wait_until="domcontentloaded")
        time.sleep(1.0)
        shot(tv, "01_title")

        puck_row(hub, 0).get_by_role("button", name="Hold 1s").click(); time.sleep(0.5)
        puck_row(hub, 0).locator("button", has_text="Confirm").click(); time.sleep(0.8)
        pair_code = requests.get(f"{BASE}/api/pair/lobby-state", timeout=5).json().get("code")
        tv.goto(f"{TV}/lobby/{pair_code}", wait_until="domcontentloaded")
        time.sleep(2.0)
        shot(tv, "02_lobby_host_only")
        puck_row(hub, 1).get_by_role("button", name="Hold 1s").click(); time.sleep(2.0)
        shot(tv, "03_lobby_both_joined")

        puck_row(hub, 0).get_by_role("button", name="Start match", exact=True).click()
        time.sleep(1.0)
        # Try to catch countdown — it's brief
        for _ in range(8):
            if "/countdown/" in tv.evaluate("() => location.pathname"):
                shot(tv, "04_countdown")
                break
            time.sleep(0.3)
        sc = requests.get(f"{BASE}/api/pair/lobby-state", timeout=5).json().get("session_code")
        # Make sure we land on /question once countdown ends
        time.sleep(3.0)
        path = tv.evaluate("() => location.pathname")
        log(f"after countdown route: {path}")

        captured = {"category_pick": False, "minigame": False, "answering": False, "reveal": False, "scoreboard": False}
        deadline = time.time() + 90
        while time.time() < deadline:
            route = tv.evaluate("() => location.pathname")
            if "/scoreboard/" in route and not captured["scoreboard"]:
                shot(tv, "10_scoreboard")
                captured["scoreboard"] = True
                break
            if "/category-pick/" in route and not captured["category_pick"]:
                shot(tv, "05_category_pick")
                captured["category_pick"] = True
            if "/minigame/" in route and not captured["minigame"]:
                shot(tv, "06_minigame_bullseye")
                captured["minigame"] = True
            if "/question/" in route:
                s1, s2 = puck_state(hub, 0), puck_state(hub, 1)
                if "ANSWERING" in s1 and "ANSWERING" in s2 and not captured["answering"]:
                    time.sleep(0.4)
                    shot(tv, "07_question_answering")
                    captured["answering"] = True

            # Drive
            s1, s2 = puck_state(hub, 0), puck_state(hub, 1)
            if "PICK CATEGORY" in s1 or "PICK CATEGORY" in s2:
                for pidx in (0, 1):
                    btns = puck_row(hub, pidx).locator("button[title]")
                    if btns.count() > 0:
                        try: btns.first.click(force=True, timeout=1200)
                        except Exception: pass
                time.sleep(1.5); continue
            if "MINIGAME" in s1 or "MINIGAME" in s2:
                for idx in (0, 1):
                    for label in ("Fire", "TAP"):
                        try: puck_row(hub, idx).get_by_role("button", name=label, exact=False).first.click(timeout=1000); break
                        except Exception: continue
                time.sleep(2.0); continue
            if "ANSWERING" in s1 and "ANSWERING" in s2:
                for idx, L in ((0, "A"), (1, "A")):  # both correct(ish)
                    try: puck_row(hub, idx).get_by_role("button", name=L, exact=True).click(force=True, timeout=2500)
                    except Exception: pass
                time.sleep(1.0)
                if not captured["reveal"]:
                    shot(tv, "08_question_reveal")
                    captured["reveal"] = True
                time.sleep(2.0)
                continue
            time.sleep(0.3)

        browser.close()

    print(f"\nscreenshots in {OUT}/:")
    for f in sorted(os.listdir(OUT)):
        print(f"  {OUT}/{f}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
