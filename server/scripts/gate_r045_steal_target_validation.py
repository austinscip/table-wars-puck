"""Gate for R045 — STEAL activate must validate target_puck_id.

Bug (server/pair_routes.py sp_power_up_activate, STEAL branch ~1666-1682):
the activate endpoint only checks target_puck_id is non-None and
int-coercible. It never checks the target is in state['expected_pucks']
nor that target != firer. So:
  * STEAL at a phantom puck_id (e.g. 999) returns ok:true and the
    one-shot item is REMOVED from inventory. At reveal,
    _apply_power_up_arms only processes targets present in `answers`,
    so the steal silently no-ops — the player loses the power-up for
    zero effect with no error.
  * Self-steal (target == firer) is accepted (net 0, but emits a bogus
    STEAL power_up_resolved with firer == target).

Fix sketch: validate `int(target_puck_id) in (state['expected_pucks'])`
and `target_puck_id != puck_id`; return 400 'invalid target' and do
NOT remove the item from inventory on failure.

Gate assertion name (decisive): steal-target-validated
Proven: fail-on-current expected; pass-on-fix.

kind: server-rest — driven purely with requests against BASE. No
browser. Pairs two pucks over the REST pair flow, drives a real match
round-by-round, wins minigames until a STEAL power-up lands in a
puck's inventory, opens the next between-rounds pick phase, then
exercises the two invalid-target activations.
"""
from __future__ import annotations

import sys
import time

import requests

from verify_lib import BASE, log, Verifier

SP = f"{BASE}/api/sp"
PAIR = f"{BASE}/api/pair"
HOST = 1001
JOIN = 1002
TIMEOUT = 8


# ---------------------------------------------------------------------------
# REST pairing (no browser): host /request, joiner /request, host /confirm,
# host /start. Yields a session_code whose expected_pucks == {HOST, JOIN}.
# ---------------------------------------------------------------------------

def _pair_via_rest() -> str | None:
    requests.post(f"{PAIR}/clear", json={}, timeout=TIMEOUT)
    r = requests.post(f"{PAIR}/request", json={"puck_id": HOST}, timeout=TIMEOUT)
    if not r.ok:
        log(f"host /request failed: {r.status_code} {r.text[:120]}")
        return None
    code = r.json().get("pair_code")
    requests.post(f"{PAIR}/request", json={"puck_id": JOIN}, timeout=TIMEOUT)
    requests.post(f"{PAIR}/confirm",
                  json={"puck_id": HOST, "code": code}, timeout=TIMEOUT)
    s = requests.post(f"{PAIR}/start", json={"puck_id": HOST}, timeout=TIMEOUT)
    if not s.ok:
        log(f"/start failed: {s.status_code} {s.text[:160]}")
        return None
    return s.json().get("session_code")


def _inventory(sc: str, puck_id: int) -> list[dict]:
    r = requests.get(f"{SP}/inventory/{sc}",
                     params={"puck_id": puck_id}, timeout=TIMEOUT)
    try:
        return r.json().get("items", [])
    except Exception:
        return []


def _steal_item(sc: str, puck_id: int) -> dict | None:
    for it in _inventory(sc, puck_id):
        if it.get("type") == "STEAL":
            return it
    return None


def _answer_both(sc: str, qid: int) -> None:
    for pid in (HOST, JOIN):
        requests.post(f"{SP}/answer", json={
            "session_code": sc, "puck_id": pid,
            "question_id": qid, "answer": "A",
            "response_time_ms": 1500,
        }, timeout=TIMEOUT)


def _resolve_pick(sc: str, phase: dict) -> None:
    """Lock the first offered category as the designated picker."""
    offer = phase.get("offer") or []
    picker = phase.get("picker_puck_id")
    if offer and picker is not None:
        requests.post(f"{SP}/select-category/{sc}", json={
            "puck_id": picker, "category_id": int(offer[0]["id"]),
        }, timeout=TIMEOUT)
    else:
        # No offer — let the deadline auto-default by polling load-question.
        time.sleep(0.1)


def _win_minigame(sc: str, phase: dict) -> None:
    """Make HOST the winner so HOST receives the random power-up grant.
    BULLSEYE: fire HOST at the target quadrant fast (t_ms small); JOIN
    fires the wrong quadrant for 0. SHOT_CLOCK: HOST fires near the
    green-zone center (t_ms=1500 -> phase 0.5); JOIN fires off-center."""
    flavor = phase.get("flavor")
    if flavor == "BULLSEYE":
        tgt = phase.get("target_quadrant") or "A"
        wrong = next(q for q in ("A", "B", "C", "D") if q != tgt)
        requests.post(f"{SP}/minigame/fire", json={
            "session_code": sc, "puck_id": HOST, "t_ms": 100, "quadrant": tgt,
        }, timeout=TIMEOUT)
        requests.post(f"{SP}/minigame/fire", json={
            "session_code": sc, "puck_id": JOIN, "t_ms": 7000, "quadrant": wrong,
        }, timeout=TIMEOUT)
    else:  # SHOT_CLOCK
        requests.post(f"{SP}/minigame/fire", json={
            "session_code": sc, "puck_id": HOST, "t_ms": 1500,
        }, timeout=TIMEOUT)
        requests.post(f"{SP}/minigame/fire", json={
            "session_code": sc, "puck_id": JOIN, "t_ms": 0,
        }, timeout=TIMEOUT)
    # Belt-and-suspenders: force-resolve in case a fire didn't land.
    requests.post(f"{SP}/minigame/finish/{sc}", json={}, timeout=TIMEOUT)


