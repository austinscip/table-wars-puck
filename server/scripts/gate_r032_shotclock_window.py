"""Gate for R032 — SHOT_CLOCK fire must reject fires past the deadline.

BUG (server-rest, high): pair_routes.py _score_minigame_fire SHOT_CLOCK
branch (840-848) computes pos=(t_ms % cycle_ms)/cycle_ms and scores purely
on distance from the green-zone center, with NO upper time-window guard.
BULLSEYE guards `if t_ms < 0 or t_ms > duration_ms: return 0` (line 832);
SHOT_CLOCK does not. A puck that fires AFTER the 8s deadline whose
(t_ms % cycle) happens to land near cycle/2 still scores up to ~1000 in the
TV's deadline+1s slop window (and worse under socket lag). sp_minigame_fire
performs no deadline check (it only rejects when no minigame is pending),
and the puck floors t_ms at 0 but never caps it (usePuckState.ts:254).

GATE ASSERTION NAME: shotclock-late-fire-scores-zero

Strategy (no browser — pure REST against http://localhost:5002):
  1. Pair two pucks and start a match entirely via /api/pair/* REST.
  2. Drive rounds 1..3 via /api/sp/load-question + /api/sp/answer, resolving
     the round-2 BULLSEYE minigame along the way, until /api/sp/load-question
     returns phase=minigame flavor=SHOT_CLOCK (fires BEFORE round 4).
  3. Read started_at + cycle_ms + duration_s from /api/sp/minigame/state.
  4. POST /api/sp/minigame/fire with t_ms WELL past duration_ms but with
     (t_ms % cycle_ms) == cycle_ms/2 (dead center of the green zone). On the
     buggy build this scores ~1000; the guard must make it 0.
     => decisive assertion: response points == 0.
  5. Belt-and-suspenders unit control on _score_minigame_fire: a synthetic
     late BULLSEYE fire (t_ms > duration) already returns 0 (the guard that
     SHOT_CLOCK is missing), proving the asymmetry the fix removes; and an
     ON-TIME centered SHOT_CLOCK fire still scores > 0 (the fix must not
     break legitimate fires).

Proven: fail-on-current expected; pass-on-fix.
"""
from __future__ import annotations

import sys
import time

import requests

from verify_lib import BASE, log, Verifier

SP = f"{BASE}/api/sp"
PAIR = f"{BASE}/api/pair"

HOST = 1
JOINER = 2
TIMEOUT = 8


def _post(url: str, body: dict) -> requests.Response:
    return requests.post(url, json=body, timeout=TIMEOUT)


def _pair_via_rest() -> str | None:
    """Pair host(1) + joiner(2) and start a match using only REST.
    Returns session_code or None."""
    _post(f"{PAIR}/clear", {})
    r = _post(f"{PAIR}/request", {"puck_id": HOST})
    if r.status_code != 200:
        log(f"pair/request host failed: {r.status_code} {r.text[:160]}")
        return None
    code = r.json().get("pair_code")
    if not code:
        log("pair/request host returned no pair_code")
        return None
    # Joiner is auto-added to the lobby on /request.
    _post(f"{PAIR}/request", {"puck_id": JOINER})
    # Host confirms its dialed code.
    _post(f"{PAIR}/confirm", {"puck_id": HOST, "code": code})
    r = _post(f"{PAIR}/start", {"puck_id": HOST})
    if r.status_code != 200:
        log(f"pair/start failed: {r.status_code} {r.text[:160]}")
        return None
    return r.json().get("session_code")


def _answer_round(sc: str, qid: int) -> None:
    """Both expected pucks answer (letter 'A'); the second answer triggers
    the aggregate reveal, which lets the next load-question advance."""
    for pid in (HOST, JOINER):
        _post(f"{SP}/answer", {
            "session_code": sc,
            "puck_id": pid,
            "question_id": qid,
            "answer": "A",
            "response_time_ms": 1200,
        })


def _drive_to_shotclock(v: Verifier, sc: str) -> dict | None:
    """Step the match forward via load-question until it returns a
    SHOT_CLOCK minigame phase (fires before round 4). Resolves any
    BULLSEYE minigame and category-pick phases encountered first.
    Returns the SHOT_CLOCK phase payload, or None if not reached."""
    for _ in range(40):
        r = _post(f"{SP}/load-question/{sc}", {})
        if r.status_code != 200:
            log(f"load-question failed: {r.status_code} {r.text[:160]}")
            return None
        data = r.json()
        phase = data.get("phase")

        if phase == "minigame":
            if data.get("flavor") == "SHOT_CLOCK":
                return data
            # BULLSEYE before round 2/6 — resolve it so we can move on.
            _post(f"{SP}/minigame/finish/{sc}", {})
            continue

        if phase == "category_pick":
            offer = data.get("offer") or []
            if not offer:
                log("category_pick phase had empty offer")
                return None
            _post(f"{SP}/select-category/{sc}", {
                "puck_id": data.get("picker_puck_id"),
                "category_id": offer[0]["id"],
            })
            continue

        # Otherwise it's a question payload — answer it to reach reveal,
        # then loop to advance.
        q = data.get("question")
        if not q:
            log(f"unexpected load-question payload: {str(data)[:200]}")
            return None
        _answer_round(sc, int(q["id"]))
        time.sleep(0.1)

    return None


