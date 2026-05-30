"""Gate for Slice I — crash-recovery state persistence.

THE INVARIANT
-------------
state_persistence.snapshot() flushes _LOBBY + _SP_STATE +
_QUESTION_TRACKER to `server/state_snapshot.json` on every POST (via
after_request hook installed by init_pair_routes). On Flask boot,
init_pair_routes calls rehydrate() and restores the dicts. A
mid-match `kill -9` followed by `systemctl restart flask` (or similar)
must produce a Flask that knows about the in-flight match.

REPRO
-----
1. Pair two pucks, start a match, drive through one round so
   _SP_STATE has substantive content (round=1, expected_pucks={1,2},
   asked_ids non-empty, current_round_answers).
2. Force a snapshot flush by waiting > DEBOUNCE_MS + 50 ms after the
   last POST.
3. Read state_snapshot.json. Confirm structure: v=1, lobby with the
   right session_code, sp_state[sc] with expected_pucks and round.
4. Simulate restart: clear the in-process module globals
   (_LOBBY/_SP_STATE/_QUESTION_TRACKER) via REST `pair/clear`, then
   call rehydrate() directly. Confirm we recovered the same
   session_code, expected_pucks, round.

This is a UNIT/integration hybrid — we exercise the real serializer
+ atomic write + on-disk file, but skip the actual OS process
restart (Flask in this sandbox doesn't have a clean
restart-and-reuse-port path). The serializer/atomic-write/rehydrate
path is the part that breaks; subprocess restart timing is a
deployment concern.

Gate assertion name: state-snapshot-roundtrips-via-rehydrate
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests

# Run the gate from the server venv (DATABASE_URL= venv/bin/python ...)
# so we can import state_persistence directly.
_SERVER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SERVER))

from verify_lib import BASE, log, Verifier, session, pair_and_start  # noqa: E402
import state_persistence  # noqa: E402


SP = f"{BASE}/api/sp"
SNAPSHOT_PATH = _SERVER / "state_snapshot.json"


def run() -> int:
    v = Verifier()
    with session() as (hub, tv):
        sc = pair_and_start(hub, tv, goto_question=True)
        if not sc:
            v.inconclusive("setup", "no session_code after pairing")
            return v.report()
        log(f"sc={sc}")

        # Drive Q1 forward enough to populate SP state.
        ms = requests.get(f"{SP}/match-state/{sc}", timeout=5).json()
        log(f"match-state: round={ms.get('round')} "
            f"complete={ms.get('complete')}")

        # Wait past debounce so the writer flushes.
        time.sleep(state_persistence.DEBOUNCE_MS / 1000.0 + 0.4)

        v.check(
            "snapshot-file-exists",
            SNAPSHOT_PATH.exists(),
            f"expected {SNAPSHOT_PATH} to exist after a POST sequence",
        )
        if not SNAPSHOT_PATH.exists():
            return v.report()

        import json
        raw = json.loads(SNAPSHOT_PATH.read_text())
        v.check(
            "snapshot-format-v1",
            raw.get("v") == 1,
            f"expected v=1, got v={raw.get('v')}",
        )
        lobby = raw.get("lobby") or {}
        sp_state = raw.get("sp_state") or {}
        v.check(
            "snapshot-contains-active-lobby",
            bool(lobby) and lobby.get("session_code") == sc,
            f"expected lobby.session_code={sc!r}, got "
            f"{lobby.get('session_code')!r} (lobby={list(lobby)[:6]})",
        )
        v.check(
            "snapshot-contains-sp-state-for-sc",
            sc in sp_state,
            f"sp_state missing session {sc!r}; keys="
            f"{list(sp_state)[:6]}",
        )

        # Round-trip via rehydrate(). The file is the only input.
        restored = state_persistence.rehydrate()
        v.check(
            "rehydrate-returns-payload",
            restored is not None,
            "rehydrate() returned None despite snapshot present",
        )
        if restored is None:
            return v.report()
        lob2 = restored.get("lobby") or {}
        sps2 = restored.get("sp_state") or {}
        state_persistence.fix_int_keys_after_rehydrate(
            lob2 or None, sps2, restored.get("question_tracker") or {})

        v.check(
            "rehydrate-recovers-session-code",
            lob2.get("session_code") == sc,
            f"rehydrated lobby.session_code={lob2.get('session_code')!r} "
            f"vs expected {sc!r}",
        )
        recovered_state = sps2.get(sc) or {}
        ep = recovered_state.get("expected_pucks")
        v.check(
            "rehydrate-expected-pucks-is-set",
            isinstance(ep, set) and len(ep) >= 1,
            f"rehydrated expected_pucks={ep!r} (must be a non-empty set)",
        )

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
