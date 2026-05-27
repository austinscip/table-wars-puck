"""Verify BULLSEYE is winnable (aiming works) in BOTH Hub variants.

'Bullseye had no results' = firing without aim defaults to quadrant A, so
unless the target is A every fire scores 0 and no winner is awarded. R020
restored aim in Variant B; the VariantA-aim change adds aim pills to the
compact variant too. This drives each variant to the round-2 BULLSEYE,
aims BOTH pucks at the live target, fires, and asserts a real winner
(a 🥇 +500 row in the TV results).

Gate assertion name: bullseye-aim-produces-a-winner (per variant)
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

# VariantB D-pad arrows: ▲=A ▶=B ▼=C ◀=D. VariantA aim pills are letters.
B_ARROW = {"A": "▲", "B": "▶", "C": "▼", "D": "◀"}

CFG = {
    "A": {
        "url": f"{TV}/dev/hub?variant=A",
        "start_btn": "Start match",
        "aim_label": lambda t: t,            # letter pill
        "fire_btn": "Fire", "fire_exact": False,
        "mg_substr": "MINIGAME BULLSEYE",
        "pick_substr": "PICK CATEGORY",
    },
    "B": {
        "url": f"{TV}/dev/hub?variant=B",
        "start_btn": "TAP",
        "aim_label": lambda t: B_ARROW[t],   # arrow
        "fire_btn": "TAP", "fire_exact": True,
        "mg_substr": "mg/BULLSEYE",
        "pick_substr": "pick category",
    },
}


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def puck_row(page: Page, idx: int):
    return page.locator("main > div").nth(idx)


def puck_state(page: Page, idx: int) -> str:
    try:
        return puck_row(page, idx).locator("span.text-cyan-300").first.inner_text(timeout=1500)
    except Exception:
        return ""


def click_category(hub: Page, picker: int) -> None:
    btns = puck_row(hub, picker).locator("button")
    for i in range(btns.count()):
        t = (btns.nth(i).inner_text() or "").strip()
        if t and t not in ("Hold 1s", "Hold 3s", "TAP", "Fire", "×",
                           "▲", "◀", "▶", "▼", "A", "B", "C", "D",
                           "Start match"):
            try:
                btns.nth(i).click(force=True, timeout=2000)
            except Exception:
                pass
            return


def run_variant(p, variant: str) -> bool:
    cfg = CFG[variant]
    requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)
    browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
    ctx = browser.new_context(viewport={"width": 1600, "height": 900})
    hub = ctx.new_page()
    tv = ctx.new_page()
    hub.goto(cfg["url"], wait_until="domcontentloaded")
    tv.goto(TV + "/", wait_until="domcontentloaded")
    time.sleep(0.8)
    tv.mouse.click(800, 450); time.sleep(0.4)

    puck_row(hub, 0).get_by_role("button", name="Hold 1s").click(); time.sleep(0.5)
    puck_row(hub, 0).locator("button", has_text="Confirm").click(); time.sleep(0.6)
    puck_row(hub, 1).get_by_role("button", name="Hold 1s").click(); time.sleep(0.8)
    puck_row(hub, 0).get_by_role("button", name=cfg["start_btn"], exact=True).click(); time.sleep(1.2)
    sc = requests.get(f"{BASE}/api/pair/lobby-state", timeout=5).json().get("session_code")
    if not sc:
        log(f"[{variant}] INCONCLUSIVE: no session_code"); browser.close(); return False
    tv.goto(f"{TV}/question/{sc}", wait_until="domcontentloaded")

    target = None
    deadline = time.time() + 40
    last_dbg = 0.0
    while time.time() < deadline:
        s1, s2 = puck_state(hub, 0), puck_state(hub, 1)
        if time.time() - last_dbg > 1.5:
            log(f"[{variant}] dbg puck1={s1!r} puck2={s2!r}")
            last_dbg = time.time()
        if cfg["mg_substr"] in s1 or cfg["mg_substr"] in s2:
            # Target is in the puck state itself (describe: "...→C").
            mg_state = s1 if cfg["mg_substr"] in s1 else s2
            m = re.search(r"→([ABCD])", mg_state)
            if not m:
                # Fall back to the TV header ("AIM AT C").
                m = re.search(r"AIM AT ([ABCD])", tv.evaluate("() => document.body.innerText"))
            target = m.group(1) if m else None
            break
        if cfg["pick_substr"] in s1 or cfg["pick_substr"] in s2:
            click_category(hub, 0 if cfg["pick_substr"] in s1 else 1)
            time.sleep(1.2); continue
        if s1.startswith(("Q", "ANSWERING")) and s2.startswith(("Q", "ANSWERING")):
            for idx in (0, 1):
                try: puck_row(hub, idx).get_by_role("button", name="A", exact=True).click(force=True, timeout=2000)
                except Exception: pass
            time.sleep(2.0); continue
        time.sleep(0.4)

    if not target:
        log(f"[{variant}] INCONCLUSIVE: never reached BULLSEYE/target"); browser.close(); return False
    log(f"[{variant}] BULLSEYE target = {target}")

    aim = cfg["aim_label"](target)
    for idx in (0, 1):
        try:
            puck_row(hub, idx).get_by_role("button", name=aim, exact=True).first.click(timeout=2000)
        except Exception as e:
            log(f"[{variant}] puck{idx+1} aim '{aim}' failed: {e!r}")
    time.sleep(0.4)
    for idx in (0, 1):
        try:
            puck_row(hub, idx).get_by_role("button", name=cfg["fire_btn"], exact=cfg["fire_exact"]).first.click(timeout=2000)
        except Exception as e:
            log(f"[{variant}] puck{idx+1} fire failed: {e!r}")

    results = ""
    for _ in range(30):
        txt = tv.evaluate("() => document.body.innerText")
        if "RESULTS" in txt:
            results = txt.replace("\n", " ")
            if "+500" in txt:
                break
        time.sleep(0.2)
    browser.close()
    has_winner = "+500" in results or "🥇" in results
    log(f"[{variant}] results: {results[:130]!r}")
    log(f"[{variant}] {'PASS' if has_winner else 'FAIL'} — winner awarded: {has_winner}")
    return has_winner


def run() -> int:
    log("=== bullseye-aim-produces-a-winner (variants A + B) ===")
    with sync_playwright() as p:
        ok_a = run_variant(p, "A")
        ok_b = run_variant(p, "B")
    log("")
    if ok_a and ok_b:
        log("RESULT: PASS — bullseye is winnable by aiming in BOTH variants.")
        return 0
    log(f"RESULT: FAIL — variantA={ok_a} variantB={ok_b}")
    return 1


if __name__ == "__main__":
    sys.exit(run())
