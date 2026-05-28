"""Gate for R043 — POST /api/sp/reset/<code> must not fabricate phantom state.

Bug: sp_reset (server/pair_routes.py:1442) unconditionally writes
_SP_STATE[code] with no trivia_sessions / existing-session guard. So a
reset against a code that was never paired returns {ok:true} HTTP 200,
and GET /api/sp/match-state/<code> flips exists:false -> exists:true
(round:0, complete:false). The `exists` flag is load-bearing for puck
recovery: usePuckState MATCH_ENDED treats exists===false -> IDLE but
exists===true && !complete -> IN_GAME_IDLE. A spurious/duplicate reset
(two pucks both Play-Again, or a reset racing a Hub Reset-all that
already wiped the session) re-creates exists:true, so a puck that should
drop to IDLE instead drops to IN_GAME_IDLE and waits forever for a
current-question that never arrives.

Repro (pure server-rest, no browser):
  1) Pick a code that was never paired. Confirm match-state exists:false.
  2) POST reset/<code>.
  3) Re-GET match-state/<code>. With the bug, exists flipped to true.
     With the fix, reset is rejected (404/409) and exists stays false.

Gate assertion name: reset-rejects-unknown-session
Proven: fail-on-current expected; pass-on-fix.
"""
from __future__ import annotations

import sys
import time

import requests

from verify_lib import BASE, log, Verifier


def _match_state(code: str) -> dict:
    return requests.get(f"{BASE}/api/sp/match-state/{code}", timeout=5).json()


def run() -> int:
    v = Verifier()

    # A code that was never paired and has no _SP_STATE entry. Uniquify
    # so reruns (and any stale state from prior runs) can't pollute it.
    code = f"R043PHANTOM{int(time.time())}"
    log(f"Using never-paired session_code={code}")

    # --- Step 1: baseline must be exists:false (no session, no state). ---
    before = _match_state(code)
    log(f"match-state before reset: {before}")
    if before.get("exists") is not False:
        # If this isn't a clean unknown code we can't faithfully exercise
        # the bug — inconclusive counts as failure.
        v.inconclusive(
            "baseline unknown-session is exists:false",
            f"expected exists:false for fresh code, got {before}")
        return v.report()
    v.check("baseline unknown-session is exists:false",
            before.get("exists") is False,
            f"exists={before.get('exists')}")

    # --- Step 2: POST reset against the unknown code. ---
    resp = requests.post(f"{BASE}/api/sp/reset/{code}",
                         json={}, timeout=5)
    try:
        body = resp.json()
    except Exception:
        body = {"_raw": resp.text}
    log(f"POST reset -> HTTP {resp.status_code} {body}")

    # --- Step 3: the decisive check — match-state must NOT have been
    # fabricated. With the fix, reset rejects the unknown session
    # (404/409) and never writes _SP_STATE, so exists stays false. ---
    after = _match_state(code)
    log(f"match-state after reset: {after}")

    exists_after = after.get("exists")
    # The faithful signal: a reset against a session that was never
    # paired must leave exists:false. If exists flipped to true, a puck
    # polling this wiped session would recover to IN_GAME_IDLE instead of
    # IDLE and hang forever.
    v.check("reset-rejects-unknown-session",
            exists_after is False,
            f"reset HTTP {resp.status_code}; match-state.exists after "
            f"reset={exists_after} (must be False; True = phantom state, "
            f"puck would hang in IN_GAME_IDLE)")

    # Supporting signal (not the decisive gate): a correct guard rejects
    # the POST with 404/409 rather than returning a 200 {ok:true} that
    # falsely implies a session was reset. This is informational; the
    # exists-flag check above is what fails the build.
    v.check("reset of unknown session is not a 200 ok",
            resp.status_code in (404, 409),
            f"HTTP {resp.status_code} body={body}")

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
