"""Gate for R024 — category-pick timeout must auto-advance the match.

The TV must re-issue loadQuestion when the 10s pick deadline expires;
without that the match hangs at 0s forever (the user's "round 3
category pick went to 0s and stopped completely"). The existing
e2e_full_match always CLICKS a category so it never exercises this
path — this gate deliberately does NOTHING during the pick and asserts
the match still advances.

Gate assertion name: pick-timeout-auto-advances-to-question
Proven: FAIL on pre-fix build, PASS on fix.
"""
from __future__ import annotations

import sys
import time

import requests

from verify_lib import (
    BASE, TV, log, session, pair_and_start, Verifier,
)


def run() -> int:
    v = Verifier()
    with session() as (hub, tv):
        sc = pair_and_start(hub, tv, goto_question=True)
        if not sc:
            v.inconclusive("setup", "no session_code after pairing")
            return v.report()

        # Wait for the TV to reach the round-1 category-pick screen.
        on_pick = False
        for _ in range(40):
            if "/category-pick/" in tv.evaluate("() => location.pathname"):
                on_pick = True
                break
            time.sleep(0.25)
        if not on_pick:
            v.inconclusive(
                "TV reached category-pick screen",
                f"route={tv.evaluate('() => location.pathname')}")
            return v.report()
        log("TV on category-pick — doing NOTHING for ~13s to force the timeout path")

        # Wait past the 10s deadline + grace. With R024 the TV must
        # kick loadQuestion on expiry and navigate to /question.
        deadline = time.time() + 16
        reached_q = False
        last = ""
        while time.time() < deadline:
            last = tv.evaluate("() => location.pathname")
            if "/question/" in last:
                reached_q = True
                break
            time.sleep(0.3)

        # Confirm a real question is actually active server-side.
        q_active = False
        if reached_q:
            for _ in range(12):
                cq = requests.get(f"{BASE}/api/sp/current-question/{sc}",
                                  timeout=4).json()
                if cq.get("active") and cq.get("question_id"):
                    q_active = True
                    break
                time.sleep(0.4)

        v.check("pick-timeout-auto-advances-to-question",
                reached_q and q_active,
                f"route={last} reached_q={reached_q} q_active={q_active}")

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
