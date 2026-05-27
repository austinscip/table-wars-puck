"""R022 TRUE verification — does narration voice bleed into the next screen?

Rebuilt on the proven audio-capture primitive (see proof_audio_capture.py)
with honest gating. The prior version logged only that play() was called
and reported PASS with ZERO narration events — a false green. This one:

  1. RECORDS the tab's real audio (HTMLAudioElement -> Web Audio ->
     MediaRecorder) so we can prove sound actually happened and keep the
     artifact for inspection/transcription.
  2. Instruments every <audio> element and exposes its live
     {src, currentTime, paused, ended} so Python can detect an element
     that is ACTIVELY ADVANCING its playback clock (= producing sound).
  3. Drives a real Hub match; in each answer round it WAITS for narration
     to actually start playing before answering both pucks fast — the
     exact condition that makes the host voice bleed past the reveal.
  4. Ground-truth bleed test: a narration MP3 must NEVER have an advancing
     playback clock while the TV route is not /question/*.
  5. Honest verdict: if narration never played at all, INCONCLUSIVE (exit
     2) — we cannot certify anything. Never PASS on no evidence.

Run with sandbox Flask up on :5002.
"""
from __future__ import annotations

import base64
import os
import re
import subprocess
import sys
import tempfile
import time

import requests
from playwright.sync_api import sync_playwright, Page


BASE = "http://localhost:5002"
TV = f"{BASE}/tv/speed-pyramid"
HUB = f"{TV}/dev/hub"

# Capture rig + per-element probe, installed before the app loads.
INIT = r"""
(() => {
  const AC = window.AudioContext || window.webkitAudioContext;
  const ctx = new AC();
  const dest = ctx.createMediaStreamDestination();
  const chunks = [];
  const rec = new MediaRecorder(dest.stream, { mimeType: 'audio/webm' });
  rec.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
  rec.start(200);

  window.__els = new Set();
  window.__log = [];
  const seen = new WeakSet();
  const _play = HTMLAudioElement.prototype.play;
  const _pause = HTMLAudioElement.prototype.pause;
  HTMLAudioElement.prototype.play = function () {
    window.__els.add(this);
    if (!seen.has(this)) {
      seen.add(this);
      try {
        const s = ctx.createMediaElementSource(this);
        s.connect(dest); s.connect(ctx.destination);
      } catch (e) {}
    }
    if (ctx.state === 'suspended') ctx.resume();
    window.__log.push({ a: 'play', src: this.src || this.currentSrc || '', route: location.pathname, t: Date.now() });
    return _play.apply(this, arguments);
  };
  HTMLAudioElement.prototype.pause = function () {
    window.__log.push({ a: 'pause', src: this.src || this.currentSrc || '', route: location.pathname, t: Date.now() });
    return _pause.apply(this, arguments);
  };
  window.__probe = () => {
    const route = location.pathname;
    const els = [];
    window.__els.forEach((el) => els.push({
      src: el.src || el.currentSrc || '', ct: el.currentTime,
      paused: el.paused, ended: el.ended,
    }));
    return { route, els, t: Date.now() };
  };
  window.__stopDump = async () => {
    rec.requestData(); await new Promise(r => setTimeout(r, 250));
    rec.stop(); await new Promise(r => setTimeout(r, 250));
    const blob = new Blob(chunks, { type: 'audio/webm' });
    const buf = await blob.arrayBuffer(); const b = new Uint8Array(buf);
    let s = ''; for (let i = 0; i < b.length; i++) s += String.fromCharCode(b[i]);
    return { b64: btoa(s), bytes: b.length };
  };
})();
"""


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def is_narr(src: str) -> bool:
    return "/audio/questions/" in src and src.endswith(".mp3")


def puck_row(page: Page, idx: int):
    return page.locator("main > div").nth(idx)


def puck_state(page: Page, idx: int) -> str:
    try:
        return puck_row(page, idx).locator("span.text-cyan-300").first.inner_text(timeout=1500)
    except Exception:
        return ""


class Tracker:
    """Detects a narration element actively advancing its clock off-route."""

    def __init__(self, tv: Page):
        self.tv = tv
        self.last_ct: dict[str, float] = {}
        self.narration_play_events = 0
        self.violations: list[dict] = []
        self.samples = 0

    def sample(self) -> None:
        try:
            snap = self.tv.evaluate("() => window.__probe ? window.__probe() : null")
        except Exception:
            return
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

    def narration_is_playing(self) -> bool:
        try:
            snap = self.tv.evaluate("() => window.__probe ? window.__probe() : null")
        except Exception:
            return False
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
            if self.narration_is_playing():
                return True
            time.sleep(0.1)
        return False


