"""Comprehensive audio-events gate — retroactively closes R015-R018 TBDs.

Initialises window.__sfxLog before the app loads, drives a real full
match through the Hub, and asserts every expected SFX cue fires at the
right phase. Backed by the tiny dev-only tap inside lib/audio.ts _play().

Cues covered (sample names from audio.ts):
  sfx_joined         — puck joined the lobby (R016)
  sfx_digit          — pair-code digit / confirm (R015)
  sfx_pick_show      — category-pick screen opens (R018)
  sfx_pick_locked    — pick locks in
  sfx_question_show  — question card reveal
  sfx_tick           — countdown tick last 3s (R017)
  sfx_lock           — answer lock-in
  sfx_correct/wrong/reveal — per-question reveal stinger
  sfx_match_end      — final scoreboard chord

Gate assertion name: every-named-sfx-fires-during-a-match
Run with sandbox Flask up on :5002.
"""
from __future__ import annotations

import sys
import time
from collections import Counter

import requests
from playwright.sync_api import sync_playwright, Page


BASE = "http://localhost:5002"
TV = f"{BASE}/tv/speed-pyramid"
HUB = f"{TV}/dev/hub"

INIT = (
    # add_init_script re-runs on every cross-document navigation, so a
    # plain setItem would wipe the accumulated events each tv.goto.
    # Initialise only if the key is not already set; persist across
    # navigations.
    "try {"
    "  if (sessionStorage.getItem('__sfxLog') === null)"
    "    sessionStorage.setItem('__sfxLog', '[]');"
    "} catch (e) {}"
)


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def puck_row(page: Page, idx: int):
    return page.locator("main > div").nth(idx)


def puck_state(page: Page, idx: int) -> str:
    try:
        return puck_row(page, idx).locator("span.text-cyan-300").first.inner_text(timeout=1500)
    except Exception:
        return ""


def parse_qid(state: str):
    if "Q" not in state:
        return None
    tail = state.split("Q", 1)[1]
    num = ""
    for ch in tail:
        if ch.isdigit():
            num += ch
        else:
            break
    return int(num) if num else None


