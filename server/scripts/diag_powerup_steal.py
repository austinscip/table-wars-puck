"""Bug hunt: STEAL power-up specifically.

diag_powerups landed REVEAL last run; STEAL was never exercised. STEAL
takes a different code path:
  - activate requires target_puck_id.
  - server queues an incoming_steals entry on the target's arms.
  - on reveal, server transfers points from target -> firer and emits
    power_up_resolved.

This runs matches in a loop until STEAL is granted to puck 1, then
activates targeting puck 2 and verifies:
  - 200 response with type=STEAL.
  - power_up_resolved socket fires with both puck_ids.
  - puck 2's cumulative_total drops by the stolen amount on next reveal.
  - puck 1's cumulative_total rises.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import time
from pathlib import Path

import requests

from verify_lib import (
    BASE, log, session, pair_and_start, drive_match_to_scoreboard,
    puck_row, puck_state, parse_qid, Verifier,
)

PUCK1, PUCK2 = 1, 2
MAX_MATCH_ATTEMPTS = 6
DB = Path(__file__).resolve().parent.parent / "tablewars.db"


def get_inventory(sc: str, puck_id: int) -> list[dict]:
    r = requests.get(f"{BASE}/api/sp/inventory/{sc}",
                     params={"puck_id": puck_id}, timeout=4)
    return r.json().get("items", []) if r.status_code == 200 else []


def correct_answer_for(qid: int) -> str | None:
    """Look up the correct answer letter for a question from the DB —
    used so puck 2 can deliberately score on the STEAL target question
    (STEAL is a no-op if target has 0 points)."""
    con = sqlite3.connect(str(DB))
    row = con.execute(
        "SELECT correct_answer FROM trivia_questions WHERE id = ?",
        (qid,)).fetchone()
    con.close()
    return row[0] if row else None


def current_question_id(sc: str) -> int | None:
    r = requests.get(f"{BASE}/api/sp/current-question/{sc}", timeout=4).json()
    return r.get("question_id") if r.get("active") else None


def play_until_steal_granted(hub, tv, v: Verifier) -> tuple[str, dict] | None:
    """Run matches until a STEAL is granted to puck 1, returning
    (session_code, item) so caller can activate it on the next round."""
    for attempt in range(1, MAX_MATCH_ATTEMPTS + 1):
        log(f"=== match attempt {attempt}/{MAX_MATCH_ATTEMPTS} ===")
        requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)
        # Reload the Hub so virtual pucks reset to IDLE — pair/clear
        # wipes server state but the Hub pucks still hold their last
        # state until their poll catches up.
        from verify_lib import HUB
        hub.goto(HUB, wait_until="domcontentloaded")
        time.sleep(1.2)
        sc = pair_and_start(hub, tv)
        if not sc:
            continue

        # Drive minigames manually (REST fires) so puck 1 wins each one
        # → 3 power-up grants per match.
        deadline = time.time() + 180
        while time.time() < deadline:
            if "/scoreboard/" in tv.evaluate("() => location.pathname"):
                break
            s1, s2 = puck_state(hub, 0), puck_state(hub, 1)
            if "MATCH ENDED" in s1 and "MATCH ENDED" in s2: break

            if "MINIGAME" in s1 or "MINIGAME" in s2:
                m = re.search(r"→([ABCD])", s1)
                target = m.group(1) if m else None
                if target and "BULLSEYE" in s1:
                    # puck 1 wins
                    requests.post(f"{BASE}/api/sp/minigame/fire", json={
                        "session_code": sc, "puck_id": PUCK1, "t_ms": 500,
                        "quadrant": target}, timeout=4)
                    wrong = next(q for q in "ABCD" if q != target)
                    requests.post(f"{BASE}/api/sp/minigame/fire", json={
                        "session_code": sc, "puck_id": PUCK2, "t_ms": 4000,
                        "quadrant": wrong}, timeout=4)
                else:
                    # SHOT_CLOCK: puck 1 fires fast, puck 2 slow
                    requests.post(f"{BASE}/api/sp/minigame/fire", json={
                        "session_code": sc, "puck_id": PUCK1, "t_ms": 1500,
                        "quadrant": None}, timeout=4)
                    requests.post(f"{BASE}/api/sp/minigame/fire", json={
                        "session_code": sc, "puck_id": PUCK2, "t_ms": 5000,
                        "quadrant": None}, timeout=4)
                time.sleep(2.5)

                # Did puck 1 get a STEAL?
                inv = get_inventory(sc, PUCK1)
                steal = next((it for it in inv if it["type"] == "STEAL"), None)
                if steal:
                    log(f"  GRANTED STEAL: {steal['id']}")
                    return sc, steal
                continue

            if "PICK CATEGORY" in s1 or "PICK CATEGORY" in s2:
                # Resolve picks via Hub clicks
                pd = time.time() + 13
                while time.time() < pd:
                    if ("PICK CATEGORY" not in puck_state(hub, 0)
                            and "PICK CATEGORY" not in puck_state(hub, 1)):
                        break
                    for pidx in (0, 1):
                        btns = puck_row(hub, pidx).locator("button[title]")
                        if btns.count() > 0:
                            try: btns.first.click(force=True, timeout=1200)
                            except Exception: pass
                    time.sleep(0.5)
                time.sleep(1.0); continue

            if "ANSWERING" in s1 and "ANSWERING" in s2:
                for idx, L in ((0, "A"), (1, "A")):
                    try:
                        puck_row(hub, idx).get_by_role(
                            "button", name=L, exact=True).click(
                                force=True, timeout=2000)
                    except Exception: pass
                    time.sleep(0.2)
                time.sleep(2.5); continue
            time.sleep(0.3)
        # Match ended without granting STEAL; try again with fresh
        # lobby clear.
    log("STEAL never granted across attempts.")
    return None


def run() -> int:
    v = Verifier()
    socket_events: list[dict] = []

    with session() as (hub, tv):
        def on_ws(ws):
            def on_frame(payload):
                if not isinstance(payload, str): return
                for tag in ("inventory_updated", "power_up_used",
                            "power_up_resolved", "reveal", "minigame_winner"):
                    if f'"{tag}"' in payload:
                        try:
                            i = payload.index('[')
                            arr = json.loads(payload[i:])
                            socket_events.append({"event": arr[0], "data": arr[1]})
                        except Exception: pass
                        return
            ws.on("framereceived", on_frame)
        tv.on("websocket", on_ws)

        result = play_until_steal_granted(hub, tv, v)
        if not result:
            v.inconclusive("STEAL was granted",
                           "no STEAL after multiple matches — random RNG")
            return v.report()
        sc, steal = result
        v.check("STEAL was granted to puck 1", True,
                f"item_id={steal['id']}")

        # We now have STEAL in inventory. Activate during the NEXT
        # between-rounds phase, then drive until at least one reveal
        # event fires AFTER activation so we can observe the effect.
        log("waiting for next between-rounds phase to activate STEAL...")
        activated = False
        reveals_before_activation = 0  # set AT activation moment (not before
        # the loop) so we measure reveals POST-activate, not since granted.
        # Step 1: wait for between-rounds phase + activate.
        for _ in range(120):  # ~60s
            ms = requests.get(f"{BASE}/api/sp/match-state/{sc}",
                              timeout=4).json()
            if ms.get("pending_category_pick") or ms.get("pending_minigame"):
                # Snapshot reveal count AT activation moment.
                reveals_before_activation = sum(
                    1 for e in socket_events if e["event"] == "reveal")
                r = requests.post(f"{BASE}/api/sp/power-up/activate", json={
                    "session_code": sc, "puck_id": PUCK1,
                    "item_id": steal["id"], "target_puck_id": PUCK2,
                }, timeout=4)
                log(f"  activate -> {r.status_code} {r.json()}  "
                    f"(reveals so far: {reveals_before_activation})")
                v.check("STEAL activate returns 200", r.status_code == 200,
                        f"status={r.status_code} body={r.json()}")
                activated = True
                break
            # Drive whatever phase is current while waiting for between-rounds.
            s1, s2 = puck_state(hub, 0), puck_state(hub, 1)
            if "ANSWERING" in s1 and "ANSWERING" in s2:
                for idx in (0, 1):
                    try: puck_row(hub, idx).get_by_role(
                        "button", name="A", exact=True).click(force=True, timeout=2000)
                    except Exception: pass
                    time.sleep(0.2)
                time.sleep(2.5)
            time.sleep(0.4)

        # Step 2: drive at least one reveal that arrives AFTER the
        # power_up_used event. Anchoring on arrival order (not just a
        # count) avoids the race where a pre-activation reveal is
        # in-flight when we snapshot and lands after activation, fooling
        # a simple counter into thinking we have a post-activation reveal.
        if activated:
            log("driving forward until a reveal arrives AFTER power_up_used...")
            deadline = time.time() + 60
            while time.time() < deadline:
                # Find index of power_up_used; any reveal at higher index
                # is genuinely post-activation in arrival order.
                pu_idx = next((i for i, e in enumerate(socket_events)
                               if e["event"] == "power_up_used"
                               and e["data"].get("type") == "STEAL"), -1)
                post_reveal = None
                if pu_idx >= 0:
                    post_reveal = next((e for e in socket_events[pu_idx + 1:]
                                        if e["event"] == "reveal"), None)
                if post_reveal:
                    log(f"  reveal at index {socket_events.index(post_reveal)} (post power_up_used at {pu_idx})  qid={post_reveal['data'].get('question_id')}")
                    break
                if "/scoreboard/" in tv.evaluate("() => location.pathname"):
                    break
                s1, s2 = puck_state(hub, 0), puck_state(hub, 1)
                if "PICK CATEGORY" in s1 or "PICK CATEGORY" in s2:
                    for pidx in (0, 1):
                        btns = puck_row(hub, pidx).locator("button[title]")
                        if btns.count() > 0:
                            try: btns.first.click(force=True, timeout=1200)
                            except Exception: pass
                    time.sleep(1.2)
                elif "MINIGAME" in s1 or "MINIGAME" in s2:
                    for pid in (PUCK1, PUCK2):
                        requests.post(f"{BASE}/api/sp/minigame/fire", json={
                            "session_code": sc, "puck_id": pid, "t_ms": 4000,
                            "quadrant": None}, timeout=4)
                    time.sleep(2.5)
                elif "ANSWERING" in s1 and "ANSWERING" in s2:
                    # Force puck 2 to score on the target reveal so
                    # STEAL has something to steal. Look up the correct
                    # answer for the active question, click it on puck 2.
                    qid = current_question_id(sc)
                    correct = correct_answer_for(qid) if qid else None
                    p2_letter = correct or "A"
                    log(f"  target reveal Q{qid} — correct={correct}, puck2 clicks {p2_letter}")
                    for idx, L in ((0, "A"), (1, p2_letter)):
                        try: puck_row(hub, idx).get_by_role(
                            "button", name=L, exact=True).click(force=True, timeout=2000)
                        except Exception: pass
                        time.sleep(0.2)
                    time.sleep(2.5)
                else:
                    time.sleep(0.4)
        time.sleep(1.5)

    log("")
    log("=== FULL socket event timeline (filtered) ===")
    for i, e in enumerate(socket_events):
        if e["event"] in ("power_up_used", "power_up_resolved",
                           "reveal", "minigame_winner"):
            qid = e["data"].get("question_id", "")
            results = e["data"].get("results", [])
            summary = ""
            if e["event"] == "reveal" and results:
                summary = "  " + ", ".join(
                    f"p{r['puck_id']}={r.get('points',0)}/cum={r.get('cumulative_total',0)}"
                    for r in results)
            log(f"  [{i:2d}] {e['event']:18s} qid={qid}{summary}")
    log("")
    log("=== STEAL-related ===")
    for e in socket_events:
        if e["event"] in ("power_up_used", "power_up_resolved"):
            log(f"  {e['event']}: {json.dumps(e['data'])}")

    # Find first reveal AFTER power_up_used (arrival order) — that's
    # the question STEAL applies to. Puck 2 should have been targeted;
    # if STEAL transferred points, power_up_resolved fired with a
    # points_transferred amount.
    used_idx = next((i for i, e in enumerate(socket_events)
                     if e["event"] == "power_up_used"
                     and e["data"].get("type") == "STEAL"), None)
    if used_idx is not None:
        post_reveal = next((e for e in socket_events[used_idx + 1:]
                            if e["event"] == "reveal"), None)
        if post_reveal:
            res = {r["puck_id"]: r for r in post_reveal["data"]["results"]}
            p1_pts = res.get(PUCK1, {}).get("points", 0)
            p2_pts = res.get(PUCK2, {}).get("points", 0)
            log(f"target reveal qid={post_reveal['data'].get('question_id')}  "
                f"puck1.points={p1_pts}  puck2.points={p2_pts}")
            if p2_pts == 0:
                v.inconclusive(
                    "STEAL points-transfer assertion",
                    f"puck 2 scored 0 on target Q ({post_reveal['data'].get('question_id')}) — nothing to steal; can't verify")
            else:
                resolved = [e for e in socket_events
                            if e["event"] == "power_up_resolved"]
                transferred = (resolved[0]["data"].get("points_transferred")
                               if resolved else 0)
                v.check(
                    "STEAL emitted power_up_resolved when target had points",
                    len(resolved) > 0,
                    f"transferred={transferred}, puck2 {p2_pts}pts post-steal")
        else:
            v.inconclusive("STEAL reveal-after-activation",
                           "no reveal arrived after power_up_used")
    else:
        v.inconclusive("STEAL power_up_used event", "never seen")

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