def run() -> int:
    v = Verifier()

    # ---- Unit control on the scoring function (asymmetry + no regression).
    # Import the live module so the gate exercises the actual code path.
    try:
        import pair_routes as pr
    except Exception as e:
        v.inconclusive("import pair_routes", f"{e!r}")
        return v.report()

    cycle = pr.SP_SHOTCLOCK_CYCLE_MS          # 3000
    dur_ms = pr.SP_SHOTCLOCK_DURATION_S * 1000.0  # 8000
    sc_mg = {
        "flavor": "SHOT_CLOCK",
        "duration_s": pr.SP_SHOTCLOCK_DURATION_S,
        "cycle_ms": cycle,
        "green_frac": pr.SP_SHOTCLOCK_GREEN_FRAC,
        "target_quadrant": None,
    }
    # On-time, dead-center fire MUST still score (fix must not over-reject).
    ontime_center = int(cycle // 2)  # 1500ms: pos=0.5, < duration => legal
    pts_ontime = pr._score_minigame_fire(sc_mg, ontime_center, None)
    v.check("ontime-centered-shotclock-still-scores", pts_ontime > 0,
            f"t_ms={ontime_center} points={pts_ontime} (expected >0)")

    # Late, dead-center fire: t_ms past duration but (t_ms % cycle)==cycle/2.
    # Pick the smallest full-cycle offset that exceeds duration so it lands
    # exactly on green-zone center yet is unambiguously after the deadline.
    n = int(dur_ms // cycle) + 1
    late_center = n * cycle + cycle // 2  # e.g. 3*3000 + 1500 = 10500ms
    assert late_center > dur_ms and (late_center % cycle) == cycle // 2
    pts_unit_late = pr._score_minigame_fire(sc_mg, late_center, None)

    # Control: BULLSEYE already rejects a late fire (the guard SHOT_CLOCK
    # lacks). Proves the asymmetry; this should pass on current AND fixed.
    bull_mg = {
        "flavor": "BULLSEYE",
        "duration_s": pr.SP_BULLSEYE_DURATION_S,
        "target_quadrant": "A",
    }
    pts_bull_late = pr._score_minigame_fire(bull_mg, late_center, "A")
    v.check("control-bullseye-late-fire-scores-zero", pts_bull_late == 0,
            f"t_ms={late_center} points={pts_bull_late} (expected 0)")

    # ---- Live end-to-end against the running server.
    sc = _pair_via_rest()
    if not sc:
        v.inconclusive("setup-pair-and-start", "no session_code via REST")
        return v.report()
    log(f"paired session_code={sc}")

    mg = _drive_to_shotclock(v, sc)
    if not mg:
        v.inconclusive("reach-shotclock-minigame",
                       "load-question never returned a SHOT_CLOCK phase")
        return v.report()
    log(f"reached SHOT_CLOCK minigame: duration_s={mg.get('duration_s')} "
        f"cycle_ms={mg.get('cycle_ms')}")

    # Confirm the live minigame state matches our scoring assumptions.
    st = requests.get(f"{SP}/minigame/state/{sc}", timeout=TIMEOUT).json()
    if not st.get("active") or st.get("flavor") != "SHOT_CLOCK":
        v.inconclusive("shotclock-minigame-active",
                       f"state={str(st)[:200]}")
        return v.report()
    live_cycle = int(st.get("cycle_ms") or cycle)
    live_dur_ms = float(st.get("duration_s") or pr.SP_SHOTCLOCK_DURATION_S) * 1000.0
    n2 = int(live_dur_ms // live_cycle) + 1
    fire_t_ms = n2 * live_cycle + live_cycle // 2  # late + dead-center
    log(f"firing late: t_ms={fire_t_ms} (> {live_dur_ms:.0f}ms deadline, "
        f"t_ms%cycle={fire_t_ms % live_cycle} == cycle/2={live_cycle // 2})")

    fr = _post(f"{SP}/minigame/fire", {
        "session_code": sc,
        "puck_id": HOST,
        "t_ms": fire_t_ms,
    })
    if fr.status_code != 200:
        v.inconclusive("minigame-fire-accepted",
                       f"{fr.status_code} {fr.text[:160]}")
        return v.report()
    live_points = int(fr.json().get("points", -1))

    # DECISIVE: a fire past the 8s deadline must score zero. Currently it
    # scores ~1000 because the SHOT_CLOCK branch skips the window guard.
    v.check("shotclock-late-fire-scores-zero",
            live_points == 0,
            f"live fire t_ms={fire_t_ms} points={live_points} (expected 0); "
            f"unit late-center points={pts_unit_late}")

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
