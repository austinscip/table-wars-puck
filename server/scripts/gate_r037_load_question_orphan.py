"""Gate for R037 — POST /api/sp/load-question/<arbitrary-code> must NOT
auto-create an orphan _SP_STATE / open a phantom category pick for an
unpaired session.

The bug: sp_load_question calls _sp_state_for(session_code), which
unconditionally creates the full _SP_STATE dict for ANY unknown code
with no pairing/lobby check. Live repro confirmed:
  POST /api/sp/load-question/QPHANT9 (never paired) -> HTTP 200 with a
  full category_pick offer (phase:category_pick, picker_puck_id:1,
  fresh 10s deadline, round:1), and a subsequent
  GET /api/sp/match-state/QPHANT9 then reports exists:true, round:0,
  pending_category_pick populated. Any client can spam this to leak
  unbounded in-memory state, and a later real pairing colliding on the
  code would start pre-seeded with a stale pick.

The fix (fixSketch): guard sp_load_question to verify a backing session
(trivia_session row or matching _LOBBY.session_code) exists before
_sp_state_for; return 404/409 for unknown codes; reserve the create
path for sessions started via /api/pair/start.

Decisive assertion name: load-question-rejects-unpaired-session
Kind: server-rest — driven purely with requests against BASE; no browser.
Proven: fail-on-current expected; pass-on-fix.
"""
from __future__ import annotations

import sys
import time

import requests

from verify_lib import BASE, log, Verifier


def run() -> int:
    v = Verifier()

    # Use a code that has NEVER been paired/started. Make it unique per
    # run so a previously-leaked orphan from an earlier invocation can't
    # mask the bug (or, post-fix, can't be mistaken for a fresh reject).
    code = f"QGHOST{int(time.time()) % 100000}"
    log(f"Using never-paired session_code={code}")

    # Clear any lobby so there is definitively no active/backing session.
    try:
        requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)
    except Exception as e:
        v.inconclusive("setup: pair/clear", f"{e!r}")
        return v.report()

    # Pre-condition: the orphan code must not already exist server-side.
    try:
        pre = requests.get(f"{BASE}/api/sp/match-state/{code}", timeout=5)
        pre_json = pre.json()
    except Exception as e:
        v.inconclusive("setup: pre match-state", f"{e!r}")
        return v.report()
    if pre_json.get("exists") is not False:
        v.inconclusive(
            "setup: code starts non-existent",
            f"match-state pre-POST exists={pre_json.get('exists')} (expected False)")
        return v.report()
    log(f"Pre-check OK: {code} reports exists:false before POST")

    # ---- Exercise the bug: POST load-question for the unpaired code. ----
    try:
        resp = requests.post(
            f"{BASE}/api/sp/load-question/{code}", json={}, timeout=8)
    except Exception as e:
        v.inconclusive("POST load-question issued", f"{e!r}")
        return v.report()

    status = resp.status_code
    try:
        body = resp.json()
    except Exception:
        body = {}
    phase = body.get("phase")
    log(f"POST load-question/{code} -> HTTP {status} phase={phase!r} "
        f"body_keys={sorted(body.keys())}")

    # The bug manifests two ways; either one failing is the bug:
    #   (1) the POST returns 200 with a phantom category_pick offer, and/or
    #   (2) the GET match-state afterward shows exists:true (orphan state).
    rejected = status >= 400
    no_phantom_pick = phase != "category_pick"

    # ---- Assert no orphan state was leaked into _SP_STATE. ----
    try:
        post = requests.get(f"{BASE}/api/sp/match-state/{code}", timeout=5)
        post_json = post.json()
    except Exception as e:
        v.inconclusive("post match-state read", f"{e!r}")
        return v.report()
    orphan_exists = post_json.get("exists") is True
    log(f"GET match-state/{code} after POST -> exists={post_json.get('exists')} "
        f"round={post_json.get('round')} "
        f"pending_pick={post_json.get('pending_category_pick')}")

    # Decisive assertion: an unpaired code must be rejected (4xx, no
    # category_pick offer) AND must leave no orphan _SP_STATE behind.
    ok = rejected and no_phantom_pick and not orphan_exists
    v.check(
        "load-question-rejects-unpaired-session",
        ok,
        f"http_status={status} phase={phase!r} rejected={rejected} "
        f"no_phantom_pick={no_phantom_pick} orphan_state_exists={orphan_exists}")

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
