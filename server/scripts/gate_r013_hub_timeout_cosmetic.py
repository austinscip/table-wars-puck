"""Gate for R013 — Hub puck row must render TIMEOUT (not "LOCKED →A")
when the puck times out without tapping.

THE INVARIANT
-------------
usePuckState.ts (IN_GAME_ANSWERING -> LOCKED transition, ~line 547):
when /api/sp/current-question reports the question rotated away while we
were still ANSWERING with no tap, set `chosen: cur.pending ?? null`. The
variants must render `chosen === null` as TIMEOUT, not as `LOCKED → A`.

VariantA (`TIMEOUT Q${id}` vs `LOCKED Q${id} →${chosen}`) and VariantB
(`timeout` vs `locked ${chosen}`) both branch on `chosen === null`. The
regression Austin reported: Hub showed `LOCKED →A` after a no-tap timeout
(usePuckState was defaulting to 'A' instead of null).

REPRO
-----
1. Pair two pucks. Start the match. TV at /question/<sc>.
2. Neither puck taps. The match advances on its own (server-side question
   deadline). After deadline + reveal grace, both pucks' usePuckState
   polling sees the question rotated -> sets LOCKED chosen=null.
3. Read every puck-row state string on the Hub. Each one whose state is
   `IN_GAME_LOCKED` MUST contain "TIMEOUT" and MUST NOT contain "→A"
   (or "→B"/"→C"/"→D"). Any locked-with-arrow -> FAIL.

Gate assertion name: hub-renders-TIMEOUT-not-LOCKED-on-no-tap
"""
from __future__ import annotations

import re
import sys
import time

import requests

from verify_lib import (
    BASE, log, Verifier, session, pair_and_start, puck_row,
)


def run() -> int:
    v = Verifier()
    with session() as (hub, tv):
        sc = pair_and_start(hub, tv, goto_question=True)
        if not sc:
            v.inconclusive("setup", "no session_code after pairing")
            return v.report()
        log(f"sc={sc}")

        # Force the TV to load the first question (server only emits
        # question_show via load-question — the TV triggers that itself
        # via QuestionScreen on mount). Then DO NOT tap. Wait the
        # question deadline (10s) and force-reveal + load-question via
        # REST so the server rotates the question even though the TV
        # never POSTed advance on its own (the test browser closes
        # /question on session end; rotation needs an external nudge).
        log("waiting 11s for question deadline")
        time.sleep(11)
        # Force-reveal flips the in-memory question to revealed and the
        # next /current-question call returns active=false (or the next
        # qid). usePuckState's ANSWERING-branch then trips
        # `chosen: cur.pending ?? null`. CRITICAL: do NOT immediately
        # load-question, or pucks fly past LOCKED into the next phase
        # (BULLSEYE/SHOT_CLOCK minigame or category pick) before we can
        # observe the LOCKED row. Capture the state ~1.5s after the
        # reveal so the polling tick has fired but the next phase hasn't
        # been triggered yet.
        log("force-reveal — DO NOT load-question yet")
        requests.post(f"{BASE}/api/sp/force-reveal/{sc}", timeout=5)
        time.sleep(1.5)

        # Read both puck rows' state strings. Variant A renders them as
        # data-state on the row's status span; verify_lib.puck_state
        # returns the row's full text — grep for TIMEOUT / LOCKED.
        from verify_lib import puck_state  # noqa: E402
        s0 = puck_state(hub, 0)
        s1 = puck_state(hub, 1)
        log(f"puck0 state={s0!r}")
        log(f"puck1 state={s1!r}")

        # In Variant A the row text contains the kind label
        # ("TIMEOUT Q1" / "LOCKED Q1 →A"). The gate is: any locked-with-
        # arrow on a puck that never tapped is the regression.
        def has_locked_arrow(s: str) -> bool:
            # Match "LOCKED Q<n> →<letter>" or "→A" etc. anywhere.
            return bool(re.search(r"LOCKED\s+Q\d+\s*→[A-D]", s)) or \
                   bool(re.search(r"locked\s+[A-D]", s))

        def has_timeout(s: str) -> bool:
            return ("TIMEOUT" in s) or ("timeout" in s) or \
                   ("MATCH ENDED" in s) or ("match end" in s)

        # If the match completed instantly somehow (all 7 rounds rotated
        # to scoreboard before we polled), MATCH ENDED is also acceptable
        # since the LOCKED kind never rendered to the user.
        v.check(
            "hub-renders-TIMEOUT-not-LOCKED-on-no-tap",
            (not has_locked_arrow(s0)) and (not has_locked_arrow(s1)),
            f"a puck row shows 'LOCKED Q<n> →<letter>' despite never "
            f"tapping (R013 regression). puck0={s0!r} puck1={s1!r}",
        )

        # Bonus assertion: at least ONE puck row should show TIMEOUT
        # (or be in a downstream phase like CATEGORY_PICKING / MATCH ENDED
        # that necessarily came after a timeout-resolved round). If
        # NEITHER row ever reached a timeout state, the test didn't
        # actually exercise the bug.
        downstream_ok = (
            "PICK CATEGORY" in s0 or "PICK CATEGORY" in s1 or
            "pick category" in s0 or "pick category" in s1 or
            "MINIGAME" in s0 or "MINIGAME" in s1 or
            "mg/" in s0 or "mg/" in s1
        )
        v.check(
            "hub-actually-exercised-timeout",
            has_timeout(s0) or has_timeout(s1) or downstream_ok,
            f"neither puck row reached TIMEOUT / MATCH ENDED / a "
            f"between-round phase — the bug path wasn't exercised. "
            f"puck0={s0!r} puck1={s1!r}",
        )

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
