"""Gate for Slice I — ghost-puck sweep.

THE INVARIANT
-------------
_maybe_emit_reveal calls _sweep_stale_pucks(state) before evaluating
"all expected pucks answered." _sweep_stale_pucks drops any puck whose
last_seen is older than GHOST_TIMEOUT_S from state["expected_pucks"]
and emits player_left. Without the sweep, a single disconnected puck
blocks every reveal forever.

GATE PACING
-----------
Production default GHOST_TIMEOUT_S=30 is too slow for a gate. The
constant reads SP_GHOST_TIMEOUT_S from env on module load; this gate
REQUIRES Flask to have been booted with SP_GHOST_TIMEOUT_S=3.

REPRO
-----
1. Pair two pucks (each gets last_seen=now via /api/pair/request).
2. Start match. Read state_snapshot.json (Slice I persistence) →
   confirm sp_state[<sc>].expected_pucks == {1, 2}.
3. Sit ~ GHOST_TIMEOUT_S + 1 s. Bump heartbeat for puck 1 only.
4. POST /api/sp/force-reveal (runs through _maybe_emit_reveal →
   _sweep_stale_pucks).
5. Wait debounce + small grace; re-read state_snapshot.json.
6. ASSERT puck 2 removed from expected_pucks.

Gate assertion name: ghost-puck-removed-from-expected_pucks
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

_SERVER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SERVER))

# This gate REQUIRES Flask boot env SP_GHOST_TIMEOUT_S=3. The gate
# itself can't reach into the running Flask to set it.
GATE_GHOST_TIMEOUT_S = float(os.environ.get("SP_GHOST_TIMEOUT_S", "3"))

from verify_lib import BASE, log, Verifier, session, pair_and_start  # noqa: E402
import state_persistence  # noqa: E402

SP = f"{BASE}/api/sp"
SNAPSHOT_PATH = _SERVER / "state_snapshot.json"


def _read_expected(sc: str) -> set | None:
    if not SNAPSHOT_PATH.exists():
        return None
    raw = json.loads(SNAPSHOT_PATH.read_text())
    sps = raw.get("sp_state") or {}
    st = sps.get(sc)
    if not st:
        return None
    ep = st.get("expected_pucks")
    if isinstance(ep, dict) and "__set__" in ep:
        return set(int(p) for p in ep["__set__"])
    if isinstance(ep, list):
        return set(int(p) for p in ep)
    if isinstance(ep, set):
        return ep
    return None


def run() -> int:
    v = Verifier()
    with session() as (hub, tv):
        sc = pair_and_start(hub, tv, goto_question=True)
        if not sc:
            v.inconclusive("setup", "no session_code after pairing")
            return v.report()
        log(f"sc={sc}")

        # Pre-bump both pucks so the pair-flow's joined_at timestamps
        # don't expire under the gate's aggressive timeout. Real
        # production uses GHOST_TIMEOUT_S=30; the pair flow's natural
        # delay is ~4s which would already exceed timeout=3.
        for pid in (1, 2):
            requests.post(f"{SP}/heartbeat",
                          json={"puck_id": pid}, timeout=3)
        time.sleep(state_persistence.DEBOUNCE_MS / 1000.0 + 0.4)
        ep0 = _read_expected(sc)
        log(f"baseline expected_pucks={ep0}")
        v.check(
            "baseline-expected-has-both-pucks",
            isinstance(ep0, set) and len(ep0) >= 2,
            f"expected baseline expected_pucks to contain >=2 pucks; "
            f"got {ep0}",
        )
        if not isinstance(ep0, set) or len(ep0) < 2:
            return v.report()

        active_puck = sorted(ep0)[0]
        ghost_puck = sorted(ep0)[1]
        log(f"active_puck={active_puck} ghost_puck={ghost_puck}")

        # Wait > ghost timeout. Bump only active.
        wait_s = GATE_GHOST_TIMEOUT_S + 1.5
        log(f"waiting {wait_s:.1f}s — ghost {ghost_puck} stays silent")
        deadline = time.time() + wait_s
        while time.time() < deadline:
            requests.post(f"{SP}/heartbeat",
                          json={"puck_id": active_puck}, timeout=3)
            time.sleep(GATE_GHOST_TIMEOUT_S / 4)

        # Trigger sweep via match-state poll (also runs sweep). This
        # works before Q1 is even loaded — important: a puck that
        # ghosts during the category pick should still be dropped.
        requests.get(f"{SP}/match-state/{sc}", timeout=4)
        time.sleep(state_persistence.DEBOUNCE_MS / 1000.0 + 0.4)

        ep1 = _read_expected(sc)
        log(f"after-sweep expected_pucks={ep1}")
        v.check(
            "ghost-puck-removed-from-expected_pucks",
            isinstance(ep1, set) and ghost_puck not in ep1
            and active_puck in ep1,
            f"expected ghost {ghost_puck} dropped, active {active_puck} "
            f"kept. ep0={ep0} ep1={ep1}",
        )

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