def _drive_until_steal(sc: str, max_rounds: int = 14) -> dict | None:
    """Advance the match round-by-round. Whenever a between-rounds phase
    is open AND HOST already holds a STEAL, return (phase, item) so the
    caller can fire the bug WHILE the phase is pending. Otherwise resolve
    the phase / answer the question and continue. Returns a dict
    {phase, item} or None if no STEAL ever landed."""
    for _ in range(max_rounds):
        r = requests.post(f"{SP}/load-question/{sc}", json={}, timeout=TIMEOUT)
        if not r.ok:
            # match_complete (409) or no questions — stop this attempt.
            return None
        body = r.json()
        phase = body.get("phase")
        if phase in ("category_pick", "minigame"):
            # A between-rounds phase is open right now. If HOST holds a
            # STEAL, this is the exact window the bug lives in.
            item = _steal_item(sc, HOST)
            if item is not None:
                return {"phase": phase, "phase_body": body, "item": item}
            # No steal yet — resolve the phase and keep going.
            if phase == "category_pick":
                _resolve_pick(sc, body)
            else:
                _win_minigame(sc, body)
            time.sleep(0.15)
            continue
        # A question was loaded — answer it for both pucks to reveal.
        q = body.get("question") or {}
        qid = q.get("id")
        if qid is None:
            return None
        _answer_both(sc, int(qid))
        time.sleep(0.15)
    return None


def run() -> int:
    v = Verifier()

    captured = None
    # The grant is random.choice over 4 types per minigame win, with 3
    # minigame rounds per match (~58% chance of >=1 STEAL/match). Retry
    # whole matches until a STEAL lands during an open between-rounds
    # phase. If none ever lands, the gate is INCONCLUSIVE (= failure).
    for attempt in range(8):
        sc = _pair_via_rest()
        if not sc:
            log(f"attempt {attempt}: pairing failed")
            continue
        log(f"attempt {attempt}: session={sc}")
        captured = _drive_until_steal(sc)
        if captured:
            log(f"attempt {attempt}: captured STEAL during "
                f"{captured['phase']} phase, item={captured['item']}")
            break
        # Clean up before the next attempt.
        requests.post(f"{PAIR}/clear", json={}, timeout=TIMEOUT)

    if not captured:
        v.inconclusive(
            "steal-target-validated",
            "could not obtain a STEAL power-up during a between-rounds "
            "phase across 8 match attempts — bug condition not exercised")
        return v.report()

    item_id = captured["item"]["id"]

    # Sanity: confirm HOST really holds this STEAL before we fire.
    pre = _steal_item(sc, HOST)
    if pre is None or pre.get("id") != item_id:
        v.inconclusive("steal-target-validated",
                       "STEAL vanished from inventory before activation")
        return v.report()

    # --- Decisive probe 1: phantom (non-participant) target -----------------
    # 999 is not in expected_pucks ({HOST, JOIN}). The fix must reject it
    # with 400 and KEEP the item; the buggy build returns ok:true and
    # consumes the one-shot item for zero effect.
    r_phantom = requests.post(f"{SP}/power-up/activate", json={
        "session_code": sc, "puck_id": HOST,
        "item_id": item_id, "target_puck_id": 999,
    }, timeout=TIMEOUT)
    phantom_status = r_phantom.status_code
    phantom_ok = (r_phantom.json() or {}).get("ok") if r_phantom.content else None
    item_after_phantom = _steal_item(sc, HOST)
    item_retained = (item_after_phantom is not None
                     and item_after_phantom.get("id") == item_id)

    phantom_rejected = (phantom_status == 400) and (phantom_ok is not True) \
        and item_retained
    log(f"phantom target 999 -> status={phantom_status} ok={phantom_ok} "
        f"item_retained={item_retained}")

    # --- Decisive probe 2: self-steal (target == firer) ---------------------
    # Only meaningful if the item still exists (it should, post-fix). If the
    # buggy build already consumed it in probe 1, we cannot re-fire, so we
    # capture self-steal acceptance via a fresh check only when retained.
    self_rejected = None
    if item_retained:
        r_self = requests.post(f"{SP}/power-up/activate", json={
            "session_code": sc, "puck_id": HOST,
            "item_id": item_id, "target_puck_id": HOST,
        }, timeout=TIMEOUT)
        self_status = r_self.status_code
        self_ok = (r_self.json() or {}).get("ok") if r_self.content else None
        item_after_self = _steal_item(sc, HOST)
        self_retained = (item_after_self is not None
                         and item_after_self.get("id") == item_id)
        self_rejected = (self_status == 400) and (self_ok is not True) \
            and self_retained
        log(f"self target {HOST} -> status={self_status} ok={self_ok} "
            f"item_retained={self_retained}")
    else:
        # The buggy build already consumed the item on the phantom probe,
        # so self-steal can't be re-tested with the same item. The phantom
        # failure alone proves the bug; record self as not-evaluated.
        log("self-steal not re-tested: item was consumed by phantom probe "
            "(buggy build) — phantom failure already proves the bug")

    # Decisive assertion: BOTH invalid targets must be rejected (400, item
    # retained). On the buggy build the phantom probe already fails this
    # (ok:true, item consumed), so the gate goes red. On the fixed build
    # both probes return 400 and keep the item, so the gate goes green.
    decisive = phantom_rejected and (self_rejected is True)
    v.check(
        "steal-target-validated",
        decisive,
        f"phantom_rejected={phantom_rejected} self_rejected={self_rejected} "
        f"(both must be 400 + item retained)")

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
