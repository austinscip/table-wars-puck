"""Reusable browser-verification toolkit for Speed Pyramid.

Consolidates the patterns repeated across the 10+ gate/diag scripts:
Playwright session setup, Hub puck helpers, pair-and-start, the
phase-driven match driver, audio-event capture init, and a Verifier
class with the "inconclusive = fail" discipline.

Goal: gate scripts become small and obvious — just the unique
assertion they're testing, no boilerplate.

Usage pattern:

    from verify_lib import (
        session, pair_and_start, drive_match_to_scoreboard,
        log, puck_state, Verifier,
    )

    def run() -> int:
        v = Verifier()
        with session(record_sfx=True) as (hub, tv):
            sc = pair_and_start(hub, tv)
            qids = drive_match_to_scoreboard(hub, tv)
            v.check("answered 7 distinct questions", len(qids) == 7,
                    f"answered={len(qids)}")
        return v.report()

See gate_r024_pick_timeout.py / gate_audio_events.py for live examples.
"""
from __future__ import annotations

import json
import time
from contextlib import contextmanager
from typing import Callable, Iterable

import requests
from playwright.sync_api import sync_playwright, Page


# ============================================================================
# Constants
# ============================================================================

BASE = "http://localhost:5002"
TV = f"{BASE}/tv/speed-pyramid"
HUB = f"{TV}/dev/hub"


# ============================================================================
# INIT scripts (browser-side instrumentation)
# ============================================================================

INIT_SFX_LOG = (
    # sessionStorage so events persist across cross-document navigations.
    # `if null` so the array isn't reset on every tv.goto.
    "try {"
    "  if (sessionStorage.getItem('__sfxLog') === null)"
    "    sessionStorage.setItem('__sfxLog', '[]');"
    "} catch (e) {}"
)

# Patch HTMLAudioElement.play/pause to log events with the live route.
# Drop INIT_AUDIO_PLAY_LOG into add_init_script when you want to track
# narration-element lifecycle (e.g., bleed detection). Pairs naturally
# with INIT_SFX_LOG (different layer: HTMLAudioElement vs lib/audio bus).
INIT_AUDIO_PLAY_LOG = r"""
(() => {
  window.__log = [];
  window.__els = new Set();
  const _play = HTMLAudioElement.prototype.play;
  const _pause = HTMLAudioElement.prototype.pause;
  HTMLAudioElement.prototype.play = function () {
    window.__els.add(this);
    window.__log.push({ a: 'play', src: this.src || this.currentSrc || '',
                        route: location.pathname, t: Date.now() });
    return _play.apply(this, arguments);
  };
  HTMLAudioElement.prototype.pause = function () {
    window.__log.push({ a: 'pause', src: this.src || this.currentSrc || '',
                        route: location.pathname, t: Date.now() });
    return _pause.apply(this, arguments);
  };
  window.__probe = () => {
    const els = [];
    window.__els.forEach((el) => els.push({
      src: el.src || el.currentSrc || '', ct: el.currentTime,
      paused: el.paused, ended: el.ended,
    }));
    return { route: location.pathname, els };
  };
})();
"""


# ============================================================================
# Misc helpers
# ============================================================================

def log(msg: str) -> None:
    """Timestamped print to stdout, flushed."""
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def puck_row(page: Page, idx: int):
    """The N-th puck row in the Hub. `idx` is 0-based."""
    return page.locator("main > div").nth(idx)


def puck_state(page: Page, idx: int) -> str:
    """Read the cyan state-badge text from puck row idx. Empty string if
    not yet rendered."""
    try:
        return puck_row(page, idx).locator(
            "span.text-cyan-300").first.inner_text(timeout=1500)
    except Exception:
        return ""


def parse_qid(state: str) -> int | None:
    """Extract the question_id from a puck state badge like
    'ANSWERING Q12345 -> A' or 'Q12345'."""
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


# ============================================================================
# Verifier — pass / fail / inconclusive accounting
# ============================================================================

