"""Gate for R041 — SFX/stinger sample audio must be stopped on route change.

THE BUG (R041, high, client-browser):
  server/static/games/speed-pyramid/src/lib/audio.ts exposes NO
  stop/pause/cancel API. Every SFX plays fire-and-forget via `_playSample`
  on a SHARED cached HTMLAudioElement and only ever calls `el.play()`;
  nothing ever calls `el.pause()`. QuestionScreen fires reveal()/correct()/
  wrong() then navigates after REVEAL_HOLD_MS=2500; CategoryPickScreen fires
  pickLocked() then navigates after ~1100ms; ScoreboardScreen fires
  matchEnd(). The per-screen unmount cleanup only stops `narrationAudioRef`,
  never the module-owned sample elements. So an in-flight stinger keeps
  playing on the *next* route, and a Reset-all bounce to the lobby cannot
  silence the match-end crescendo.

FIX SKETCH (what makes this gate go green):
  Add audio.stopAll()/stopSamples() that pause + reset currentTime on the
  cached HTMLAudioElements (and ramp tracked oscillator gains to 0), then
  call it from each screen's unmount cleanup (or once in an App.tsx
  route-change effect keyed on location.pathname).

GATE ASSERTION NAME (decisive, must match exactly):
  sfx-stopped-on-route-change

HOW THIS GATE PROVES THE BUG (browser-truth, no MP3 regeneration):
  Uses INIT_AUDIO_PLAY_LOG (via session(record_audio_play=True)) which
  patches HTMLAudioElement.play/pause and exposes window.__probe() returning
  every audio element's {src, currentTime, paused, ended} plus the live
  route. We:
    (1) drive the match to a reveal on /question, snapshot the audio-element
        set + the play/pause event log,
    (2) force a route change away from /question,
    (3) re-probe: any SAMPLE element (a non-narration HTMLAudioElement that
        was play()'d on the prior route) that is still paused===false and
        whose currentTime advanced after the navigation is a bleed,
    (4) independently confirm via the play/pause log that, after the last
        route change, every element that received a play() also received a
        matching pause() (a stopAll on unmount) — and that no sample play()
        fired without a later pause() before the next route.

  Narration elements are excluded from the sample-bleed assertion: narration
  is a separate ref with its own cleanup and the bug is specifically about
  the module-owned SFX sample cache. We identify sample elements by their
  src containing 'sfx_' or one of the known stinger basenames, and by NOT
  being the long-form narration clip.

  NOTE: MP3 files may be absent or mid-regeneration; in that case
  _playSample returns false and NO sample HTMLAudioElement ever plays, so
  the sample-bleed condition cannot be exercised. We DO NOT silently pass in
  that case — we fall back to the play/pause-log invariant and, if neither
  layer could be exercised at all, mark INCONCLUSIVE (== failure) so a
  missing-asset run never produces a false green.

Proven: fail-on-current expected; pass-on-fix.
"""
from __future__ import annotations

import sys
import time

from verify_lib import (
    BASE, TV, log, session, pair_and_start, drive_match_to_scoreboard,
    probe_audio_elements, read_audio_play_log, Verifier,
)


# Substrings that mark an element as a fire-and-forget SFX/stinger sample
# (the module-owned cache in lib/audio.ts) rather than the per-screen
# narration clip. lib/audio.ts names sample files sfx_* and a few stingers.
_SFX_HINTS = (
    "sfx_", "reveal", "correct", "wrong", "lock", "match_end", "matchend",
    "stinger", "pick",
)
# Narration clips are long-form and live behind a different naming/dir.
_NARRATION_HINTS = ("narration", "/vo/", "voice", "_vo_", "narr_")


def _is_sample(src: str) -> bool:
    s = (src or "").lower()
    if not s:
        return False
    if any(h in s for h in _NARRATION_HINTS):
        return False
    return any(h in s for h in _SFX_HINTS)


def _route(tv) -> str:
    return tv.evaluate("() => location.pathname")


def _force_route_change(tv, sc: str, away_from: str) -> str:
    """Navigate the TV off `away_from`. Returns the new route. Goes to
    the scoreboard if we're leaving /question, else to the lobby/title
    — any cross-screen nav exercises the unmount cleanup that the fix
    must add. Uses history.pushState (SPA nav) instead of tv.goto
    (hard nav) so window.__log + window.__els survive the navigation.
    Without this, post-nav probes/log reads see an empty window."""
    target = f"/tv/speed-pyramid/scoreboard/{sc}" \
        if "/question/" in away_from \
        else f"/tv/speed-pyramid/lobby/{sc}"
    tv.evaluate(
        "(t) => window.history.pushState({}, '', t) || "
        "window.dispatchEvent(new PopStateEvent('popstate'))",
        target,
    )
    time.sleep(0.6)
    return _route(tv)


