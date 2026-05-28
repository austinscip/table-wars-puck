"""Gate for R031 — REVEAL power-up armed on a TIMED-OUT puck must NOT
score that puck as correct/1000/LEGENDARY at reveal.

The bug (open R014): _maybe_emit_reveal fills TIMEOUT entries
(is_correct=False, points=0, tier='TIMEOUT') into current_round_answers
BEFORE _apply_power_up_arms runs (pair_routes.py:1506-1518). Then
_apply_power_up_arms (640-648) iterates ALL answers — including the
synthetic TIMEOUT fill — and REVEAL unconditionally sets
is_correct=True / points=1000 / tier='LEGENDARY'. So a puck that never
answered the question but happens to hold an armed REVEAL is rewarded a
correct LEGENDARY answer in the reveal payload AND in cumulative_scores.

This gate reproduces it purely over the REST API (kind: server-rest):
  1. Pair two pucks via /api/pair (request/confirm/start) — no browser.
  2. Drive round 1 (answer + reveal), then round 2 which opens the
     BULLSEYE minigame. Let puck2 win it so puck2 is granted a random
     power-up. Grants are random (DOUBLE/SHIELD/REVEAL/STEAL), so the
     whole match is retried (fresh /api/pair/clear) until puck2 holds a
     REVEAL item.
  3. Advance to round 3 (a category-pick phase = a valid between-rounds
     window) and ACTIVATE puck2's REVEAL via /api/sp/power-up/activate.
  4. Load round-3 question. puck1 answers; puck2 NEVER answers.
  5. TV POSTs /api/sp/force-reveal/<code>, which fills puck2 as TIMEOUT
     then applies the REVEAL arm.
  6. Capture the 'reveal' socket payload (via a python-socketio client
     joined to the session room) and inspect puck2's result.

Decisive assertion (EXACT name):
  timed-out-puck-with-reveal-not-marked-correct
    -> puck2.is_correct == False AND puck2.points == 0
       (current build: is_correct True, points 1000, tier LEGENDARY).
A corroborating check confirms cumulative_scores did not gain ~1000 for
the silent puck.

Fix sketch: in _apply_power_up_arms, skip entries whose tier=='TIMEOUT'
(or answer is None) before applying REVEAL/DOUBLE/STEAL.

Proven: fail-on-current expected; pass-on-fix.
"""
from __future__ import annotations

import sys
import threading
import time

import requests
import socketio as _sio

from verify_lib import BASE, log, Verifier


HOST_PUCK = 101
JOIN_PUCK = 202
MAX_MATCH_ATTEMPTS = 24   # ~58% chance of a REVEAL grant per match.


# ---------------------------------------------------------------------------
# REST helpers (thin wrappers; keep boilerplate out of run()).
# ---------------------------------------------------------------------------

def _post(path: str, body: dict, timeout: float = 8) -> requests.Response:
    return requests.post(f"{BASE}{path}", json=body, timeout=timeout)


def _get(path: str, timeout: float = 8) -> dict:
    return requests.get(f"{BASE}{path}", timeout=timeout).json()


def _clear() -> None:
    requests.post(f"{BASE}/api/pair/clear", json={}, timeout=8)


def _pair_two() -> str | None:
    """Pair HOST (host) + JOIN (joiner) and start the match purely via the
    REST pair flow. Returns the session_code or None."""
    r = _post("/api/pair/request", {"puck_id": HOST_PUCK})
    if r.status_code != 200:
        return None
    code = r.json().get("pair_code")
    # Joiner is added on /request; host must confirm its dial.
    _post("/api/pair/request", {"puck_id": JOIN_PUCK})
    _post("/api/pair/confirm", {"puck_id": HOST_PUCK, "code": code})
    s = _post("/api/pair/start", {"puck_id": HOST_PUCK})
    if s.status_code != 200:
        return None
    return s.json().get("session_code")


def _load_question(sc: str) -> dict:
    """POST load-question and return (status_code-tagged) JSON."""
    r = _post(f"/api/sp/load-question/{sc}", {})
    try:
        data = r.json()
    except Exception:
        data = {}
    data["_status"] = r.status_code
    return data


def _answer(sc: str, puck_id: int, qid: int, letter: str) -> dict:
    r = _post("/api/sp/answer", {
        "session_code": sc, "puck_id": puck_id,
        "question_id": qid, "answer": letter, "response_time_ms": 1500,
    })
    try:
        return r.json()
    except Exception:
        return {}


