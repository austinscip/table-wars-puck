"""Gate for R046 — pick-timeout auto-default must emit the same lock cue
as a manual pick (audible pickLocked SFX + chosen-card highlight).

The bug (kind: mixed):
  server/pair_routes.py _maybe_auto_resolve_pick (761-777) stashes
  next_category_id and clears pending_category_pick but emits NO socket,
  unlike sp_select_category (1820-1829) which emits 'category_picked'.
  On the TV, CategoryPickScreen.onPicked (83-91) is the ONLY place
  audio.pickLocked() and setChosenId() run, and it is wired solely to the
  'category_picked' socket. On a pure 10s timeout the screen's kickedRef
  branch (114-132) calls loadQuestion then navigate('/question') directly:
  chosenId stays null, onPicked never fires, so the picker/audience get
  ZERO audible (sfx_pick_locked) or visible (chosen-card highlight) lock-in
  cue. The screen shows 'Waiting on Puck N…' right up until it cuts to the
  question. This is the open R019.

Decisive gate assertion name: pick-timeout-emits-lock-cue

Repro strategy (mixed: browser truth + REST corroboration):
  1. Pair + start, ride the TV to the round-1 /category-pick screen.
  2. Do NOTHING — let the 10s server deadline lapse with no select-category.
  3. BROWSER TRUTH: assert __sfxLog accumulated an 'sfx_pick_locked' entry
     whose route is the /category-pick screen. On the current build this is
     ABSENT (no category_picked socket -> onPicked never runs -> no
     pickLocked()). After the fix it is PRESENT. This is the decisive check.
  4. REST CORROBORATION: confirm the timeout path actually resolved server
     side — load-question after the deadline returns a real question (not a
     still-pending 'category_pick' phase). This proves the lock-cue
     condition was genuinely EXERCISED, so an absent SFX is the bug and not
     an unexercised path (inconclusive=fail discipline).

Proven: fail-on-current expected; pass-on-fix.
"""
from __future__ import annotations

import sys
import time

import requests

from verify_lib import (
    BASE, TV, log, session, pair_and_start, read_sfx_log, Verifier,
)

# Routes/keys the SFX bus logs.
_PICK_LOCKED_SFX = "sfx_pick_locked"
_PICK_PATH = "/category-pick"


def run() -> int:
    v = Verifier()
    # record_sfx=True installs INIT_SFX_LOG so lib/audio.ts's sessionStorage
    # tap accumulates every _play() call across cross-document navigations.
    with session(record_sfx=True) as (hub, tv):
        sc = pair_and_start(hub, tv, goto_question=True)
        if not sc:
            v.inconclusive("setup", "no session_code after pairing")
            return v.report()

        # Ride the TV to the round-1 category-pick screen.
        on_pick = False
        for _ in range(40):
            if _PICK_PATH + "/" in tv.evaluate("() => location.pathname"):
                on_pick = True
                break
            time.sleep(0.25)
        if not on_pick:
            v.inconclusive(
                "TV reached category-pick screen",
                f"route={tv.evaluate('() => location.pathname')}")
            return v.report()
        log("TV on category-pick — doing NOTHING for ~13s to force the "
            "10s timeout auto-default path")

        # The pick-show cue should have fired on screen open. If it didn't,
        # the SFX tap isn't wired and any later assertion would be a false
        # green — flag inconclusive so we don't pass on an unwired harness.
        time.sleep(0.6)
        early = read_sfx_log(tv)
        if not any(e.get("name") == "sfx_pick_show" for e in early):
            v.inconclusive(
                "SFX tap is live on category-pick",
                f"no sfx_pick_show seen; __sfxLog={early[-5:]}")
            return v.report()
        log(f"SFX tap live (saw sfx_pick_show). __sfxLog so far={len(early)} events")

        # Do NOTHING through the deadline + grace. The TV's kickedRef branch
        # will eventually call load-question (forcing the server auto-default)
        # and navigate to /question. We watch for that navigation as the
        # signal that the timeout path actually executed.
        deadline = time.time() + 18
        left_pick = False
        last = ""
        while time.time() < deadline:
            last = tv.evaluate("() => location.pathname")
            if "/question/" in last:
                left_pick = True
                break
            time.sleep(0.2)

        # REST CORROBORATION: the timeout path must have produced a real
        # question server side (proving the lock-cue condition was exercised,
        # not merely skipped). load-question is idempotent here.
        q_active = False
        last_resp = {}
        for _ in range(12):
            r = requests.post(f"{BASE}/api/sp/load-question/{sc}",
                              json={}, timeout=6)
            try:
                last_resp = r.json()
            except Exception:
                last_resp = {}
            phase = last_resp.get("phase")
            if phase != "category_pick" and last_resp.get("question"):
                q_active = True
                break
            time.sleep(0.4)

        if not (left_pick and q_active):
            # We never actually drove the timeout to resolution — cannot
            # judge the lock cue. inconclusive == failure.
            v.inconclusive(
                "pick-timeout was exercised to question-advance",
                f"left_pick={left_pick} q_active={q_active} "
                f"route={last} resp_phase={last_resp.get('phase')}")
            return v.report()
        log(f"timeout resolved: TV left pick (route={last}) and server "
            f"returned a question. Now checking for the lock cue.")

        # DECISIVE: did the auto-default emit a lock cue? The only path to
        # an sfx_pick_locked entry is onPicked() firing on a 'category_picked'
        # socket. On the current build the timeout emits no socket, so this
        # entry is absent. Give the post-navigation log a beat to flush, then
        # read the full accumulated __sfxLog.
        time.sleep(1.4)
        sfx = read_sfx_log(tv)
        locked_on_pick = [
            e for e in sfx
            if e.get("name") == _PICK_LOCKED_SFX
            and _PICK_PATH in (e.get("route") or "")
        ]
        # Be lenient on route too: a fixed build fires pickLocked() while
        # still on /category-pick (1100ms reveal beat before navigate), but
        # accept any sfx_pick_locked emitted during this pick phase.
        locked_any = [e for e in sfx if e.get("name") == _PICK_LOCKED_SFX]

        v.check(
            "pick-timeout-emits-lock-cue",
            len(locked_on_pick) > 0 or len(locked_any) > 0,
            f"sfx_pick_locked on /category-pick={len(locked_on_pick)} "
            f"any sfx_pick_locked={len(locked_any)} "
            f"total_sfx={len(sfx)} "
            f"names={[e.get('name') for e in sfx]}")

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
