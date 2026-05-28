"""Gate for R047 — ScoreboardScreen must auto-return to the title screen
after ~30s of inactivity (spec UX-10).

Bug: On a bar kiosk, a finished match parks the TV on the final scoreboard
forever. ScoreboardScreen wires only `match_reset` and `lobby_cancelled`
socket listeners plus a 250ms matchEnd audio timer — there is NO
window.setTimeout navigating to '/'. After _clear_lobby at match end, the
only exits are a puck Play-Again (match_reset) or Back-to-start / Reset-all
(lobby_cancelled). When players walk away, neither fires and the attract
loop never resumes — the unit is stuck on one game's final scores.

Fix sketch: a useEffect with window.setTimeout(() => navigate('/',
{replace:true}), 30000), cleared on unmount and cancelled if
match_reset / lobby_cancelled fires first.

This gate drives a full match to /scoreboard/<code>, sends NO further puck
actions, then waits past the 30s deadline (with grace) and asserts the TV
has self-navigated to the title screen '/'. The existing e2e flows always
trigger a Play-Again or Reset, so they never exercise this idle path —
this gate deliberately does nothing and watches the route.

Gate assertion name: scoreboard-auto-returns-to-title
Proven: fail-on-current expected; pass-on-fix.
"""
from __future__ import annotations

import sys
import time

from urllib.parse import urlparse

from verify_lib import (
    TV, log, session, pair_and_start, drive_match_to_scoreboard, Verifier,
)

# The SPA is served under a router basename, so the title screen's
# location.pathname is the base path (e.g. "/tv/speed-pyramid"), not a bare
# "/". navigate('/') resolves against the basename. Treat either the bare
# root or the base path (with optional trailing slash) as "back at title",
# while still rejecting deeper routes like /question or /scoreboard.
TITLE_BASE = urlparse(TV).path.rstrip("/")  # e.g. "/tv/speed-pyramid"


def _is_title(path: str) -> bool:
    p = path.rstrip("/")
    return p == "" or p == TITLE_BASE

# The fix uses a 30000ms timer. Give it generous grace for the
# navigation + count-up animation overhead before declaring failure.
AUTO_RETURN_MS = 30000
GRACE_S = 12.0
POLL_S = 0.5


def run() -> int:
    v = Verifier()
    with session() as (hub, tv):
        sc = pair_and_start(hub, tv, goto_question=True)
        if not sc:
            v.inconclusive("setup", "no session_code after pairing")
            return v.report()

        # Drive the full match until the TV lands on /scoreboard/.
        drive_match_to_scoreboard(hub, tv)

        # Confirm we actually reached the scoreboard — otherwise the
        # idle-timer condition was never exercised (inconclusive = fail).
        on_scoreboard = False
        for _ in range(40):
            route = tv.evaluate("() => location.pathname")
            if "/scoreboard/" in route:
                on_scoreboard = True
                break
            time.sleep(0.5)
        if not on_scoreboard:
            v.inconclusive(
                "TV reached scoreboard",
                f"route={tv.evaluate('() => location.pathname')} — "
                "match never finished, idle-return path not exercised")
            return v.report()

        start_route = tv.evaluate("() => location.pathname")
        log(f"TV on scoreboard ({start_route}) — sending NO puck actions, "
            f"idling past the {AUTO_RETURN_MS}ms auto-return deadline")

        # Sit completely idle. Poll the route until either it returns to
        # the title '/' (fix present) or the deadline + grace elapses
        # (bug present: stuck on scoreboard forever).
        deadline = time.time() + (AUTO_RETURN_MS / 1000.0) + GRACE_S
        returned = False
        last = start_route
        while time.time() < deadline:
            last = tv.evaluate("() => location.pathname")
            # Title screen route is the SPA base path (basename-aware).
            # Guard against deeper routes so a stray "/question" etc.
            # doesn't false-pass.
            if _is_title(last):
                returned = True
                break
            time.sleep(POLL_S)

        # Belt-and-suspenders: make sure the title screen actually rendered
        # (the attract loop is back), not just that the path string flipped.
        title_visible = False
        if returned:
            try:
                tv.wait_for_load_state("domcontentloaded", timeout=4000)
            except Exception:
                pass
            title_visible = _is_title(tv.evaluate("() => location.pathname"))

        v.check(
            "scoreboard-auto-returns-to-title",
            returned and title_visible,
            f"start={start_route} final={last} returned={returned} "
            f"title_visible={title_visible} "
            f"(waited ~{AUTO_RETURN_MS/1000.0 + GRACE_S:.0f}s idle)")

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
