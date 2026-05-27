"""R022 ground-truth verification — does narration voice bleed into the
next screen?

Detection is ground-truth without the capture rig that broke the earlier
version: we patch HTMLAudioElement.play/pause to log events and expose a
per-element probe of {src, currentTime, paused, ended}. An element whose
currentTime is ACTIVELY ADVANCING (delta > 0, not paused, not ended) is
producing audio output. R022 is live if a narration MP3
(.../audio/questions/q_*.mp3) advances its clock while the TV route is
not /question/*.

(An earlier version routed every <audio> through createMediaElementSource
into a MediaRecorder to record real sound. That routing suppressed
playback/detection and produced a false 0-narration reading. Recording is
not needed to detect bleed — clock advancement off-route is enough — so
it's dropped here. proof_audio_capture.py still proves recording is
possible for content/transcription checks when those are needed.)

Honest gating:
  - If narration never played at all, return INCONCLUSIVE (exit 2) — we
    cannot certify the bleed is fixed.
  - If a narration clock advances off /question, FAIL (exit 1).
  - Otherwise PASS, reporting how many rounds actually exercised narration.

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
HUB = f"{TV}/dev/hub"

INIT = r"""
(() => {
  window.__log = [];
  window.__els = new Set();
  const _play = HTMLAudioElement.prototype.play;
  const _pause = HTMLAudioElement.prototype.pause;
  HTMLAudioElement.prototype.play = function () {
    window.__els.add(this);
    window.__log.push({ a: 'play', src: this.src || this.currentSrc || '', route: location.pathname, t: Date.now() });
    return _play.apply(this, arguments);
  };
  HTMLAudioElement.prototype.pause = function () {
    window.__log.push({ a: 'pause', src: this.src || this.currentSrc || '', route: location.pathname, t: Date.now() });
    return _pause.apply(this, arguments);
  };
  window.__probe = () => {
    const els = [];
    window.__els.forEach((el) => els.push({
      src: el.src || el.currentSrc || '', ct: el.currentTime,
      paused: el.paused, ended: el.ended,
    }));
    return { route: location.pathname, els: els };
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


class Tracker:
    def __init__(self, tv: Page):
        self.tv = tv
        self.last_ct: dict[str, float] = {}
        self.violations: list[dict] = []
        self.samples = 0

    def _snap(self):
        try:
            return self.tv.evaluate("() => window.__probe ? window.__probe() : null")
        except Exception:
            return None

    def sample(self) -> None:
        snap = self._snap()
        if not snap:
            return
        self.samples += 1
        on_q = bool(re.search(r"/question/", snap["route"]))
        for el in snap["els"]:
            src = el["src"]
            if not is_narr(src):
                continue
            prev = self.last_ct.get(src)
            self.last_ct[src] = el["ct"]
            advancing = (prev is not None and el["ct"] - prev > 0.02
                         and not el["paused"] and not el["ended"])
            if advancing and not on_q:
                self.violations.append({
                    "route": snap["route"], "src": src.split("/")[-1],
                    "ct": round(el["ct"], 2), "t": time.strftime("%H:%M:%S"),
                })

    def watch(self, seconds: float, interval: float = 0.1) -> None:
        end = time.time() + seconds
        while time.time() < end:
            self.sample()
            time.sleep(interval)

    def narration_playing(self) -> bool:
        snap = self._snap()
        if not snap:
            return False
        for el in snap["els"]:
            if is_narr(el["src"]) and not el["paused"] and not el["ended"] and el["ct"] > 0.05:
                return True
        return False

    def wait_for_narration(self, timeout_s: float) -> bool:
        end = time.time() + timeout_s
        while time.time() < end:
            self.sample()
            if self.narration_playing():
                return True
            time.sleep(0.1)
        return False


def run() -> int:
    requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)
    log("=== R022 ground-truth bleed verification ===")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        ctx = browser.new_context(viewport={"width": 1600, "height": 900})
        hub = ctx.new_page()
        tv = ctx.new_page()
        tv.add_init_script(INIT)
        hub.goto(HUB, wait_until="domcontentloaded")
        tv.goto(TV + "/", wait_until="domcontentloaded")
        time.sleep(0.8)
        tv.mouse.click(800, 450)
        time.sleep(0.6)

        trk = Tracker(tv)
        puck_row(hub, 0).get_by_role("button", name="Hold 1s").click(); time.sleep(0.5)
        puck_row(hub, 0).locator("button", has_text="Confirm").click(); time.sleep(0.6)
        puck_row(hub, 1).get_by_role("button", name="Hold 1s").click(); time.sleep(0.8)
        puck_row(hub, 0).get_by_role("button", name="Start match").click(); time.sleep(1.2)
        sc = requests.get(f"{BASE}/api/pair/lobby-state", timeout=5).json().get("session_code")
        if not sc:
            log("FAIL early: no session_code"); browser.close(); return 1
        log(f"sc={sc} -> TV /question/{sc}")
        tv.goto(f"{TV}/question/{sc}", wait_until="domcontentloaded")
        trk.watch(1.0)

        rounds_with_narration = 0
        for rnd in range(7):
            for _ in range(10):
                trk.sample()
                s1, s2 = puck_state(hub, 0), puck_state(hub, 1)
                if "MATCH ENDED" in s1 and "MATCH ENDED" in s2:
                    break
                if "PICK CATEGORY" in s1 or "PICK CATEGORY" in s2:
                    picker = 0 if "PICK CATEGORY" in s1 else 1
                    cats = puck_row(hub, picker).locator("button[title]")
                    if cats.count() > 0:
                        try: cats.first.click(force=True, timeout=3000)
                        except Exception: pass
                    trk.watch(1.5); continue
                if "MINIGAME" in s1 or "MINIGAME" in s2:
                    for idx in (0, 1):
                        for label in ("Fire", "Tap", "TAP"):
                            try:
                                puck_row(hub, idx).get_by_role("button", name=label, exact=False).first.click(timeout=1200); break
                            except Exception: continue
                    trk.watch(2.2); continue
                if "ANSWERING" in s1 and "ANSWERING" in s2:
                    # Wait for the host to actually start reading, THEN answer
                    # both fast — forces reveal + navigation mid-narration.
                    if trk.wait_for_narration(timeout_s=5.0):
                        rounds_with_narration += 1
                        log(f"  round {rnd+1}: narration playing — answering both fast")
                    else:
                        log(f"  round {rnd+1}: narration never started (404/missing?) — answering")
                    for idx, letter in ((0, "A"), (1, "B")):
                        try:
                            puck_row(hub, idx).get_by_role("button", name=letter, exact=True).click(timeout=2500, force=True)
                        except Exception: pass
                    trk.watch(4.5)  # watch hard across reveal + navigation
                    break
                trk.watch(0.5)

        trk.watch(3.0)
        log(f"final route: {tv.evaluate('() => location.pathname')}")
        events = tv.evaluate("() => window.__log || []")
        browser.close()

    narr_plays = len([e for e in events if e["a"] == "play" and is_narr(e["src"])])
    log(f"samples={trk.samples}  narration play events={narr_plays}  "
        f"rounds with narration={rounds_with_narration}")

    log("")
    if narr_plays == 0:
        log("RESULT: INCONCLUSIVE — narration never played; cannot certify (exit 2)")
        return 2
    if trk.violations:
        log(f"RESULT: FAIL — narration clock advanced off /question on "
            f"{len(trk.violations)} samples (R022 LIVE):")
        for v in trk.violations[:10]:
            log(f"   {v['t']} route={v['route']} narration={v['src']} ct={v['ct']}s")
        return 1
    log(f"RESULT: PASS — narration played in {rounds_with_narration} round(s) "
        f"({narr_plays} play events) and NEVER advanced off /question.")
    log(f"        R022 bleed is genuinely not occurring.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
