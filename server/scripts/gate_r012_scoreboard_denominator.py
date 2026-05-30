"""Gate for R012 — Scoreboard 'correct' denominator must be total_rounds,
NOT the per-puck answered count.

THE INVARIANT
-------------
ScoreboardScreen renders one line per player:

    Puck #{p.puck_id} · {p.correct}/{results.total_rounds} correct

results.total_rounds is the SP_TOTAL_ROUNDS constant (7). Denominator
MUST always be 7 regardless of how many rounds the puck actually
answered (timeouts, leaves, disconnects).

REPRO
-----
1. Pair two pucks via Hub UI. Drive through the full match to
   /scoreboard/<sc> using the standard phase driver (answers letter
   'A' every round — some will be wrong, all will be ANSWERED so the
   answered-count differs round-by-round across runs).
2. Read TV body innerText. Find every `<correct>/<denom> correct`
   substring with a regex. For each line: denom MUST == "7". Any
   denom != "7" -> FAIL (regression: showed answered count not
   total_rounds).

Gate assertion name: scoreboard-denominator-is-total-rounds
"""
from __future__ import annotations

import re
import sys
import time

from verify_lib import (
    BASE, log, Verifier, session, pair_and_start, drive_match_to_scoreboard,
)


def run() -> int:
    v = Verifier()
    with session() as (hub, tv):
        sc = pair_and_start(hub, tv, goto_question=True)
        if not sc:
            v.inconclusive("setup", "no session_code after pairing")
            return v.report()
        log(f"sc={sc}")

        drive_match_to_scoreboard(hub, tv)
        # Belt-and-suspenders — TV might be in /question still mid-reveal.
        for _ in range(15):
            route = tv.evaluate("() => location.pathname")
            if "/scoreboard/" in route:
                break
            time.sleep(0.5)
        route = tv.evaluate("() => location.pathname")
        log(f"TV route={route}")

        if "/scoreboard/" not in route:
            # Force-navigate so the gate still gives a verdict instead of
            # silently inconclusive on a stuck advance.
            tv.goto(f"{BASE}/tv/speed-pyramid/scoreboard/{sc}",
                    wait_until="domcontentloaded")
            time.sleep(2.5)

        body = tv.evaluate("() => document.body.innerText") or ""
        # Pattern: "<num>/<num> correct" — capture both numerators and
        # denominators. Use word boundaries to avoid catching the round
        # progress dots etc.
        matches = re.findall(r"\b(\d+)\s*/\s*(\d+)\s*correct\b", body)
        log(f"correct-patterns found: {matches}")

        v.check(
            "scoreboard-shows-correct-patterns",
            len(matches) > 0,
            f"no '_/_ correct' pattern in body — TV may not be on "
            f"scoreboard or layout changed. body[:400]={body[:400]!r}",
        )

        bad = [(n, d) for (n, d) in matches if d != "7"]
        v.check(
            "scoreboard-denominator-is-total-rounds",
            not bad,
            f"denominator != 7 in patterns: {bad} (all patterns: {matches})",
        )

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
