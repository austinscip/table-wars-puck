"""Diagnostic: confirm "Q1 silent, Q2+ procedural" audio pattern.

Hypothesis: audio.ts _playSample returns true unconditionally when status
is 'unknown' (Q1 first call). play() rejects async, setting status to
'missing', but the synchronous return already blocked the procedural
fallback. Q2 sees status='missing' and falls through to procedural.

To confirm: drive a TV through two answer_locked events. Check that
- Q1: an HTMLAudio sfx_lock.mp3 create + error happens, NO procedural
  oscillator activity.
- Q2: NO new HTMLAudio attempt, AND an AudioContext oscillator burst
  happens (procedural fallback fired).

Run with sandbox Flask up on :5002:
    cd ~/table-wars-puck-sandbox/server
    venv/bin/python scripts/diag_audio_q1.py
"""
from __future__ import annotations

import json
import sys
import time

import requests
from playwright.sync_api import sync_playwright


BASE = "http://localhost:5002"
TV = f"{BASE}/tv/speed-pyramid"


def reset() -> None:
    requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)


def post(path: str, body: dict | None = None) -> dict:
    r = requests.post(f"{BASE}{path}", json=body or {}, timeout=10)
    r.raise_for_status()
    if r.text.strip().startswith("{"):
        return r.json()
    return {}


def drive_match_to_q1() -> tuple[str, int]:
    reset()
    post("/api/pair/clear")
    r = post("/api/pair/request", {"puck_id": 901})
    code = r["pair_code"]
    post("/api/pair/confirm", {"puck_id": 901, "code": code})
    post("/api/pair/request", {"puck_id": 902})
    post("/api/pair/confirm", {"puck_id": 902, "code": code})
    sc = post("/api/pair/start", {"puck_id": 901})["session_code"]
    for _ in range(5):
        lq = post(f"/api/sp/load-question/{sc}")
        if "question" in lq:
            return sc, lq["question"]["id"]
    raise RuntimeError("no question phase reached")


def install_probes(page) -> None:
    """Capture: HTMLAudio create/play/error, AudioContext oscillator
    activity, and audio._sampleStatus / audio._unlocked snapshots."""
    page.add_init_script("""
      (() => {
        const events = [];
        const oscEvents = [];
        const _Audio = window.Audio;
        window.Audio = function(src) {
          const a = new _Audio(src);
          events.push({type:'create', src:a.src || src, ts:Date.now()});
          a.addEventListener('play',  () => events.push({type:'play',  src:a.src, ts:Date.now()}));
          a.addEventListener('error', () => events.push({type:'error', src:a.src, code:a.error?.code, ts:Date.now()}));
          return a;
        };
        const _Ctx = window.AudioContext || window.webkitAudioContext;
        if (_Ctx) {
          window.AudioContext = class extends _Ctx {
            constructor(...a) {
              super(...a);
              const _create = this.createOscillator.bind(this);
              this.createOscillator = function() {
                oscEvents.push({ts:Date.now(), state:this.state});
                return _create();
              };
            }
          };
        }
        window.__audioEvents = events;
        window.__oscEvents = oscEvents;
      })();
    """)


def run() -> int:
    sc, qid = drive_match_to_q1()
    print(f"session={sc} qid={qid}")

    with sync_playwright() as p:
        # Match the user's real Chrome runtime: --autoplay-policy=no-user-
        # gesture-required (their planned bar-deployment flag) plus the
        # chrome://settings/content/sound "allowed" workaround. In headless
        # default mode AudioContext stays suspended forever; with this flag
        # it resumes immediately, mirroring how the user actually hears it.
        browser = p.chromium.launch(
            headless=True,
            args=["--autoplay-policy=no-user-gesture-required"],
        )
        ctx = browser.new_context()
        page = ctx.new_page()
        install_probes(page)
        page.goto(f"{TV}/question/{sc}", wait_until="networkidle")
        time.sleep(1.5)

        # === Q1 answer_locked sequence ===
        # Two answers -> reveal -> server auto-advances to Q2.
        post("/api/sp/answer", {
            "session_code": sc, "puck_id": 901, "question_id": qid,
            "answer": "A", "response_time_ms": 1000,
        })
        # Give the TV a beat to receive the answer_locked socket event.
        time.sleep(1.0)
        ev_after_q1_first = page.evaluate("() => window.__audioEvents.slice()")
        osc_after_q1_first = page.evaluate("() => window.__oscEvents.slice()")
        print()
        print("=== After Q1 puck1 answer (one answer_locked emitted) ===")
        print(f"  audio events ({len(ev_after_q1_first)}):")
        for e in ev_after_q1_first:
            print(f"    {e}")
        print(f"  oscillator-create events: {len(osc_after_q1_first)}")
        for e in osc_after_q1_first:
            print(f"    {e}")

        post("/api/sp/answer", {
            "session_code": sc, "puck_id": 902, "question_id": qid,
            "answer": "B", "response_time_ms": 1500,
        })
        time.sleep(2.5)  # reveal + advance to Q2

        # Snapshot internal sample status table after Q1.
        status = page.evaluate("""
          () => {
            // The audio module exports a singleton 'audio'. Its closure
            // holds _sampleStatus. We can't read it directly without an
            // export, so we infer by inspecting cached audio elements.
            // Just dump created HTMLAudios.
            const evs = window.__audioEvents || [];
            const seen = {};
            for (const e of evs) {
              const m = (e.src || '').match(/\\/audio\\/(?:sfx_[^/]+|[^/]+)\\.mp3$/);
              const key = m ? m[0].replace('/audio/','').replace('.mp3','') : (e.src||'');
              if (!seen[key]) seen[key] = {};
              seen[key][e.type] = (seen[key][e.type] || 0) + 1;
            }
            return seen;
          }
        """)
        print()
        print("=== Audio file event counts after Q1 ===")
        print(json.dumps(status, indent=2))

        # === Q2 ===
        # Find Q2's qid from server.
        cq = requests.get(f"{BASE}/api/sp/current-question/{sc}", timeout=5).json()
        qid2 = cq.get("question_id")
        print(f"\n=== Q2 qid={qid2} ===")
        post("/api/sp/answer", {
            "session_code": sc, "puck_id": 901, "question_id": qid2,
            "answer": "A", "response_time_ms": 1000,
        })
        time.sleep(1.0)
        ev_after_q2 = page.evaluate("() => window.__audioEvents.slice()")
        osc_after_q2 = page.evaluate("() => window.__oscEvents.slice()")
        delta_audio = ev_after_q2[len(ev_after_q1_first):]
        delta_osc = osc_after_q2[len(osc_after_q1_first):]
        print(f"  new audio events after Q2 puck1 ({len(delta_audio)}):")
        for e in delta_audio[:20]:
            print(f"    {e}")
        print(f"  new oscillator-creates after Q2 puck1 ({len(delta_osc)}):")
        for e in delta_osc[:10]:
            print(f"    {e}")

        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(run())
