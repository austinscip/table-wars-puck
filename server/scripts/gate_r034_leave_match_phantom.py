"""Gate for R034 — leave-match is a phantom route (404).

Bug: A puck that holds-3s to leave POSTs /api/sp/leave-match, but no such
route is registered (HTTP 404). usePuckState.hold3s swallows the failure and
sets the local puck IDLE anyway, so the departed puck is NEVER removed from
state['expected_pucks']. Consequences:
  - _maybe_emit_reveal's `all(pid in answers for pid in expected)` gate
    (pair_routes.py:1491) can no longer go True from the remaining pucks
    answering — every round only completes via the TV's ~10s force-reveal.
  - QuestionScreen has no player_left_match handler, so the departed lane
    shows 'thinking' forever and the next category pick can be misrouted to
    the gone puck.

Fix sketch: register POST /api/sp/leave-match that discards the puck from
state['expected_pucks'] (and current_round_answers / power_up_* /
pending_minigame.fires; clears last_round_winner_puck_id if it was them),
emits player_left_match, then calls _maybe_emit_reveal/_resolve_minigame.
Stop swallowing the POST failure in usePuckState; add player_left_match
handlers in QuestionScreen/MinigameScreen.

Gate assertion name: leave-match-route-prunes-expected-pucks

Kind: mixed — the decisive, deterministic, CPU-cheap proof is REST-only
(no browser): we establish a 2-puck session over /api/pair, drive it to an
ANSWERING question, have puck B leave, then have puck A answer ALONE. If the
route pruned B from expected_pucks, A's lone answer must trigger the reveal
(observable via /api/sp/answer -> reveal_emitted == true, and
/api/sp/current-question -> active == false). On the current build the route
404s, B is never pruned, and A's lone answer does NOT reveal (reveal_emitted
== false, question still active until force-reveal). The client-side lane /
handler behavior is verified later under browser-truth; this gate proves the
load-bearing server contract.

Proven: fail-on-current expected; pass-on-fix.
"""
from __future__ import annotations

import sys
import time

import requests

from verify_lib import BASE, log, Verifier

# Puck ids for the two-handed REST match. Host = A (stays), joiner = B (leaves).
PUCK_A = 7001
PUCK_B = 7002

_TIMEOUT = 6


def _post(path: str, body: dict):
    return requests.post(f"{BASE}{path}", json=body, timeout=_TIMEOUT)


def _get(path: str):
    return requests.get(f"{BASE}{path}", timeout=_TIMEOUT)


def _establish_two_puck_session() -> str | None:
    """Pure-REST pairing: clear -> request(A=host) -> request(B=joiner) ->
    confirm(A) -> start(A). Returns the session_code, or None on failure.
    Both pucks end up registered, so expected_pucks == {A, B}."""
    _post("/api/pair/clear", {})
    r_host = _post("/api/pair/request", {"puck_id": PUCK_A})
    if r_host.status_code != 200:
        log(f"  pair/request(host) -> {r_host.status_code}")
        return None
    code = r_host.json().get("pair_code")
    if not code:
        return None
    # Joiner is added to the lobby on /request alone (no dial step).
    r_join = _post("/api/pair/request", {"puck_id": PUCK_B})
    if r_join.status_code != 200:
        log(f"  pair/request(joiner) -> {r_join.status_code}")
        return None
    # Host confirms its dial.
    _post("/api/pair/confirm", {"puck_id": PUCK_A, "code": code})
    r_start = _post("/api/pair/start", {"puck_id": PUCK_A})
    if r_start.status_code != 200:
        log(f"  pair/start -> {r_start.status_code} {r_start.text[:160]}")
        return None
    return r_start.json().get("session_code")


