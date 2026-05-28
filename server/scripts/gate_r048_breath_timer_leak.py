"""Gate for R048 — R023 breath-gap setTimeout is not tracked in
narrationTimersRef, so beginAnswering + a stray /api/sp/start-timer POST
can fire AFTER the QuestionScreen has navigated away.

The bug: inside handoff() in QuestionScreen.tsx the R023 "breath" is
    window.setTimeout(() => startTimer(sc).then(beginAnswering), 800)
but its timer id is never pushed into narrationTimersRef (unlike
metadataTimer/playTimer). Both the unmount cleanup and onReveal only
clear ids in narrationTimersRef, so neither can cancel the breath timer.
If narration 'ended'/'error' fires and then within 800ms the screen
unmounts (lobby_cancelled / match_ended / nav to pick/minigame) or a
reveal arrives, beginAnswering still runs on a dead screen: it POSTs
/api/sp/start-timer (restarting the server round timer) and arms a fresh
forceRevealTimer — a leaked server side-effect from an unmounted screen.

Gate assertion name (EXACT): breath-timer-cancelled-on-unmount

How this gate exercises the bug (browser-truth, in-page fetch tap):
  1. Pair + drive the TV onto a narrated /question/<sc> screen.
  2. Force the narration to take the 'error' handoff path immediately by
     making HTMLMediaElement.play() reject — handoff() then arms the
     800ms breath timer right away (no waiting on a real MP3, and we
     never touch the .mp3 files on disk).
  3. A patched window.setTimeout records the moment the 800ms breath
     timer is armed (__breathArmedAt).
  4. As soon as the breath is armed (and BEFORE the 800ms elapses), POST
     /api/pair/clear. The server emits 'lobby_cancelled', QuestionScreen's
     onLobbyCancelled navigates('/') — an in-app (same-document) unmount,
     so our in-page fetch log survives.
  5. A patched window.fetch logs every POST to /api/sp/start-timer with
     the location.pathname AT CALL TIME.
  6. Decisive assertion: NO start-timer POST is logged from a non-question
     route after the navigation. On the current build the orphaned breath
     timer fires ~800ms later from route '/' and POSTs start-timer — the
     leak. On the fixed build (id pushed to narrationTimersRef + aborted
     guard) the unmount cleanup cancels it and no such POST occurs.

Proven: fail-on-current expected; pass-on-fix.

Constraints honored: no Playwright launch of MP3 work, no writes to the
audio dir, no git, no process kills. Uses the shared verify_lib session.
"""
from __future__ import annotations

import sys
import time

import requests

from verify_lib import (
    BASE, TV, log, session, pair_and_start, Verifier,
)


# Init script installed on the TV BEFORE any app code runs.
#  - taps window.fetch to record start-timer POSTs + the route at call time
#  - forces narration play() to reject so handoff() takes the error path
#    immediately and arms the 800ms breath timer without a real MP3
#  - taps window.setTimeout to record when the 800ms breath timer is armed
INIT_BREATH_TAP = r"""
(() => {
  window.__startTimerLog = [];
  window.__breathArmedAt = 0;

  // 1) fetch tap — log every start-timer POST with the route at call time.
  const _fetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    try {
      const url = typeof input === 'string' ? input : (input && input.url) || '';
      const method = ((init && init.method) || (input && input.method) || 'GET')
        .toUpperCase();
      if (method === 'POST' && url.indexOf('/api/sp/start-timer/') !== -1) {
        window.__startTimerLog.push({
          url: url,
          route: location.pathname,
          t: Date.now(),
        });
      }
    } catch (e) { /* never let the tap break the app */ }
    return _fetch(input, init);
  };

  // 2) Force the narration error-handoff: any media play() rejects.
  //    QuestionScreen does `void a.play().catch(handoff)`, so a rejected
  //    play() drives handoff() immediately at PLAY_DELAY_MS (~600ms).
  try {
    const proto = window.HTMLMediaElement && window.HTMLMediaElement.prototype;
    if (proto) {
      proto.play = function () {
        return Promise.reject(new DOMException('forced-by-gate', 'NotAllowedError'));
      };
    }
  } catch (e) { /* leave play() alone if we cannot patch it */ }

  // 3) setTimeout tap — the R023 breath is scheduled at exactly 800ms.
  //    Record the arm time so the driver can navigate away inside the
  //    breath window deterministically (no wall-clock guessing).
  const _setTimeout = window.setTimeout.bind(window);
  window.setTimeout = function (fn, delay) {
    try {
      if (delay === 800) {
        window.__breathArmedAt = Date.now();
      }
    } catch (e) { /* ignore */ }
    return _setTimeout.apply(window, arguments);
  };
})();
"""


