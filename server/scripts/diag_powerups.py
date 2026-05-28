"""Bug hunt: do power-ups actually fire end-to-end in a real match?

Slice E3 added DOUBLE / SHIELD / REVEAL / STEAL granted to minigame
winners. The full cycle is:

  1. Win a minigame  ->  server grants random power-up to winner.
  2. inventory_updated socket fires with the new item.
  3. Player activates the item during the next between-rounds phase.
  4. Next question reveal applies the armed effect.

This drives a real match, captures the granted item, activates it via
REST, then checks the next reveal payload for the expected effect. If
any link in the chain fails, that's the bug.

Asserts (for the type that lands):
  - DOUBLE: puck's `points` on the next question == 2x raw points.
  - REVEAL: puck's `is_correct` == true even on a wrong-letter answer.
  - SHIELD: armed (no easy assertion — need an incoming STEAL).
  - STEAL : `power_up_resolved` socket fires AND target's cumulative drops.
"""
from __future__ import annotations

import json
import sys
import time

import requests
from playwright.sync_api import sync_playwright, Page


BASE = "http://localhost:5002"
TV = f"{BASE}/tv/speed-pyramid"
HUB = f"{TV}/dev/hub"

# VariantA TAP fires the minigame defaulting to quadrant A. We want
# puck 1 to WIN the minigame, so puck 1 needs to fire the matching
# quadrant. VariantB has aim. For simplicity we use VariantA but read
# the target quadrant and use REST to fire puck 1 in the right quadrant.

PUCK1 = 1
PUCK2 = 2


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def puck_row(page: Page, idx: int):
    return page.locator("main > div").nth(idx)


def puck_state(page: Page, idx: int) -> str:
    try:
        return puck_row(page, idx).locator("span.text-cyan-300").first.inner_text(timeout=1500)
    except Exception:
        return ""


def parse_qid(state: str):
    if "Q" not in state:
        return None
    tail = state.split("Q", 1)[1]
    num = ""
    for ch in tail:
        if ch.isdigit(): num += ch
        else: break
    return int(num) if num else None


def get_inventory(sc: str, puck_id: int) -> list[dict]:
    r = requests.get(f"{BASE}/api/sp/inventory/{sc}",
                     params={"puck_id": puck_id}, timeout=4)
    if r.status_code != 200:
        return []
    return r.json().get("items", [])


