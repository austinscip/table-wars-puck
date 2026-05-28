"""Gate for R036 — force-reveal returning HTTP 400 must still advance the match.

THE BUG
-------
QuestionScreen.tsx arms a force-reveal fallback timer (lines 206-215):

    api.sp.forceReveal(sc)
      .then(() => { scheduleAdvanceToNextQuestion() })
      .catch(() => {})

api.ts `postJson` THROWS on any non-2xx. The server's sp_force_reveal
returns 400 {ok:false, reason:'no current question'} whenever
current_question_id is None — which happens when the round already
advanced or _SP_STATE was wiped by a peer Play-Again / reset / restart
while the socket `reveal` was missed or raced. On that 400 the `.then`
never runs, scheduleAdvanceToNextQuestion() is never called, and the
empty `.catch` hides the failure. The TV sits on the revealed question
forever. This is exactly the scenario the force-reveal fallback exists
to protect, so the bug defeats the safety net precisely when it matters.

WHAT THIS GATE DOES
-------------------
1. (server REST, cheap + deterministic) Pair + drive to an active
   question, then POST /api/sp/reset/<code> to wipe current_question_id
   and assert POST /api/sp/force-reveal/<code> returns HTTP 400. This
   PROVES the precondition the client mishandles actually exists live.
   If this 400 cannot be produced, the bug cannot be exercised and the
   decisive check is marked inconclusive (== failure).

2. (browser) Drive a SECOND match to an active question with the
   force-reveal fallback timer armed on the TV. From a REST client wipe
   current_question_id via /api/sp/reset just AFTER the timer is armed
   but BEFORE it fires. When the TV's force-reveal timer fires it hits
   the 400. Assert the TV ADVANCES off the stranded question anyway
   (route leaves the same /question/<sc>?qid, or current_question_id
   becomes non-None again, or it lands on category-pick/minigame/
   scoreboard). On the CURRENT build the empty .catch swallows the 400
   and the TV never advances -> FAIL. With the fix (.finally / both
   .then+.catch, or sp_force_reveal returning 200 {emitted:false} on no
   current question) the advance fires -> PASS.

Gate assertion name: force-reveal-failure-still-advances
Proven: fail-on-current expected; pass-on-fix.
"""
from __future__ import annotations

import sys
import time

import requests

from verify_lib import (
    BASE, TV, log, session, pair_and_start, drive_match_to_scoreboard,
    Verifier,
)


def _force_reveal(sc: str):
    return requests.post(f"{BASE}/api/sp/force-reveal/{sc}", json={}, timeout=5)


def _reset(sc: str):
    return requests.post(f"{BASE}/api/sp/reset/{sc}", json={}, timeout=5)


def _match_state(sc: str) -> dict:
    try:
        return requests.get(f"{BASE}/api/sp/match-state/{sc}", timeout=5).json()
    except Exception:
        return {}


def _current_question(sc: str) -> dict:
    try:
        return requests.get(
            f"{BASE}/api/sp/current-question/{sc}", timeout=5).json()
    except Exception:
        return {}


