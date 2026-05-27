"""Diagnose WHY narration never plays in a real match.

Drives a real Hub match and records, on the TV page:
  - every /api/sp/load-question response: phase, question id, audio_url
  - every /audio/questions/*.mp3 request + HTTP status (200 vs 404)
  - the TV route at the moment a question becomes active
  - every HTMLAudioElement play() / pause() event (patched)

Prints the timeline so we can see exactly where the host voice is lost:
no audio_url returned? mp3 404? wrong screen? play() never called?

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
  const _pause = HTMLAudioElement.prototype.pause;
  HTMLAudioElement.prototype.play = function () {
    window.__log.push({ a: 'play', src: this.src || this.currentSrc || '', route: location.pathname, t: Date.now() });
    return _play.apply(this, arguments);
  };
  HTMLAudioElement.prototype.pause = function () {
    window.__log.push({ a: 'pause', src: this.src || this.currentSrc || '', route: location.pathname, t: Date.now() });
    return _pause.apply(this, arguments);
  };
})();
"""


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def puck_row(page: Page, idx: int):
    return page.locator("main > div").nth(idx)


def puck_state(page: Page, idx: int) -> str:
    try:
        return puck_row(page, idx).locator("span.text-cyan-300").first.inner_text(timeout=1500)
    except Exception:
        return ""


def run() -> int:
    requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)
    loadq: list[dict] = []
    mp3: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        ctx = browser.new_context(viewport={"width": 1600, "height": 900})
        hub = ctx.new_page()
        tv = ctx.new_page()
        tv.add_init_script(INIT)

        def on_resp(resp):
            u = resp.url
            try:
                if "/api/sp/load-question" in u:
                    try:
                        b = resp.json()
                    except Exception:
                        b = {}
                    loadq.append({
                        "phase": b.get("phase"),
                        "qid": (b.get("question") or {}).get("id"),
                        "audio_url": b.get("audio_url"),
                        "t": time.strftime("%H:%M:%S"),
                    })
                elif "/audio/questions/" in u and u.endswith(".mp3"):
                    mp3.append({"file": u.split("/")[-1], "status": resp.status, "t": time.strftime("%H:%M:%S")})
            except Exception:
                pass

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
            log("FAIL: no session_code"); browser.close(); return 1
        log(f"sc={sc} -> TV /question/{sc}")
        tv.goto(f"{TV}/question/{sc}", wait_until="domcontentloaded")
        time.sleep(1.5)

        for rnd in range(7):
            for _ in range(10):
                s1, s2 = puck_state(hub, 0), puck_state(hub, 1)
                if "MATCH ENDED" in s1 and "MATCH ENDED" in s2:
                    break
                if "PICK CATEGORY" in s1 or "PICK CATEGORY" in s2:
                    picker = 0 if "PICK CATEGORY" in s1 else 1
                    cats = puck_row(hub, picker).locator("button[title]")
                    if cats.count() > 0:
                        try: cats.first.click(force=True, timeout=3000)
                        except Exception: pass
                    time.sleep(1.5); continue
                if "MINIGAME" in s1 or "MINIGAME" in s2:
                    for idx in (0, 1):
                        for label in ("Fire", "Tap", "TAP"):
                            try:
                                puck_row(hub, idx).get_by_role("button", name=label, exact=False).first.click(timeout=1200); break
                            except Exception: continue
                    time.sleep(2.0); continue
                if "ANSWERING" in s1 and "ANSWERING" in s2:
                    route = tv.evaluate("() => location.pathname")
                    log(f"round {rnd+1}: pucks ANSWERING, TV route = {route}")
                    # wait a moment for narration to (maybe) start, then answer
                    time.sleep(1.5)
                    for idx, letter in ((0, "A"), (1, "B")):
                        try:
                            puck_row(hub, idx).get_by_role("button", name=letter, exact=True).click(timeout=2500, force=True)
                        except Exception: pass
                    time.sleep(2.5); break
                time.sleep(0.5)

        time.sleep(2.0)
        events = tv.evaluate("() => window.__log || []")
        browser.close()

    print("\n===== load-question responses (TV) =====", flush=True)
    for r in loadq:
        au = r["audio_url"]
        print(f"  {r['t']} phase={r['phase']!s:14s} qid={r['qid']!s:7s} audio_url={'<none>' if not au else au.split('/')[-1]}")
    print(f"\n===== mp3 requests ({len(mp3)}) =====", flush=True)
    for r in mp3:
        print(f"  {r['t']} {r['file']:18s} status={r['status']}")
    print(f"\n===== HTMLAudioElement play/pause events ({len(events)}) =====", flush=True)
    for e in events:
        print(f"  {e['a']:5s} route={e['route']:40s} src={e['src'].split('/')[-1] if e['src'] else '<empty>'}")

    # summary
    q_loads = [r for r in loadq if r.get("qid")]
    with_audio = [r for r in q_loads if r.get("audio_url")]
    mp3_404 = [r for r in mp3 if r["status"] != 200]
    plays = [e for e in events if e["a"] == "play"]
    print("\n===== SUMMARY =====", flush=True)
    print(f"  question loads: {len(q_loads)}  |  with audio_url: {len(with_audio)}")
    print(f"  mp3 requests: {len(mp3)}  |  non-200: {len(mp3_404)}")
    print(f"  audio play() calls: {len(plays)}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