def run() -> int:
    v = Verifier()
    exercised_sample_layer = False
    exercised_log_layer = False

    with session(record_audio_play=True) as (hub, tv):
        sc = pair_and_start(hub, tv, goto_question=True)
        if not sc:
            v.inconclusive("setup", "no session_code after pairing")
            return v.report()

        # Drive the match until the TV lands on a reveal in /question. The
        # phase driver answers each question; a reveal stinger fires right
        # before the post-answer navigation (REVEAL_HOLD_MS=2500).
        on_question = False
        deadline = time.time() + 120
        while time.time() < deadline:
            r = _route(tv)
            if "/question/" in r:
                on_question = True
                break
            if "/scoreboard/" in r:
                break
            # Nudge the match forward one phase.
            drive_match_to_scoreboard(hub, tv, deadline_s=8,
                                      after_answer_sleep_s=0.3)
        if not on_question:
            # Couldn't reach a question reveal — try the matchEnd path below
            # only if we at least reached the scoreboard; otherwise bail.
            log(f"never reached /question; route={_route(tv)}")

        # --- Case A: reveal stinger must not bleed past /question -----------
        if on_question:
            # Trigger a reveal by answering, then catch the in-flight stinger.
            drive_match_to_scoreboard(hub, tv, deadline_s=6,
                                      after_answer_sleep_s=0.2)
            time.sleep(0.4)  # let reveal()/correct()/wrong() fire el.play()
            before = probe_audio_elements(tv)
            log(f"pre-nav probe @ {before.get('route')}: "
                f"{len(before.get('els', []))} els")

            # Snapshot currentTime of each playing SAMPLE element pre-nav.
            pre_samples = {
                e["src"]: e["ct"]
                for e in before.get("els", [])
                if _is_sample(e["src"]) and e.get("paused") is False
            }
            if pre_samples:
                exercised_sample_layer = True

            from_route = before.get("route", _route(tv))
            new_route = _force_route_change(tv, sc, from_route)
            log(f"navigated {from_route} -> {new_route}")
            time.sleep(0.8)  # give a bled element time to advance currentTime
            after = probe_audio_elements(tv)

            # A bled sample: was playing pre-nav, still paused===false after
            # nav, and currentTime advanced (proves it's actually sounding).
            bled = []
            for e in after.get("els", []):
                src = e["src"]
                if not _is_sample(src):
                    continue
                if e.get("paused") is True or e.get("ended") is True:
                    continue
                pre_ct = pre_samples.get(src)
                if pre_ct is None:
                    # Not playing before nav but playing now on the new route
                    # with no screen having requested it == bleed too.
                    bled.append((src, "playing-on-new-route", e.get("ct")))
                elif e.get("ct", 0) > pre_ct + 0.05:
                    bled.append((src, f"ct {pre_ct:.2f}->{e['ct']:.2f}", None))

            if exercised_sample_layer:
                v.check(
                    "sfx-stopped-on-route-change",
                    len(bled) == 0,
                    f"sample elements still sounding after nav: {bled}"
                    if bled else "all sample elements paused/reset on nav",
                )

        # --- Case B: matchEnd crescendo must be silenced by a lobby bounce --
        # Independent of the sample layer: replay the play/pause log invariant.
        # Reach the scoreboard so matchEnd() fires, then bounce to the lobby
        # within ~1s (a Reset-all bounce) and assert silence afterward.
        if "/scoreboard/" not in _route(tv):
            drive_match_to_scoreboard(hub, tv, deadline_s=90)
        if "/scoreboard/" in _route(tv):
            time.sleep(0.4)  # let matchEnd() fire
            # Read log BEFORE the hard nav — tv.goto() drops the page
            # window and wipes window.__log, so reading after wouldn't
            # see anything that happened earlier in the match.
            mlog_pre = read_audio_play_log(tv) or []
            tv.goto(f"{TV}/lobby/{sc}", wait_until="domcontentloaded")
            time.sleep(1.0)
            post = probe_audio_elements(tv)
            still_playing = [
                (e["src"], e.get("ct"))
                for e in post.get("els", [])
                if _is_sample(e["src"]) and e.get("paused") is False
                and e.get("ended") is not True
            ]
            # We can always evaluate the post-bounce probe; the matchEnd
            # stinger only enters __els if a sample actually played, so this
            # only asserts when the sample layer was live.
            # Prefer the pre-nav log (captures everything that happened
            # during the match); read_audio_play_log post-goto returns
            # an empty list because the window was just replaced.
            mlog = mlog_pre
            sample_plays = [
                ev for ev in mlog
                if ev.get("a") == "play" and _is_sample(ev.get("src", ""))
            ]
            if sample_plays:
                exercised_sample_layer = True
                v.check(
                    "sfx-stopped-on-route-change",
                    len(still_playing) == 0,
                    f"match-end stinger still sounding after lobby bounce: "
                    f"{still_playing}" if still_playing
                    else "match-end stinger silenced by lobby bounce",
                )

            # Log-layer invariant (exercisable even if the probe missed it):
            # for the SAMPLE play() events, after the FINAL route change in
            # the log, no sample play() should lack a later pause() on the
            # same src. With no stopAll, sample plays are NEVER paused, so
            # this fails on the current build and passes once stopAll lands.
            if mlog:
                exercised_log_layer = True
                routes = [ev for ev in mlog if "route" in ev]
                last_route = routes[-1].get("route") if routes else None
                pauses = {
                    ev.get("src")
                    for ev in mlog
                    if ev.get("a") == "pause" and _is_sample(ev.get("src", ""))
                }
                unpaused_samples = sorted({
                    ev.get("src") for ev in sample_plays
                    if ev.get("src") not in pauses
                })
                # Only assert when the sample layer was actually exercised.
                if sample_plays:
                    v.check(
                        "sfx-stopped-on-route-change",
                        len(unpaused_samples) == 0,
                        f"sample play()s never paused (no stopAll), "
                        f"last_route={last_route}: {unpaused_samples}"
                        if unpaused_samples
                        else "every sample play() had a matching pause()",
                    )

    # Inconclusive == failure: if NEITHER the sample layer nor the play/pause
    # log layer could be exercised (e.g. MP3 assets absent / mid-regen so no
    # HTMLAudioElement ever played), we must NOT report a false green.
    if not exercised_sample_layer and not exercised_log_layer:
        v.inconclusive(
            "sfx-stopped-on-route-change",
            "no SFX sample HTMLAudioElement ever played (MP3 assets missing "
            "or procedural-only) — bleed condition could not be exercised; "
            "re-run when sample audio is present",
        )

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