def _correct_letter(sc: str, qid: int) -> str:
    """Best-effort correct-answer probe so puck1 answers correctly (keeps
    the round's non-timeout side well-defined). Falls back to 'A'."""
    cq = _get(f"/api/sp/current-question/{sc}")
    ca = (cq or {}).get("correct_answer")
    if ca in ("A", "B", "C", "D"):
        return ca
    return "A"


def _resolve_pick_phase(sc: str, lq: dict) -> dict:
    """Given a load-question payload that returned a category_pick phase,
    pick the first offered category (so load-question can advance to the
    real question) and return the subsequent load-question payload. The
    build opens pick rounds (1/3/5/7) with this phase BEFORE the question.
    """
    offer = lq.get("offer") or []
    picker = lq.get("picker_puck_id")
    if offer and picker is not None:
        _post(f"/api/sp/select-category/{sc}",
              {"puck_id": picker, "category_id": offer[0]["id"]})
    return _load_question(sc)


def _resolve_question_round(sc: str, lq: dict) -> int | None:
    """Given a load-question payload that returned a real question, have
    BOTH pucks answer it (reveal fires automatically). Returns the qid."""
    q = lq.get("question") or {}
    qid = q.get("id")
    if qid is None:
        return None
    letter = _correct_letter(sc, qid)
    _answer(sc, HOST_PUCK, qid, letter)
    _answer(sc, JOIN_PUCK, qid, letter)
    return qid