class Verifier:
    """Records named assertions with three outcomes: pass / fail /
    inconclusive. Inconclusive counts as failure when computing the exit
    code — a verification that couldn't exercise its condition must
    never report success (this is the discipline the user demanded
    after a harness produced false greens)."""

    def __init__(self):
        self.passes: list[str] = []
        self.failures: list[str] = []
        self.inconclusives: list[str] = []

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        flag = "PASS" if ok else "FAIL"
        log(f"  [{flag}] {name}" + (f" — {detail}" if detail else ""))
        (self.passes if ok else self.failures).append(name)
        return ok

    def inconclusive(self, name: str, reason: str = "") -> None:
        log(f"  [INCONCLUSIVE] {name}" + (f" — {reason}" if reason else ""))
        self.inconclusives.append(name)

    def report(self) -> int:
        log("")
        n = len(self.passes) + len(self.failures) + len(self.inconclusives)
        log(f"==== {len(self.passes)} pass / {len(self.failures)} fail / "
            f"{len(self.inconclusives)} inconclusive  ({n} total) ====")
        if self.failures:
            log("FAILURES:")
            for f in self.failures: log(f"  - {f}")
        if self.inconclusives:
            log("INCONCLUSIVE (treated as failure):")
            for i in self.inconclusives: log(f"  - {i}")
        # Inconclusive counts as failure.
        return 0 if not (self.failures or self.inconclusives) else 1


# ============================================================================
# Session — Playwright context manager
# ============================================================================

@contextmanager
def session(*,
            variant: str = "A",
            tv_init_scripts: Iterable[str] = (),
            record_sfx: bool = False,
            record_audio_play: bool = False,
            headless: bool = True,
            viewport: tuple[int, int] = (1600, 900)):
    """Open a Playwright Chromium with autoplay enabled, plus a Hub page
    and a TV page. Yields `(hub, tv)`. Optional flags:

      variant            — Hub variant: 'A' (compact), 'B' (game controller), 'C' (workshop).
      record_sfx         — install INIT_SFX_LOG on the TV so sessionStorage __sfxLog accumulates.
      record_audio_play  — install INIT_AUDIO_PLAY_LOG on the TV so HTMLAudioElement events log.
      tv_init_scripts    — additional add_init_script blocks for the TV.
      headless           — Chromium headless (default True).
      viewport           — (width, height) tuple, default (1600, 900).

    Pairs:
      - Hub starts at /tv/speed-pyramid/dev/hub?variant=<variant>.
      - TV starts at /tv/speed-pyramid/ (title screen).
    """
    requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--autoplay-policy=no-user-gesture-required"],
        )
        ctx = browser.new_context(viewport={"width": viewport[0],
                                             "height": viewport[1]})
        hub = ctx.new_page()
        tv = ctx.new_page()
        if record_sfx:
            tv.add_init_script(INIT_SFX_LOG)
        if record_audio_play:
            tv.add_init_script(INIT_AUDIO_PLAY_LOG)
        for s in tv_init_scripts:
            tv.add_init_script(s)
        hub_url = HUB + (f"?variant={variant}" if variant != "A" else "")
        hub.goto(hub_url, wait_until="domcontentloaded")
        tv.goto(TV + "/", wait_until="domcontentloaded")
        time.sleep(0.8)
        try:
            yield hub, tv
        finally:
            browser.close()


# ============================================================================
# Pairing + match driving
# ============================================================================

# Variant -> name of the "start match" button on the host puck row.
_START_BTN = {"A": "Start match", "B": "TAP", "C": "TAP"}


def pair_and_start(hub: Page, tv: Page, *,
                   variant: str = "A",
                   goto_question: bool = True) -> str | None:
    """Pair puck 0 (host) + puck 1 (joiner), host starts the match,
    optionally point the TV at /question/<sc>. Returns the session_code,
    or None if pairing failed."""
    puck_row(hub, 0).get_by_role("button", name="Hold 1s").click()
    time.sleep(0.5)
    puck_row(hub, 0).locator("button", has_text="Confirm").click()
    time.sleep(0.8)
    puck_row(hub, 1).get_by_role("button", name="Hold 1s").click()
    time.sleep(1.2)
    puck_row(hub, 0).get_by_role(
        "button", name=_START_BTN[variant], exact=True).click()
    time.sleep(1.2)
    sc = requests.get(f"{BASE}/api/pair/lobby-state",
                      timeout=5).json().get("session_code")
    if sc and goto_question:
        tv.goto(f"{TV}/question/{sc}", wait_until="domcontentloaded")
    return sc