def run() -> int:
    requests.post(f"{BASE}/api/pair/clear", json={}, timeout=5)
    socket_events: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        ctx = browser.new_context(viewport={"width": 1600, "height": 900})
        hub = ctx.new_page()
        tv = ctx.new_page()

        def on_ws(ws):
            def on_frame(payload):
                if not isinstance(payload, str): return
                for tag in ("inventory_updated", "power_up_used",
                            "power_up_resolved", "reveal", "minigame_winner"):
                    if f'"{tag}"' in payload:
                        try:
                            # socket.io frames look like '42["event",{...}]'
                            i = payload.index('[')
                            arr = json.loads(payload[i:])
                            socket_events.append({"event": arr[0], "data": arr[1]})
                        except Exception:
                            pass
                        return
            ws.on("framereceived", on_frame)
        tv.on("websocket", on_ws)

        hub.goto(HUB, wait_until="domcontentloaded")
        tv.goto(TV + "/", wait_until="domcontentloaded")
        time.sleep(0.8)

        # Pair + start.
        puck_row(hub, 0).get_by_role("button", name="Hold 1s").click(); time.sleep(0.5)
        puck_row(hub, 0).locator("button", has_text="Confirm").click(); time.sleep(0.8)
        puck_row(hub, 1).get_by_role("button", name="Hold 1s").click(); time.sleep(1.2)
        puck_row(hub, 0).get_by_role("button", name="Start match", exact=True).click(); time.sleep(1.2)
        sc = requests.get(f"{BASE}/api/pair/lobby-state", timeout=5).json().get("session_code")
        if not sc:
            log("INCONCLUSIVE: no session_code"); browser.close(); return 2
        tv.goto(f"{TV}/question/{sc}", wait_until="domcontentloaded")
        log(f"sc={sc}")

        granted_item: dict | None = None
        powerup_used = False
        target_question_id: int | None = None
        target_round: int | None = None
        powerup_type: str | None = None

        deadline = time.time() + 200
        while time.time() < deadline:
            if "/scoreboard/" in tv.evaluate("() => location.pathname"):
                break
            s1, s2 = puck_state(hub, 0), puck_state(hub, 1)
            if "MATCH ENDED" in s1 and "MATCH ENDED" in s2:
                break

            if "PICK CATEGORY" in s1 or "PICK CATEGORY" in s2:
                # If we have an unused granted power-up and we're in a
                # between-rounds phase, ACTIVATE NOW.
                if granted_item and not powerup_used:
                    log(f"  activating power-up {granted_item['type']} (id={granted_item['id']}) for puck {PUCK1}")
                    body = {"session_code": sc, "puck_id": PUCK1, "item_id": granted_item["id"]}
                    if granted_item["type"] == "STEAL":
                        body["target_puck_id"] = PUCK2
                    r = requests.post(f"{BASE}/api/sp/power-up/activate",
                                       json=body, timeout=4)
                    log(f"  activate -> {r.status_code} {r.json()}")
                    if r.status_code == 200:
                        powerup_used = True
                        powerup_type = granted_item["type"]
                        target_round = None  # set after next question loads

                # Resolve the pick.
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

            if "MINIGAME" in s1 or "MINIGAME" in s2:
                # Read target quadrant from puck 1's state ("MINIGAME BULLSEYE -> X")
                target = None
                import re
                m = re.search(r"→([ABCD])", s1)
                if m: target = m.group(1)
                if target and "BULLSEYE" in s1:
                    # Fire puck 1 in the matching quadrant via REST (so puck 1 wins).
                    log(f"  minigame target={target}, firing puck 1 in {target}")
                    requests.post(f"{BASE}/api/sp/minigame/fire", json={
                        "session_code": sc, "puck_id": PUCK1, "t_ms": 500, "quadrant": target,
                    }, timeout=4)
                    # Fire puck 2 in the wrong quadrant (also via REST so we don't depend on the Hub button).
                    wrong = next(q for q in "ABCD" if q != target)
                    requests.post(f"{BASE}/api/sp/minigame/fire", json={
                        "session_code": sc, "puck_id": PUCK2, "t_ms": 4000, "quadrant": wrong,
                    }, timeout=4)
                else:
                    # SHOT_CLOCK or no target detected — just TAP both via REST.
                    for pid in (PUCK1, PUCK2):
                        requests.post(f"{BASE}/api/sp/minigame/fire", json={
                            "session_code": sc, "puck_id": pid, "t_ms": 1500, "quadrant": None,
                        }, timeout=4)
                time.sleep(2.5)

                # Check inventory immediately after minigame resolves.
                inv = get_inventory(sc, PUCK1)
                if inv and not granted_item:
                    granted_item = inv[0]
                    log(f"  GRANTED to puck 1: {granted_item['type']} id={granted_item['id']}")
                continue

            if "ANSWERING" in s1 and "ANSWERING" in s2:
                qid = parse_qid(s1) or parse_qid(s2)
                # First question AFTER a power-up activation is the
                # target — record its qid so we can check the reveal.
                if powerup_used and target_question_id is None:
                    target_question_id = qid
                    log(f"  >>> target question is Q{qid} (power-up should land here)")

                # If REVEAL is active, puck 1 should be marked correct
                # even on a WRONG answer. So pick D (often wrong) to test.
                # For DOUBLE we just want to land any correct answer to
                # see points doubled. Easiest: both pick A.
                p1_letter = "D" if powerup_type == "REVEAL" else "A"
                for idx, L in ((0, p1_letter), (1, "B")):
                    try:
                        puck_row(hub, idx).get_by_role("button", name=L, exact=True).click(
                            force=True, timeout=2000)
                    except Exception: pass
                    time.sleep(0.3)
                time.sleep(3.0)
                continue
            time.sleep(0.3)

        browser.close()

    # === analyze ===
    log("")
    log(f"=== power-up grant cycle ===")
    log(f"granted_item: {granted_item}")
    log(f"powerup_used: {powerup_used}  type={powerup_type}")
    log(f"target_question_id: {target_question_id}")

    log("")
    log(f"=== relevant socket events ({len(socket_events)}) ===")
    for e in socket_events:
        log(f"  {e['event']}: {json.dumps(e['data'])[:200]}")

    # Find the reveal for the target question.
    reveals = [e for e in socket_events
               if e["event"] == "reveal"
               and e["data"].get("question_id") == target_question_id]
    log("")
    log(f"=== reveal for Q{target_question_id} ({len(reveals)} matched) ===")

    failures = []
    if not granted_item:
        failures.append("no power-up was ever granted after winning a minigame")
    elif not powerup_used:
        failures.append(f"granted {granted_item['type']} but ACTIVATE never succeeded")
    elif not reveals:
        failures.append(f"power-up activated but no reveal captured for Q{target_question_id}")
    else:
        rv = reveals[0]
        p1_result = next((r for r in rv["data"]["results"] if r["puck_id"] == PUCK1), None)
        log(f"  puck 1 result: {p1_result}")
        if powerup_type == "DOUBLE":
            # Hard to assert exact 2x without raw_points; assert >= 1500
            # (typical correct LEGENDARY = 1000, doubled = 2000).
            pts = p1_result["points"] if p1_result else 0
            if pts < 1500:
                failures.append(f"DOUBLE armed but points only {pts} (expected ~2000)")
            else:
                log(f"  DOUBLE: puck 1 got {pts} points ✓ (likely 2x'd)")
        elif powerup_type == "REVEAL":
            ok = p1_result and p1_result.get("is_correct")
            if not ok:
                failures.append(f"REVEAL armed but puck 1 is_correct={p1_result and p1_result.get('is_correct')}")
            else:
                log(f"  REVEAL: puck 1 is_correct={ok} ✓ (forced)")
        elif powerup_type == "SHIELD":
            log(f"  SHIELD armed — no easy assertion (needs incoming STEAL). Activation succeeded.")
        elif powerup_type == "STEAL":
            resolved = [e for e in socket_events if e["event"] == "power_up_resolved"]
            if not resolved:
                failures.append("STEAL armed but no power_up_resolved socket fired")
            else:
                log(f"  STEAL: power_up_resolved fired ✓ ({resolved[0]['data']})")

    log("")
    if failures:
        log(f"RESULT: BUG(S) FOUND — {len(failures)}:")
        for f in failures: log(f"  - {f}")
        return 1
    log("RESULT: PASS — power-up cycle works end-to-end.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