def _drive_to_answering_question(sc: str) -> int | None:
    """Round 1 is a category-pick round, so load-question first opens the
    pick phase. Resolve the pick, load again to get the real question, then
    start the timer. Returns the active question_id, or None on failure."""
    # First load-question opens the category pick for round 1.
    r = _post(f"/api/sp/load-question/{sc}", {})
    body = r.json() if r.status_code == 200 else {}
    if body.get("phase") == "category_pick":
        picker = body.get("picker_puck_id")
        offer = body.get("offer") or []
        if not offer:
            return None
        cat_id = int(offer[0]["id"])
        rc = _post(f"/api/sp/select-category/{sc}",
                   {"puck_id": picker, "category_id": cat_id})
        if rc.status_code != 200:
            log(f"  select-category -> {rc.status_code} {rc.text[:160]}")
            return None
        # Second load-question consumes next_category_id and yields the question.
        r = _post(f"/api/sp/load-question/{sc}", {})

    # Resolve the active question id from current-question.
    for _ in range(12):
        cq = _get(f"/api/sp/current-question/{sc}").json()
        if cq.get("active") and cq.get("question_id"):
            qid = int(cq["question_id"])
            _post(f"/api/sp/start-timer/{sc}", {})
            return qid
        time.sleep(0.3)
    return None


def run() -> int:
    v = Verifier()

    # --- Part 1: prove the route exists (currently 404). -----------------
    # We POST a benign leave for a non-participating puck against any
    # session; the only thing under test here is route registration, so a
    # 404 (no route) is the fail signal and any non-404 (200/400/409) is the
    # pass signal. This is the cheapest standalone proof of the phantom.
    r404 = _post("/api/sp/leave-match", {"session_code": "ZZZZ", "puck_id": 999})
    route_registered = r404.status_code != 404
    log(f"leave-match route probe -> HTTP {r404.status_code} "
        f"(404 == phantom/missing)")

    # --- Part 2: the decisive behavioral proof. --------------------------
    # Establish a 2-puck session, drive to an ANSWERING question, B leaves,
    # then A answers ALONE. The reveal must fire from A alone iff B was
    # pruned from expected_pucks by the leave-match route.
    sc = _establish_two_puck_session()
    if not sc:
        v.inconclusive("leave-match-route-prunes-expected-pucks",
                       "could not establish a 2-puck REST session")
        return v.report()
    log(f"session_code = {sc}")

    qid = _drive_to_answering_question(sc)
    if qid is None:
        v.inconclusive("leave-match-route-prunes-expected-pucks",
                       "could not drive the match to an ANSWERING question")
        return v.report()
    log(f"active question_id = {qid}")

    # Sanity: question is active (not yet revealed) before anyone answers.
    pre = _get(f"/api/sp/current-question/{sc}").json()
    if not pre.get("active"):
        v.inconclusive("leave-match-route-prunes-expected-pucks",
                       f"question not active pre-answer: {pre}")
        return v.report()

    # Puck B leaves. On the current build this 404s (no route); on the fixed
    # build it prunes B from expected_pucks. We tolerate either outcome here
    # because the DECISIVE check is whether A's lone answer reveals.
    r_leave = _post("/api/sp/leave-match",
                    {"session_code": sc, "puck_id": PUCK_B})
    log(f"B leave-match -> HTTP {r_leave.status_code}")

    # Puck A answers ALONE.
    r_ans = _post("/api/sp/answer", {
        "session_code": sc,
        "puck_id": PUCK_A,
        "question_id": qid,
        "answer": "A",
        "response_time_ms": 1200,
    })
    if r_ans.status_code != 200:
        v.inconclusive("leave-match-route-prunes-expected-pucks",
                       f"puck A answer rejected: {r_ans.status_code} "
                       f"{r_ans.text[:160]}")
        return v.report()
    ans_body = r_ans.json()
    reveal_emitted = bool(ans_body.get("reveal_emitted"))
    log(f"A answer -> reveal_emitted={reveal_emitted}")

    # Corroborate via current-question: once revealed, it reports active=false
    # WITHOUT any force-reveal call. We deliberately never call force-reveal,
    # so on the broken build the question stays active (B still expected,
    # only the TV's 10s deadline could end it).
    post = _get(f"/api/sp/current-question/{sc}").json()
    revealed_via_current_q = (post.get("active") is False)
    log(f"current-question after A's lone answer -> active={post.get('active')}")

    pruned = reveal_emitted and revealed_via_current_q

    # Decisive assertion. On current build: route 404s, B stays expected,
    # A alone does not reveal -> FAIL. On fix: route prunes B, A alone
    # reveals -> PASS.
    v.check(
        "leave-match-route-prunes-expected-pucks",
        route_registered and pruned,
        f"route_registered={route_registered} leave_status={r_leave.status_code} "
        f"reveal_emitted={reveal_emitted} "
        f"revealed_via_current_q={revealed_via_current_q}",
    )

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
