"""Gate for R021 — narration MUST NOT start the instant the question
card commits. There's a deliberate 600ms gap so the framer-motion
slide-in finishes before the host starts reading.

THE INVARIANT
-------------
QuestionScreen.tsx ~line 301:

    // R021: delay narration playback by 600ms so the question card
    // finishes its 450ms framer-motion slide-in before the host starts
    // reading.
    const PLAY_DELAY_MS = 600
    const playTimer = window.setTimeout(() => {
      ...
      void a.play().catch(handoff)
    }, PLAY_DELAY_MS)

That setTimeout sits between `new Audio(args.audio_url)` (the moment we
KNOW a question_show was processed) and the actual `a.play()` call. The
gate measures the gap directly:

    delta = first_narration_play_ts - corresponding_audio_create_ts

Must be >= 400ms (defensive vs the 600ms target — JS timer slack and
event loop jitter can shave a frame or two, but 400ms is impossible to
hit accidentally).

REPRO
-----
1. Open the TV with INIT_AUDIO_PLAY_LOG (HTMLAudioElement.play hook)
   PLUS a constructor hook that records every `new Audio(src)` with a
   timestamp.
2. Pair, start, drive TV to /question/<sc>. Q1 loads.
3. Wait long enough for the narration to actually start (~3s for the
   600ms delay + a beat).
4. Pull `window.__log`. Find the FIRST 'create' for a narration src
   (matches `/audio/questions/` or `q_<id>.mp3`). Find the FIRST 'play'
   for the same src. Assert play.t - create.t >= 400.

If the regression returns (PLAY_DELAY_MS=0 or the setTimeout removed),
the gap collapses to ~0–50 ms and the gate FAILs.

Gate assertion name: narration-starts-after-question-card-slide-in
"""
from __future__ import annotations

import re
import sys
import time

from verify_lib import (
    BASE, log, Verifier, session, pair_and_start, read_audio_play_log,
    INIT_AUDIO_PLAY_LOG, _resolve_pick, drive_match_to_scoreboard,
)


# Hook the Audio constructor so we can timestamp the moment QuestionScreen
# decides to create a narration element (i.e., the question_show handoff
# point). The R021 fix is the setTimeout BETWEEN this moment and play().
INIT_AUDIO_CTOR_LOG = r"""
(() => {
  const _A = window.Audio;
  function PatchedAudio(src) {
    const a = src !== undefined ? new _A(src) : new _A();
    try {
      (window.__log = window.__log || []).push({
        a: 'create', src: src || a.src || '',
        route: location.pathname, t: Date.now(),
      });
    } catch (e) {}
    return a;
  }
  PatchedAudio.prototype = _A.prototype;
  window.Audio = PatchedAudio;
})();
"""


def _is_narration(src: str) -> bool:
    # Sandbox serves Kokoro MP3s from /static/games/speed-pyramid/audio/
    # questions/q_<id>.mp3 (cache-busted by ?v=<mtime>).
    return ("/audio/questions/" in src) or bool(re.search(r"q_\d+\.mp3", src))


def run() -> int:
    v = Verifier()
    with session(record_audio_play=True,
                 tv_init_scripts=(INIT_AUDIO_CTOR_LOG,)) as (hub, tv):
        sc = pair_and_start(hub, tv, goto_question=True)
        if not sc:
            v.inconclusive("setup", "no session_code after pairing")
            return v.report()
        log(f"sc={sc}")

        # Round 1 is a category-pick round in current pacing — resolve it
        # so the TV navigates to /question and Q1 narration actually fires.
        # Drive the whole match — the in-flight TV will hit /question
        # at least once per round and we'll capture every narration
        # create+play pair into __log. We only need ONE valid pair to
        # measure the R021 delay invariant.
        log("driving match to scoreboard so __log fills with narration events")
        drive_match_to_scoreboard(hub, tv)
        time.sleep(2)

        log(f"TV url={tv.url} route={tv.evaluate('()=>location.pathname')}")
        events = read_audio_play_log(tv) or []
        log(f"audio events captured: {len(events)}")
        for e in events[:8]:
            log(f"  {e}")

        creates = [e for e in events
                   if e.get("a") == "create" and _is_narration(e.get("src", ""))]
        plays = [e for e in events
                 if e.get("a") == "play" and _is_narration(e.get("src", ""))]

        if not creates:
            v.inconclusive(
                "narration-starts-after-question-card-slide-in",
                f"no narration `new Audio` recorded — Q1 narration never "
                f"loaded. events[:6]={events[:6]}")
            return v.report()
        if not plays:
            v.inconclusive(
                "narration-starts-after-question-card-slide-in",
                f"narration created but never play()ed. creates={creates[:3]} "
                f"events[:8]={events[:8]}")
            return v.report()

        # Pair the first create with the first play for the SAME src.
        # 'create' src comes from `new Audio(args.audio_url)` and is
        # RELATIVE ("/static/games/..."), while 'play' src is the
        # absolute resolved URL ("http://host:port/static/games/...").
        # Also both carry ?v=<mtime> cache-bust. Normalize to path-only,
        # query-stripped, host-stripped.
        def path_of(src: str) -> str:
            no_query = src.split("?", 1)[0]
            # Strip protocol+host if absolute.
            if "://" in no_query:
                no_query = no_query.split("://", 1)[1]
                slash = no_query.find("/")
                no_query = no_query[slash:] if slash >= 0 else no_query
            return no_query

        c0 = creates[0]
        c0_path = path_of(c0["src"])
        p0 = next((p for p in plays if path_of(p["src"]) == c0_path), None)
        if p0 is None:
            v.inconclusive(
                "narration-starts-after-question-card-slide-in",
                f"narration create has no matching play. create={c0} "
                f"plays={plays[:3]}")
            return v.report()

        delta_ms = int(p0["t"]) - int(c0["t"])
        log(f"narration: create.t={c0['t']} play.t={p0['t']} delta={delta_ms}ms")

        # 400ms defensive bound: we want >=600 but timer slack on slow
        # CI/laptop event loops can shave ~100-150ms. 400ms is impossible
        # without an intentional delay between create and play.
        v.check(
            "narration-starts-after-question-card-slide-in",
            delta_ms >= 400,
            f"narration played {delta_ms}ms after Audio create — R021 "
            f"requires >=400ms gap (target 600ms). The framer-motion card "
            f"slide-in is 450ms; firing audio at <400ms means the host "
            f"starts reading mid-transition.",
        )

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