def _route(tv) -> str:
    return tv.evaluate("() => location.pathname")


def run() -> int:
    v = Verifier()
    with session(tv_init_scripts=[INIT_BREATH_TAP]) as (hub, tv):
        sc = pair_and_start(hub, tv, goto_question=True)
        if not sc:
            v.inconclusive("setup", "no session_code after pairing")
            return v.report()

        # Wait for the TV to land on the question screen for this session.
        on_q = False
        for _ in range(60):
            if "/question/" in _route(tv):
                on_q = True
                break
            time.sleep(0.25)
        if not on_q:
            v.inconclusive(
                "TV reached /question screen",
                f"route={_route(tv)}")
            return v.report()
        q_route = _route(tv)
        log(f"TV on question screen: {q_route}")

        # Confirm this question actually carries narration. Without an
        # audio_url the breath-gap code path never runs and the gate
        # would not exercise the bug — that must be inconclusive, not a
        # false pass. (We do NOT touch the mp3 files; just read the API.)
        cq = requests.get(f"{BASE}/api/sp/current-question/{sc}",
                          timeout=5).json()
        has_narration = False
        try:
            ln = requests.post(f"{BASE}/api/sp/load-question/{sc}",
                               json={}, timeout=5)
            # load-question is idempotent-ish for the current round; we
            # only use its audio_url to confirm narration is wired.
            audio_url = (ln.json() or {}).get("audio_url") or ""
            has_narration = bool(audio_url)
        except Exception:
            audio_url = ""
        if not has_narration:
            # Fall back: the question_show socket carries audio_url too;
            # if the API gave us nothing, we cannot guarantee the breath
            # path executes.
            v.inconclusive(
                "question carries narration audio_url",
                f"current_question={cq} audio_url={audio_url!r} — breath "
                "path not exercised")
            return v.report()
        log(f"narration confirmed: audio_url={audio_url}")

        # Wait until the breath timer (800ms) has been armed by handoff().
        # play() is patched to reject, so handoff fires at PLAY_DELAY_MS.
        armed = False
        for _ in range(80):  # up to ~12s
            if tv.evaluate("() => window.__breathArmedAt || 0") > 0:
                armed = True
                break
            time.sleep(0.15)
        if not armed:
            v.inconclusive(
                "R023 breath timer armed (handoff fired)",
                "no 800ms setTimeout observed — narration handoff never ran")
            return v.report()
        log("breath timer armed — navigating away within the 800ms window")

        # We are inside the 800ms breath window. Trigger an in-app
        # navigation away from QuestionScreen by clearing the lobby:
        # the server emits lobby_cancelled and onLobbyCancelled does
        # navigate('/'), unmounting QuestionScreen WITHOUT a full page
        # reload (BrowserRouter), so our in-page fetch log survives.
        requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)

        # Wait for the in-app nav to actually leave /question.
        navigated = False
        for _ in range(40):  # up to ~6s
            if "/question/" not in _route(tv):
                navigated = True
                break
            time.sleep(0.15)
        if not navigated:
            v.inconclusive(
                "QuestionScreen unmounted (navigated off /question)",
                f"route still {_route(tv)} after lobby_cancelled")
            return v.report()
        post_nav_route = _route(tv)
        log(f"navigated away — route now {post_nav_route}")

        # Let the orphaned breath timer have its chance to fire. The
        # breath fires 800ms after arming; we already spent time
        # navigating, but wait generously to be safe.
        time.sleep(1.4)

        # Inspect the fetch log. The DECISIVE leak signal: a start-timer
        # POST whose recorded route is NOT the question screen — i.e. it
        # was issued after the screen navigated away.
        log_entries = tv.evaluate("() => window.__startTimerLog || []")
        leaked = [
            e for e in log_entries
            if "/question/" not in str(e.get("route", ""))
        ]
        for e in log_entries:
            log(f"  start-timer POST route={e.get('route')!r} t={e.get('t')}")

        v.check(
            "breath-timer-cancelled-on-unmount",
            len(leaked) == 0,
            (f"leaked start-timer POSTs after nav: {leaked}"
             if leaked else
             f"no post-nav start-timer POST ({len(log_entries)} total, "
             "all from /question)"),
        )

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