def _wait_for_active_question(sc: str, hub, tv, timeout_s: float = 60.0) -> bool:
    """Drive a single match until /api/sp/current-question reports an
    active question_id, with the TV parked on /question/<sc>. Uses the
    phase driver's resolvers but answers no questions so the round stays
    open (force-reveal timer stays meaningful). Returns True if reached."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        cq = _current_question(sc)
        route = tv.evaluate("() => location.pathname")
        if cq.get("active") and cq.get("question_id") and "/question/" in route:
            return True
        # Resolve any blocking pick/minigame phase so a real question can
        # become active, but never answer (we want the round held open).
        s0 = ""
        s1 = ""
        try:
            from verify_lib import puck_state
            s0 = puck_state(hub, 0)
            s1 = puck_state(hub, 1)
        except Exception:
            pass
        if "PICK CATEGORY" in (s0 + s1) or "pick category" in (s0 + s1).lower():
            from verify_lib import _resolve_pick
            _resolve_pick(hub)
            time.sleep(1.0)
            continue
        if "MINIGAME" in (s0 + s1) or "mg/" in (s0 + s1):
            from verify_lib import _resolve_minigame
            _resolve_minigame(hub)
            time.sleep(2.0)
            continue
        time.sleep(0.5)
    return False


def run() -> int:
    v = Verifier()

    # ------------------------------------------------------------------
    # PART 1 — server REST: prove force-reveal returns 400 on no-current-
    # question. This is the precondition the client's .catch swallows.
    # ------------------------------------------------------------------
    with session() as (hub, tv):
        sc = pair_and_start(hub, tv, goto_question=True)
        if not sc:
            v.inconclusive("setup-part1", "no session_code after pairing")
            return v.report()

        if not _wait_for_active_question(sc, hub, tv):
            v.inconclusive(
                "force-reveal-400-precondition",
                "could not drive to an active question to set up the wipe")
            return v.report()

        # Wipe current_question_id exactly the way a peer Play-Again /
        # restart does. After this, force-reveal must report 400.
        r_reset = _reset(sc)
        log(f"reset -> HTTP {r_reset.status_code} {r_reset.text[:120]}")
        time.sleep(0.4)

        r_fr = _force_reveal(sc)
        body = {}
        try:
            body = r_fr.json()
        except Exception:
            pass
        log(f"force-reveal (no current q) -> HTTP {r_fr.status_code} {body}")
        precondition_400 = (
            r_fr.status_code == 400 and body.get("ok") is False
        )
        # NOTE: this is a precondition probe, not the decisive gate. If a
        # FIX changes the server to return 200 {emitted:false} instead,
        # the precondition is satisfied differently and Part 2 still
        # decides. So we only INCONCLUSIVE here if neither 400 nor a
        # graceful 200 happened (i.e. the path could not be exercised).
        graceful_200 = (
            r_fr.status_code == 200 and body.get("ok") is True
        )
        if not (precondition_400 or graceful_200):
            v.inconclusive(
                "force-reveal-400-precondition",
                f"force-reveal on wiped state returned unexpected "
                f"HTTP {r_fr.status_code} {body}; cannot exercise bug")
            return v.report()
        log("Part 1 OK: force-reveal-on-no-current-question path is reachable "
            f"(400={precondition_400}, graceful_200={graceful_200})")

    # ------------------------------------------------------------------
    # PART 2 — browser: drive to an active question, arm the TV force-
    # reveal timer, wipe current_question_id from a REST peer just before
    # the timer fires, then assert the TV ADVANCES despite the 400.
    # ------------------------------------------------------------------
    with session() as (hub, tv):
        sc = pair_and_start(hub, tv, goto_question=True)
        if not sc:
            v.inconclusive("setup-part2", "no session_code after pairing")
            return v.report()

        if not _wait_for_active_question(sc, hub, tv):
            v.inconclusive(
                "force-reveal-failure-still-advances",
                "could not drive to an active question on TV")
            return v.report()

        start_route = tv.evaluate("() => location.pathname")
        start_qid = _current_question(sc).get("question_id")
        log(f"TV parked on {start_route}, active qid={start_qid}; "
            "force-reveal fallback timer is armed")

        # The force-reveal timer is armed for ~ time_limit (default 15s)
        # + 800ms after beginAnswering. We want the wipe to land AFTER the
        # timer is armed but BEFORE it fires. Wipe now (timer already
        # armed once the TV is on the question), so when the timer fires
        # it will hit the 400 path.
        r_reset = _reset(sc)
        log(f"reset (wipe current_question_id) -> HTTP {r_reset.status_code}")

        # Now WAIT past the worst-case timer (time_limit ~15s + grace) +
        # the REVEAL_HOLD_MS (2500ms) advance delay. On a fixed build the
        # force-reveal 400 still schedules the advance, which fires
        # loadQuestion after the hold and either re-establishes a current
        # question, moves to category-pick/minigame, or (when the match
        # cannot continue) navigates to /scoreboard. Any of those means
        # the TV did NOT strand. On the current build none happen.
        advanced = False
        end_route = start_route
        new_qid = None
        deadline = time.time() + 40  # > 15s timer + 2.5s hold + slop
        while time.time() < deadline:
            end_route = tv.evaluate("() => location.pathname")
            cq = _current_question(sc)
            new_qid = cq.get("question_id") if cq.get("active") else None
            left_question = "/question/" not in end_route
            requestion = (
                "/question/" in end_route
                and new_qid is not None
                and new_qid != start_qid
            )
            if left_question or requestion:
                advanced = True
                break
            time.sleep(0.5)

        v.check(
            "force-reveal-failure-still-advances",
            advanced,
            f"start_route={start_route} start_qid={start_qid} "
            f"end_route={end_route} new_qid={new_qid} advanced={advanced} "
            "(current build: empty .catch swallows the 400 -> TV strands; "
            "fix: .finally/200 path still calls scheduleAdvanceToNextQuestion)",
        )

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