def _win_minigame_with_join(sc: str, mg: dict) -> None:
    """JOIN puck fires optimally; HOST puck fires for 0 points, so JOIN
    wins and is granted a random power-up."""
    flavor = mg.get("flavor")
    if flavor == "BULLSEYE":
        target = mg.get("target_quadrant") or "A"
        wrong = "B" if target != "B" else "A"
        # JOIN: correct quadrant at t=0 (max points). HOST: wrong quadrant.
        _post("/api/sp/minigame/fire",
              {"session_code": sc, "puck_id": JOIN_PUCK, "t_ms": 0, "quadrant": target})
        _post("/api/sp/minigame/fire",
              {"session_code": sc, "puck_id": HOST_PUCK, "t_ms": 100, "quadrant": wrong})
    else:  # SHOT_CLOCK: JOIN hits green-zone center; HOST hits a dead spot.
        cycle = mg.get("cycle_ms") or 3000
        _post("/api/sp/minigame/fire",
              {"session_code": sc, "puck_id": JOIN_PUCK, "t_ms": cycle // 2, "quadrant": None})
        _post("/api/sp/minigame/fire",
              {"session_code": sc, "puck_id": HOST_PUCK, "t_ms": 0, "quadrant": None})
    # Belt-and-suspenders resolve in case the auto-resolve didn't fire.
    _post(f"/api/sp/minigame/finish/{sc}", {})


def _join_reveal_item(sc: str) -> dict | None:
    """Return JOIN puck's first REVEAL inventory item dict, or None."""
    ms = _get(f"/api/sp/match-state/{sc}")
    inv = (ms.get("power_up_inventories") or {}).get(str(JOIN_PUCK)) or []
    for it in inv:
        if it.get("type") == "REVEAL":
            return it
    return None


# ---------------------------------------------------------------------------
# Reveal-payload capture via a socket.io client joined to the session room.
# ---------------------------------------------------------------------------

class RevealCatcher:
    def __init__(self):
        self.client = _sio.Client(reconnection=False, logger=False,
                                   engineio_logger=False)
        self.payloads: list[dict] = []
        self.join_cum_before = 0  # JOIN cumulative snapshot pre round-3 reveal
        self._lock = threading.Lock()

        @self.client.on("reveal")
        def _on_reveal(data):  # noqa: ANN001
            with self._lock:
                self.payloads.append(data)

    def connect(self, session_code: str) -> bool:
        try:
            self.client.connect(BASE, wait_timeout=8)
        except Exception as e:  # noqa: BLE001
            log(f"socketio connect failed: {e}")
            return False
        self.client.emit("join_session_room", {"session_code": session_code})
        time.sleep(0.6)
        return True

    def latest_for_qid(self, qid: int) -> dict | None:
        with self._lock:
            for p in reversed(self.payloads):
                if p.get("question_id") == qid:
                    return p
        return None

    def close(self) -> None:
        try:
            self.client.disconnect()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# One full reproduction attempt. Returns one of:
#   ("repro", sc, qid, catcher)  — armed REVEAL on a timed-out puck, ready to assert
#   ("retry", reason, None, None) — this match didn't grant REVEAL; try again
#   ("setup", reason, None, None) — hard setup failure; abort
# ---------------------------------------------------------------------------

def _attempt() -> tuple[str, object, object, object]:
    _clear()
    sc = _pair_two()
    if not sc:
        return ("setup", "pairing failed", None, None)

    catcher = RevealCatcher()
    if not catcher.connect(sc):
        return ("setup", "could not join session room for reveal capture", None, None)

    # --- Round 1: a pick round (1/3/5/7). The build opens it with a
    # category_pick phase; resolve the pick to reach the real question. ---
    lq1 = _load_question(sc)
    if lq1.get("phase") == "category_pick":
        lq1 = _resolve_pick_phase(sc, lq1)
    if lq1.get("phase") or not lq1.get("question"):
        catcher.close()
        return ("setup", f"round1 not a question: {lq1.get('phase') or lq1}", None, None)
    if _resolve_question_round(sc, lq1) is None:
        catcher.close()
        return ("setup", "round1 answer/reveal failed", None, None)

    # --- Round 2: minigame phase. Let JOIN win to receive a power-up. ---
    lq2 = _load_question(sc)
    if lq2.get("phase") != "minigame":
        catcher.close()
        return ("setup", f"round2 not minigame: {lq2.get('phase')}", None, None)
    _win_minigame_with_join(sc, lq2)
    time.sleep(0.4)

    if _join_reveal_item(sc) is None:
        # JOIN didn't get a REVEAL this match — retry a fresh match.
        catcher.close()
        return ("retry", "no REVEAL granted to JOIN", None, None)

    # JOIN holds a REVEAL. Now play out the round-2 question so we reach
    # the round-3 category pick (a between-rounds activation window).
    lq2q = _load_question(sc)
    if not lq2q.get("question"):
        catcher.close()
        return ("retry", f"round2 question did not load: {lq2q.get('phase') or lq2q}", None, None)
    if _resolve_question_round(sc, lq2q) is None:
        catcher.close()
        return ("retry", "round2 answer/reveal failed", None, None)

    # --- Round 3: category-pick phase. Activate JOIN's REVEAL here. ---
    lq3 = _load_question(sc)
    if lq3.get("phase") != "category_pick":
        catcher.close()
        return ("retry", f"round3 not category_pick: {lq3.get('phase')}", None, None)

    item = _join_reveal_item(sc)
    if item is None:
        catcher.close()
        return ("retry", "REVEAL vanished before activation", None, None)
    act = _post("/api/sp/power-up/activate", {
        "session_code": sc, "puck_id": JOIN_PUCK, "item_id": item["id"],
    })
    if act.status_code != 200 or not act.json().get("ok"):
        catcher.close()
        return ("retry", f"activate REVEAL failed: {act.status_code} {act.text[:120]}", None, None)

    # Pick a category from the offer so load-question can advance.
    offer = lq3.get("offer") or []
    picker = lq3.get("picker_puck_id")
    if offer and picker is not None:
        _post(f"/api/sp/select-category/{sc}",
              {"puck_id": picker, "category_id": offer[0]["id"]})

    # Load the round-3 question.
    lq3q = _load_question(sc)
    if not lq3q.get("question"):
        catcher.close()
        return ("retry", f"round3 question did not load: {lq3q.get('phase') or lq3q}", None, None)
    qid3 = lq3q["question"]["id"]

    # --- Critical setup: HOST answers, JOIN (holding armed REVEAL) does
    # NOT answer. Then force the reveal so JOIN is filled as TIMEOUT and
    # the REVEAL arm is applied on top of it. ---
    # Snapshot JOIN's cumulative BEFORE the round-3 reveal so the
    # corroborating check measures the DELTA the misapplied REVEAL would
    # add (~1000), not the legitimate points JOIN earned in rounds 1-2.
    ms_pre = _get(f"/api/sp/match-state/{sc}")
    cum_pre = (ms_pre.get("cumulative_scores") or {})
    catcher.join_cum_before = cum_pre.get(str(JOIN_PUCK), cum_pre.get(JOIN_PUCK, 0))
    _answer(sc, HOST_PUCK, qid3, _correct_letter(sc, qid3))
    fr = _post(f"/api/sp/force-reveal/{sc}", {})
    if fr.status_code != 200:
        catcher.close()
        return ("retry", f"force-reveal failed: {fr.status_code}", None, None)

    # Give the socket emit a beat to land.
    deadline = time.time() + 4
    while time.time() < deadline and catcher.latest_for_qid(qid3) is None:
        time.sleep(0.2)

    return ("repro", sc, qid3, catcher)


def run() -> int:
    v = Verifier()
    last_reason = ""
    outcome = sc = qid = catcher = None

    for attempt in range(1, MAX_MATCH_ATTEMPTS + 1):
        kind, a, b, c = _attempt()
        if kind == "setup":
            v.inconclusive("timed-out-puck-with-reveal-not-marked-correct",
                           f"setup failure: {a}")
            return v.report()
        if kind == "repro":
            outcome, sc, qid, catcher = kind, a, b, c
            log(f"reproduced on match attempt {attempt} (session={sc}, qid={qid})")
            break
        last_reason = str(a)
        log(f"attempt {attempt}: retry — {last_reason}")
        time.sleep(0.2)

    if outcome != "repro":
        v.inconclusive(
            "timed-out-puck-with-reveal-not-marked-correct",
            f"could not arm a REVEAL on the timed-out puck in "
            f"{MAX_MATCH_ATTEMPTS} matches (last: {last_reason})")
        return v.report()

    try:
        payload = catcher.latest_for_qid(qid)
        if not payload:
            v.inconclusive(
                "timed-out-puck-with-reveal-not-marked-correct",
                f"no reveal socket payload captured for qid={qid}")
            return v.report()

        results = payload.get("results") or []
        join_res = next((r for r in results if r.get("puck_id") == JOIN_PUCK), None)
        host_res = next((r for r in results if r.get("puck_id") == HOST_PUCK), None)
        log(f"reveal results: JOIN={join_res} HOST={host_res}")

        if join_res is None:
            v.inconclusive(
                "timed-out-puck-with-reveal-not-marked-correct",
                f"JOIN puck {JOIN_PUCK} absent from reveal results")
            return v.report()

        # JOIN never answered — answer is None confirms the TIMEOUT fill
        # path was actually exercised (not a real answer).
        v.check("timed-out-puck-was-actually-silent",
                join_res.get("answer") is None,
                f"answer={join_res.get('answer')!r}")

        # THE DECISIVE ASSERTION.
        is_correct = bool(join_res.get("is_correct"))
        points = int(join_res.get("points") or 0)
        tier = join_res.get("tier")
        v.check(
            "timed-out-puck-with-reveal-not-marked-correct",
            (is_correct is False) and (points == 0),
            f"is_correct={is_correct} points={points} tier={tier} "
            f"(bug => True/1000/LEGENDARY)")

        # Corroborate via cumulative_scores: a silent puck must not GAIN
        # ~1000 from a misapplied REVEAL. JOIN legitimately earns points
        # in rounds 1-2 (it answers those), so assert the round-3 reveal
        # added ~0, not that the absolute total is small.
        ms = _get(f"/api/sp/match-state/{sc}")
        cum = (ms.get("cumulative_scores")
               or (payload and {str(r["puck_id"]): r.get("cumulative_total")
                                for r in results}))
        join_total = None
        if isinstance(cum, dict):
            join_total = cum.get(str(JOIN_PUCK), cum.get(JOIN_PUCK))
        if join_total is None and join_res is not None:
            join_total = join_res.get("cumulative_total")
        if join_total is not None:
            before = int(catcher.join_cum_before or 0)
            delta = int(join_total) - before
            v.check(
                "timed-out-puck-reveal-did-not-inflate-cumulative",
                delta < 1000,
                f"JOIN cumulative {before}->{join_total} (delta={delta}; "
                f"bug inflates by ~1000)")
        else:
            v.inconclusive("timed-out-puck-reveal-did-not-inflate-cumulative",
                           "could not read JOIN cumulative score")
    finally:
        if catcher is not None:
            catcher.close()

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