def _resolve_pick(hub: Page) -> None:
    """Robust pick resolution. Hub re-renders every 500ms; one click
    often loses the race. Retry on both rows until neither is picking;
    R024 server auto-default also kicks at the 10s deadline."""
    deadline = time.time() + 13
    while time.time() < deadline:
        s1 = puck_state(hub, 0)
        s2 = puck_state(hub, 1)
        if "PICK CATEGORY" not in s1 and "PICK CATEGORY" not in s2:
            if "pick category" not in s1 and "pick category" not in s2:
                return
        for pidx in (0, 1):
            btns = puck_row(hub, pidx).locator("button[title]")
            if btns.count() > 0:
                try:
                    btns.first.click(force=True, timeout=1200)
                except Exception:
                    pass
        time.sleep(0.5)


def _resolve_minigame(hub: Page) -> None:
    """Fire on both pucks. Tries Fire / TAP / Tap labels (variant
    differences)."""
    for idx in (0, 1):
        for label in ("Fire", "Tap", "TAP"):
            try:
                puck_row(hub, idx).get_by_role(
                    "button", name=label, exact=False).first.click(timeout=1000)
                break
            except Exception:
                continue


def drive_match_to_scoreboard(
    hub: Page, tv: Page, *,
    answer_letter: Callable[[int | None], str] = lambda _qid: "A",
    deadline_s: float = 200,
    after_answer_sleep_s: float = 2.5,
) -> set[int]:
    """Phase-driven driver. Resolves whatever phase is current until the
    TV reaches /scoreboard/. Answers each distinct question_id exactly
    once (so the answer-POST count is deterministic).

    `answer_letter(qid)` lets you pick a per-question letter — return
    'A'..'D'. Default: always 'A'.

    Returns the set of question_ids answered.
    """
    answered: set[int] = set()
    deadline = time.time() + deadline_s
    while time.time() < deadline:
        route = tv.evaluate("() => location.pathname")
        if "/scoreboard/" in route:
            return answered
        s1 = puck_state(hub, 0)
        s2 = puck_state(hub, 1)
        if "MATCH ENDED" in s1 and "MATCH ENDED" in s2:
            return answered

        if "PICK CATEGORY" in s1 or "PICK CATEGORY" in s2 \
                or "pick category" in s1 or "pick category" in s2:
            _resolve_pick(hub)
            time.sleep(1.0)
            continue

        if "MINIGAME" in s1 or "MINIGAME" in s2 \
                or "mg/" in s1 or "mg/" in s2:
            _resolve_minigame(hub)
            time.sleep(2.0)
            continue

        if ("ANSWERING" in s1 and "ANSWERING" in s2) \
                or (s1.startswith("Q") and s2.startswith("Q")):
            qid = parse_qid(s1) or parse_qid(s2)
            if qid in answered:
                time.sleep(0.3)
                continue
            if qid is not None:
                answered.add(qid)
            letter = answer_letter(qid)
            for idx in (0, 1):
                try:
                    puck_row(hub, idx).get_by_role(
                        "button", name=letter, exact=True).click(
                            force=True, timeout=2500)
                except Exception:
                    pass
                time.sleep(0.3)
            time.sleep(after_answer_sleep_s)
            continue

        time.sleep(0.4)
    return answered


# ============================================================================
# Audio-log readers (for record_sfx / record_audio_play sessions)
# ============================================================================

def read_sfx_log(tv: Page) -> list[dict]:
    """Pull the accumulated SFX events recorded via INIT_SFX_LOG +
    lib/audio.ts's sessionStorage tap."""
    return tv.evaluate(
        "() => { try { return JSON.parse(sessionStorage.getItem('__sfxLog') "
        "|| '[]'); } catch (e) { return []; } }"
    )


def read_audio_play_log(tv: Page) -> list[dict]:
    """Pull HTMLAudioElement play/pause events recorded via
    INIT_AUDIO_PLAY_LOG."""
    return tv.evaluate("() => window.__log || []")


def probe_audio_elements(tv: Page) -> dict:
    """Snapshot current HTMLAudioElement state (route + per-element
    currentTime/paused/ended). Requires INIT_AUDIO_PLAY_LOG."""
    return tv.evaluate(
        "() => window.__probe ? window.__probe() : {route: '', els: []}"
    )
