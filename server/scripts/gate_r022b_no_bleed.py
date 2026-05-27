"""Gate for R022b — delayed narration must not bleed past a no-reveal
navigation.

The host voice is scheduled to start 600ms after the question card mounts
(R021 breath). If the screen navigates away DURING that window without a
reveal (match end, lobby cancel, question rotation), the delayed play()
could still fire on the next screen — the voice bleeding in. The fix
tracks the pending timer and clears it on unmount.

This gate forces exactly that race: the instant a question's
load-question response arrives (narration just scheduled, not yet
playing), it POSTs /api/pair/clear, which emits lobby_cancelled and
navigates the TV to the title. It then asserts NO narration play() event
ever fires on a non-/question route.

Gate assertion name: narration-delayed-play-cleared-on-unmount

Proven behaviour: FAIL on pre-fix build (play() fires on '/'), PASS on fix.
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

INIT = r"""
(() => {
  window.__log = [];
  const _play = HTMLAudioElement.prototype.play;
  HTMLAudioElement.prototype.play = function () {
    window.__log.push({ src: this.src || this.currentSrc || '', route: location.pathname, t: Date.now() });
    return _play.apply(this, arguments);
  };
})();
"""


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def is_narr(src: str) -> bool:
    return "/audio/questions/" in src and ".mp3" in src


def puck_row(page: Page, idx: int):
    return page.locator("main > div").nth(idx)


def puck_state(page: Page, idx: int) -> str:
    try:
        return puck_row(page, idx).locator("span.text-cyan-300").first.inner_text(timeout=1500)
    except Exception:
        return ""


def run() -> int:
    requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)
    fired = {"done": False}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        ctx = browser.new_context(viewport={"width": 1600, "height": 900})
        hub = ctx.new_page()
        tv = ctx.new_page()
        tv.add_init_script(INIT)

        def on_resp(resp):
            # The instant a real question (with audio_url) loads, narration
            # has just been scheduled. Navigate away NOW, inside the 600ms
            # pre-play window, by clearing the lobby.
            if fired["done"]:
                return
            if "/api/sp/load-question" in resp.url:
                try:
                    b = resp.json()
                except Exception:
                    return
                if (b.get("question") or {}).get("id") and b.get("audio_url"):
                    fired["done"] = True
                    try:
                        requests.post(f"{BASE}/api/pair/clear", json={}, timeout=3)
                        log(f"question {b['question']['id']} loaded — fired lobby clear inside pre-play window")
                    except Exception as e:
                        log(f"clear failed: {e!r}")

        tv.on("response", on_resp)

        hub.goto(HUB, wait_until="domcontentloaded")
        tv.goto(TV + "/", wait_until="domcontentloaded")
        time.sleep(0.8)
        tv.mouse.click(800, 450)
        time.sleep(0.5)

        puck_row(hub, 0).get_by_role("button", name="Hold 1s").click(); time.sleep(0.5)
        puck_row(hub, 0).locator("button", has_text="Confirm").click(); time.sleep(0.6)
        puck_row(hub, 1).get_by_role("button", name="Hold 1s").click(); time.sleep(0.8)
        puck_row(hub, 0).get_by_role("button", name="Start match").click(); time.sleep(1.2)
        sc = requests.get(f"{BASE}/api/pair/lobby-state", timeout=5).json().get("session_code")
        if not sc:
            log("INCONCLUSIVE: no session_code"); browser.close(); return 2
        tv.goto(f"{TV}/question/{sc}", wait_until="domcontentloaded")

        # Resolve the round-1 category pick so a question loads. Click it on
        # the Hub if it appears; otherwise the R024 timeout will advance it.
        deadline = time.time() + 18
        while time.time() < deadline and not fired["done"]:
            s1 = puck_state(hub, 0)
            if "PICK CATEGORY" in s1 or "PICK CATEGORY" in puck_state(hub, 1):
                picker = 0 if "PICK CATEGORY" in s1 else 1
                cats = puck_row(hub, picker).locator("button[title]")
                if cats.count() > 0:
                    try: cats.first.click(force=True, timeout=2500)
                    except Exception: pass
            time.sleep(0.3)

        if not fired["done"]:
            log("INCONCLUSIVE: never reached a question with audio_url")
            browser.close(); return 2

        # Watch well past the 600ms pre-play window for any leaked play().
        time.sleep(3.0)
        plays = tv.evaluate("() => window.__log || []")
        browser.close()

    narr_plays = [e for e in plays if is_narr(e["src"])]
    bleed = [e for e in narr_plays if "/question/" not in e["route"]]
    log("")
    log(f"narration play() events: {len(narr_plays)}  |  off-question (bleed): {len(bleed)}")
    for e in narr_plays:
        log(f"   play {e['src'].split('/')[-1]} on route {e['route']}")
    if bleed:
        log("RESULT: FAIL — narration play() fired after navigating away (R022b bleed)")
        return 1
    log("RESULT: PASS — no narration leaked past the no-reveal navigation.")
    log("        gate: narration-delayed-play-cleared-on-unmount")
    return 0


if __name__ == "__main__":
    sys.exit(run())