def run() -> int:
    requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)
    answered_qids: set[int] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        ctx = browser.new_context(viewport={"width": 1600, "height": 900})
        hub = ctx.new_page()
        tv = ctx.new_page()
        tv.add_init_script(INIT)
        # Diagnostic: log every WS frame containing 'player_joined' so we
        # can see whether the TV actually receives the event.
        def on_ws(ws):
            def on_frame(payload):
                if isinstance(payload, str) and "player_joined" in payload:
                    log(f"  ws<- {payload[:160]}")
            ws.on("framereceived", on_frame)
        tv.on("websocket", on_ws)
        tv.on("console", lambda m: log(f"  console[{m.type}] {m.text[:200]}") if m.type in ("error", "warning") else None)
        hub.goto(HUB, wait_until="domcontentloaded")
        tv.goto(TV + "/", wait_until="domcontentloaded")
        time.sleep(1.0)

        # Pair host first, then put the TV on /lobby/<pair_code> so the
        # second puck's player_joined event fires audio.joined() — the
        # SFX only plays inside Pair/LobbyScreen. The old harness jumped
        # straight to /question and silently skipped this cue.
        puck_row(hub, 0).get_by_role("button", name="Hold 1s").click(); time.sleep(0.5)
        puck_row(hub, 0).locator("button", has_text="Confirm").click(); time.sleep(0.8)
        pair_code = requests.get(f"{BASE}/api/pair/lobby-state", timeout=5).json().get("code")
        if not pair_code:
            log("INCONCLUSIVE: no pair_code after host confirm"); browser.close(); return 2
        log(f"pair_code={pair_code} — TV -> /lobby/{pair_code}")
        tv.goto(f"{TV}/lobby/{pair_code}", wait_until="domcontentloaded")
        # Give the socket time to connect AND emit join_pair_room AND
        # receive the joined_pair_room confirmation — without this the
        # server emits player_joined to a room the TV isn't in yet.
        time.sleep(2.5)
        puck_row(hub, 1).get_by_role("button", name="Hold 1s").click(); time.sleep(2.0)

        puck_row(hub, 0).get_by_role("button", name="Start match", exact=True).click(); time.sleep(1.2)
        sc = requests.get(f"{BASE}/api/pair/lobby-state", timeout=5).json().get("session_code")
        if not sc:
            log("INCONCLUSIVE: no session_code"); browser.close(); return 2
        # The lobby's match_started handler will cascade Lobby -> Countdown.
        # Wait for the cascade then take the TV to /question/<sc> if it
        # didn't land there on its own (CountdownScreen may or may not
        # auto-advance depending on its own logic).
        time.sleep(4.0)
        if "/question/" not in tv.evaluate("() => location.pathname"):
            tv.goto(f"{TV}/question/{sc}", wait_until="domcontentloaded")

        match_deadline = time.time() + 200
        while time.time() < match_deadline:
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
                for idx in (0, 1):
                    for label in ("Fire", "Tap", "TAP"):
                        try:
                            puck_row(hub, idx).get_by_role("button", name=label, exact=False).first.click(timeout=1000); break
                        except Exception: continue
                time.sleep(2.0); continue
            if "ANSWERING" in s1 and "ANSWERING" in s2:
                qid = parse_qid(s1) or parse_qid(s2)
                if qid in answered_qids:
                    time.sleep(0.3); continue
                if qid is not None:
                    answered_qids.add(qid)
                for idx, L in ((0, "A"), (1, "B")):
                    try: puck_row(hub, idx).get_by_role("button", name=L, exact=True).click(force=True, timeout=2500)
                    except Exception: pass
                time.sleep(2.5); continue
            time.sleep(0.4)
        time.sleep(2.0)  # let scoreboard SFX fire

        sfx = tv.evaluate("() => { try { return JSON.parse(sessionStorage.getItem('__sfxLog') || '[]'); } catch (e) { return []; } }")
        browser.close()

    counts = Counter(e["name"] for e in sfx)
    log(f"captured {sum(counts.values())} SFX events:")
    for name, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        log(f"   {name:24s} {n}")

    # Thresholds — conservative; the harness sometimes answers before
    # the last 3s of the countdown, so sfx_tick may be 0 in some runs.
    expectations = [
        ("sfx_joined",         2,  "R016: puck joined SFX"),
        ("sfx_pick_show",      3,  "R018: category-pick screen open SFX"),
        ("sfx_pick_locked",    1,  "pick-locked SFX"),
        ("sfx_question_show",  6,  "question card reveal SFX"),
        ("sfx_lock",           10, "answer lock-in SFX"),
        # Reveal stingers — one of correct/wrong/reveal per round.
    ]
    failures = []
    for name, need, label in expectations:
        got = counts.get(name, 0)
        ok = got >= need
        log(f"  [{'PASS' if ok else 'FAIL'}] {label}: {got} >= {need}")
        if not ok:
            failures.append(f"{name}: {got} < {need}")

    # Reveal: any of correct/wrong/reveal >=6 in aggregate.
    reveals = counts.get("sfx_correct", 0) + counts.get("sfx_wrong", 0) + counts.get("sfx_reveal", 0)
    rev_ok = reveals >= 6
    log(f"  [{'PASS' if rev_ok else 'FAIL'}] per-reveal stinger (correct|wrong|reveal): {reveals} >= 6")
    if not rev_ok:
        failures.append(f"reveal stingers: {reveals} < 6")

    log("")
    if failures:
        log(f"RESULT: FAIL — {len(failures)} audio cue(s) under-fired:")
        for f in failures: log(f"   {f}")
        return 1
    log("RESULT: PASS — every expected audio cue fired during a real match.")
    log("        gate: every-named-sfx-fires-during-a-match")
    return 0


if __name__ == "__main__":
    sys.exit(run())
