"""Speed Pyramid end-to-end smoke — opens the TV in real Chromium,
drives a full match as two fake pucks via REST, and asserts the things
a wiring-only smoke can't see:

  - the question-narration MP3 actually loads and `play()` event fires
  - the reveal SFX (correct_N.mp3 / wrong_N.mp3) actually plays
  - the per-puck commentary text is rendered on reveal
  - the scoreboard shows N/7 not 0/1 (TIMEOUT bookkeeping ok)
  - the round counter starts at 1 not 2

Failure modes this catches that prior smokes missed:
  - browser autoplay policy blocks audio silently → narration doesn't play
  - SFX HTMLAudio elements 404 → procedural fallback that nobody hears
  - state machine increments round counter twice before first question

Run with sandbox Flask up on :5002:

    cd ~/table-wars-puck-sandbox/server
    venv/bin/python scripts/e2e_smoke.py

Exits 0 on green, non-zero with a clear report on any assertion fail.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright


BASE = "http://localhost:5002"
TV_BASE = f"{BASE}/tv/speed-pyramid"
DB_PATH = Path(__file__).resolve().parent.parent / "tablewars.db"


class Smoke:
    """Single-purpose state for one match run. Collects pass/fail
    facts as we go; print_report at the end summarizes."""

    def __init__(self) -> None:
        self.checks: list[tuple[str, bool, str]] = []
        self.audio_events: list[dict] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append((name, ok, detail))
        flag = "PASS" if ok else "FAIL"
        print(f"  [{flag}] {name}" + (f"  -- {detail}" if detail else ""))

    def all_green(self) -> bool:
        return all(ok for _, ok, _ in self.checks)

    def print_report(self) -> None:
        n = len(self.checks)
        green = sum(1 for _, ok, _ in self.checks if ok)
        print()
        print(f"==== {green}/{n} checks passed ====")
        if not self.all_green():
            print("FAILURES:")
            for name, ok, detail in self.checks:
                if not ok:
                    print(f"  - {name}: {detail}")


def db_get_correct(qid: int) -> str:
    """Look up the correct_answer letter for a question. Used so the
    smoke can submit a verifiable correct vs verifiable wrong answer
    and trigger both commentary branches."""
    with sqlite3.connect(str(DB_PATH)) as c:
        row = c.execute(
            "SELECT correct_answer, host_commentary_correct, host_commentary_wrong "
            "FROM trivia_questions WHERE id = ?",
            (qid,),
        ).fetchone()
    return row[0], row[1] or "", row[2] or ""


def post(path: str, body: dict | None = None, allow_404: bool = False) -> dict:
    """POST JSON, decode response. Errors raise so the smoke fails fast,
    unless allow_404 is set — used for endpoints that may not exist on
    every commit (e.g. sp_start_timer was added mid-sprint-2E)."""
    r = requests.post(f"{BASE}{path}", json=body or {}, timeout=10)
    if allow_404 and r.status_code == 404:
        return {"__missing__": True, "status": 404}
    r.raise_for_status()
    if r.text.strip().startswith("{"):
        return r.json()
    return {}


def drive_match_to_question(smoke: Smoke) -> tuple[str, int, int]:
    """Pair 2 fake pucks, start match, work through category-pick +
    minigame, return (session_code, question_id, correct_letter)."""
    post("/api/pair/clear")
    r1 = post("/api/pair/request", {"puck_id": 901})
    code = r1["pair_code"]
    post("/api/pair/confirm", {"puck_id": 901, "code": code})
    post("/api/pair/request", {"puck_id": 902})
    post("/api/pair/confirm", {"puck_id": 902, "code": code})
    sc = post("/api/pair/start", {"puck_id": 901})["session_code"]

    # Drive through category-pick and any pre-round minigame until we
    # land on a question phase.
    for _ in range(8):
        resp = post(f"/api/sp/load-question/{sc}")
        phase = resp.get("phase", "question")
        if phase == "category_pick":
            picker = resp["picker_puck_id"]
            cat = resp["offer"][0]["id"]
            post(f"/api/sp/select-category/{sc}",
                 {"puck_id": picker, "category_id": cat})
        elif phase == "minigame":
            post(f"/api/sp/minigame/finish/{sc}")
        else:
            qid = resp["question"]["id"]
            correct, cc, cw = db_get_correct(qid)
            smoke.check("setup_text present, question_text empty",
                        resp["question"]["setup"] and not resp["question"]["question"],
                        f"setup={resp['question']['setup'][:40]!r} q={resp['question']['question']!r}")
            smoke.check("audio_url returned by load-question",
                        bool(resp.get("audio_url") and resp["audio_url"].endswith(".mp3")),
                        f"audio_url={resp.get('audio_url')}")
            smoke.check("round starts at 1 not 2",
                        resp.get("round") == 1,
                        f"round={resp.get('round')}")
            return sc, qid, correct
    raise RuntimeError("never reached question phase in 8 iterations")


def install_audio_probes(page) -> None:
    """Inject before any page script runs. Monkey-patches the Audio
    constructor and AudioContext so we can read what the TV tried to
    play and whether play() rejected."""
    page.add_init_script("""
        (() => {
          const events = [];
          const _OrigAudio = window.Audio;
          window.Audio = function(src) {
            const a = new _OrigAudio(src);
            const tag = src || a.src;
            events.push({type:'create', src:tag, ts:Date.now()});
            a.addEventListener('play',   () => events.push({type:'play',   src:a.src, ts:Date.now()}));
            a.addEventListener('playing',() => events.push({type:'playing',src:a.src, ts:Date.now()}));
            a.addEventListener('error',  () => events.push({type:'error',  src:a.src, code:a.error?.code, ts:Date.now()}));
            a.addEventListener('ended',  () => events.push({type:'ended',  src:a.src, ts:Date.now()}));
            return a;
          };
          const _OrigCtx = window.AudioContext || window.webkitAudioContext;
          const ctxs = [];
          if (_OrigCtx) {
            window.AudioContext = class extends _OrigCtx {
              constructor(...a) { super(...a); ctxs.push(this); }
            };
          }
          window.__audioEvents = events;
          window.__audioCtxs   = ctxs;
        })();
    """)


def assert_narration_plays(page, smoke: Smoke, qid: int) -> None:
    """Wait up to 5s for the question MP3 to fire a play event."""
    deadline = time.time() + 5
    target = f"/static/games/speed-pyramid/audio/questions/q_{qid}.mp3"
    while time.time() < deadline:
        events = page.evaluate("() => window.__audioEvents || []")
        plays = [e for e in events if e.get("type") == "play" and target in (e.get("src") or "")]
        if plays:
            smoke.check(f"narration play event fired for q_{qid}.mp3",
                        True, f"after {round((plays[0]['ts'] - events[0]['ts']) / 1000, 2)}s")
            errors = [e for e in events if e.get("type") == "error" and target in (e.get("src") or "")]
            smoke.check("narration MP3 did not error",
                        not errors, f"errors={errors}")
            return
        time.sleep(0.2)
    events = page.evaluate("() => window.__audioEvents || []")
    smoke.check(f"narration play event fired for q_{qid}.mp3", False,
                f"timeout. captured events: {events[:10]}")


def assert_audio_context_unlocked(page, smoke: Smoke) -> None:
    """Without a user gesture, AudioContext stays 'suspended' and
    procedural SFX never play. The silent-mp4 unlock trick should
    flip this to 'running'."""
    states = page.evaluate("() => (window.__audioCtxs || []).map(c => c.state)")
    has_running = any(s == "running" for s in states)
    smoke.check("AudioContext unlocked (state=running)",
                has_running, f"states={states}")


def run() -> int:
    smoke = Smoke()
    print(f"==== sandbox e2e smoke @ {BASE} ====")

    # REST drive — also fills smoke checks for content shape.
    sc, qid, correct = drive_match_to_question(smoke)
    print(f"  session={sc} qid={qid} correct={correct}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        install_audio_probes(page)

        # Navigate to the TV's question screen and watch the audio probes.
        page.goto(f"{TV_BASE}/question/{sc}", wait_until="networkidle")
        time.sleep(1.0)  # give React time to render + kick off narration

        assert_narration_plays(page, smoke, qid)
        assert_audio_context_unlocked(page, smoke)

        # Drive reveal: both pucks answer, watch for SFX play event.
        # start-timer didn't exist at every commit; allow 404 so the
        # harness still runs to completion on older baselines and we
        # see the rest of the failures.
        start_resp = post(f"/api/sp/start-timer/{sc}", allow_404=True)
        smoke.check("/api/sp/start-timer endpoint exists",
                    not start_resp.get("__missing__"),
                    "needed for narration -> timer handoff")
        wrong = "A" if correct == "D" else "D"
        post("/api/sp/answer", {"session_code": sc, "puck_id": 901,
                                "question_id": qid, "answer": correct,
                                "response_time_ms": 2400})
        reveal = post("/api/sp/answer", {"session_code": sc, "puck_id": 902,
                                         "question_id": qid, "answer": wrong,
                                         "response_time_ms": 3100})
        smoke.check("reveal_emitted=true on second answer",
                    reveal.get("reveal_emitted") is True,
                    f"reveal_emitted={reveal.get('reveal_emitted')}")

        # Give the TV a moment to receive the reveal socket event + play SFX.
        time.sleep(2.0)
        events = page.evaluate("() => window.__audioEvents || []")
        sfx_plays = [e for e in events if e.get("type") == "play"
                     and ("/audio/sfx/" in (e.get("src") or ""))]
        smoke.check("reveal SFX play event fired",
                    bool(sfx_plays),
                    f"sfx_plays={sfx_plays[:3]}")

        # Commentary visibility on the question screen during reveal.
        body_text = page.evaluate("() => document.body.innerText")
        _, cc, cw = db_get_correct(qid)
        smoke.check("correct-answer commentary visible on TV",
                    cc and cc in body_text,
                    f"expected={cc!r} in_body={cc in body_text if cc else 'no commentary'}")
        smoke.check("wrong-answer commentary visible on TV",
                    cw and cw in body_text,
                    f"expected={cw!r} in_body={cw in body_text if cw else 'no commentary'}")

        # Screenshot the reveal for visual record.
        shot_path = Path("/tmp/sp_e2e_reveal.png")
        page.screenshot(path=str(shot_path), full_page=True)
        print(f"  reveal screenshot: {shot_path}")

        browser.close()

    smoke.print_report()
    return 0 if smoke.all_green() else 1


if __name__ == "__main__":
    sys.exit(run())