def run() -> int:
    requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)
    log("=== R022 ground-truth bleed verification ===")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--autoplay-policy=no-user-gesture-required"],
        )
        ctx = browser.new_context(viewport={"width": 1600, "height": 900})
        hub = ctx.new_page()
        tv = ctx.new_page()
        tv.add_init_script(INIT)
        hub.goto(HUB, wait_until="domcontentloaded")
        tv.goto(TV + "/", wait_until="domcontentloaded")
        time.sleep(0.8)
        tv.mouse.click(800, 450)  # unlock audio
        time.sleep(0.6)

        trk = Tracker(tv)

        # pair + start
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
            route = tv.evaluate("() => location.pathname")
            log(f"--- round {rnd+1} --- route={route}")
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
                                puck_row(hub, idx).get_by_role("button", name=label, exact=False).first.click(timeout=1200)
                                break
                            except Exception:
                                continue
                    trk.watch(2.2); continue

                if "ANSWERING" in s1 and "ANSWERING" in s2:
                    # Wait for the host to actually START reading, THEN answer
                    # fast on both — forces reveal mid-narration (R022 case).
                    started = trk.wait_for_narration(timeout_s=4.0)
                    if started:
                        rounds_with_narration += 1
                        log(f"  narration playing — answering both fast")
                    else:
                        log(f"  (no narration this question — answering anyway)")
                    for idx, letter in ((0, "A"), (1, "B")):
                        try:
                            puck_row(hub, idx).get_by_role("button", name=letter, exact=True).click(timeout=2500, force=True)
                        except Exception:
                            pass
                    # Watch HARD across reveal + the navigation after it.
                    trk.watch(4.5)
                    break

                trk.watch(0.5)

        trk.watch(3.0)  # final nav to scoreboard
        log(f"final route: {tv.evaluate('() => location.pathname')}")

        # Pull the recorded audio + event log.
        dump = tv.evaluate("() => window.__stopDump()")
        events = tv.evaluate("() => window.__log || []")
        browser.close()

    trk.narration_play_events = len([e for e in events if e["a"] == "play" and is_narr(e["src"])])
    log(f"samples={trk.samples}  narration play events={trk.narration_play_events}  "
        f"rounds where narration played={rounds_with_narration}")

    # Save + measure the recorded audio (self-gate: real sound happened).
    cap_dur, cap_vol = 0.0, float("-inf")
    if dump and dump.get("b64"):
        tmp = tempfile.mkdtemp(prefix="bleedcap_")
        webm = os.path.join(tmp, "match.webm"); wav = os.path.join(tmp, "match.wav")
        with open(webm, "wb") as f:
            f.write(base64.b64decode(dump["b64"]))
        subprocess.run(["ffmpeg", "-y", "-i", webm, wav], capture_output=True, text=True)
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "default=noprint_wrappers=1:nokey=1", wav],
                             capture_output=True, text=True)
        try: cap_dur = float(out.stdout.strip())
        except ValueError: pass
        vd = subprocess.run(["ffmpeg", "-i", wav, "-af", "volumedetect", "-f", "null", "-"],
                            capture_output=True, text=True)
        for ln in vd.stderr.splitlines():
            if "mean_volume:" in ln:
                try: cap_vol = float(ln.split("mean_volume:")[1].split("dB")[0].strip())
                except Exception: pass
        log(f"recorded audio: {cap_dur:.1f}s, mean {cap_vol:.1f} dB, artifact {webm}")

    # ---- honest verdict ----
    log("")
    if trk.narration_play_events == 0 or cap_vol <= -60:
        log("RESULT: INCONCLUSIVE — narration never actually played / no sound")
        log("        captured. Cannot certify the bleed is fixed. (exit 2)")
        return 2
    if trk.violations:
        log(f"RESULT: FAIL — narration clock advanced off /question on "
            f"{len(trk.violations)} samples (R022 LIVE):")
        for v in trk.violations[:10]:
            log(f"   {v['t']} route={v['route']} narration={v['src']} ct={v['ct']}s")
        return 1
    log(f"RESULT: PASS — narration played in {rounds_with_narration} rounds, real")
    log(f"        audio captured ({cap_vol:.1f} dB), and NEVER advanced off the")
    log(f"        /question screen. R022 bleed is genuinely not occurring.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
