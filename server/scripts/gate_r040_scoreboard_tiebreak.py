"""Gate for R040 — final scoreboard must apply a documented, deterministic
tie-break (points -> faster response -> lowest puck_id) and crown ALL
co-leaders, instead of relying on engine-dependent V8 sort order.

THE BUG (mixed; this gate exercises the server-REST half that the client
physically depends on):
  final-results (pair_routes.py:1419-1435) emits only
  {puck_id, total, answered, correct, tier, color, color_name} per player —
  NO response_time aggregate, no rank, no co-leader flag. ScoreboardScreen.tsx
  (sort/isWinner, 91-95) sorts purely `(a,b)=>b.total-a.total` and sets
  isWinner = i===0 && total>0 with no secondary key, so among equal totals the
  crown lands on whichever puck V8 happens to order first. The server's
  per-round response_time tie-break (1537-1551) is applied only to reveal
  ordering, never to the final standings. Because Speed Pyramid's tier-banded
  scoring makes equal cumulative totals common (two pucks in the same tier earn
  identical points every round), the documented tie-break can never fire: the
  client has no field to break the tie with.

WHAT THIS GATE DOES (purely REST, no browser — CPU is contended):
  1. Pair host+joiner and start a match entirely via /api/pair/* (no Hub UI).
  2. Drive the full match; both pucks answer 'A' every round with DIFFERENT
     response_time_ms (joiner consistently faster). Identical answer + identical
     tier band => identical cumulative `total` for both pucks (the tie), while
     their aggregate response times differ (so a correct tie-break has a
     deterministic, observable winner: the faster puck).
  3. GET /api/sp/final-results/<code> and assert that the two pucks really did
     tie on `total` (the precondition the bug needs — if they didn't tie we
     could not exercise the tie-break, so that is INCONCLUSIVE = fail).
  4. DECISIVE: assert the payload carries a tie-break field the client can sort
     on — an aggregate response time per player (response_time_ms /
     total_response_time_ms / avg_response_ms / min_response_ms) OR a
     server-computed deterministic `rank`/`is_winner`. On the current build
     none of these exist, so the client cannot apply the documented order:
     FAIL. Once the fix adds the aggregate (and the server ranks co-leaders),
     this PASSES.
  5. If a rank/is_winner field IS present, additionally assert it is
     deterministic and tie-break-correct: the faster puck (lower aggregate
     response time) outranks the slower one, and any genuine total-tie crowns
     BOTH co-leaders rather than one arbitrary puck.

Gate assertion name: scoreboard-tie-break-deterministic
Proven: fail-on-current expected; pass-on-fix.
"""
from __future__ import annotations

import sys
import time

import requests

from verify_lib import BASE, log, Verifier


# ---------------------------------------------------------------------------
# REST driving primitives (no browser — server-rest kind)
# ---------------------------------------------------------------------------

HOST_PUCK = 1
JOINER_PUCK = 2
TIMEOUT = 8
SP_TOTAL_ROUNDS = 7

# Joiner answers fastest; host answers slower. Same letter + same tier band
# => identical cumulative totals, but distinct aggregate response times so a
# CORRECT tie-break has a single deterministic winner (the faster puck).
RESPONSE_MS = {JOINER_PUCK: 800, HOST_PUCK: 1800}

# Candidate names a fixed payload could use to surface an aggregate response
# time the client can sort on.
RESP_FIELDS = (
    "response_time_ms",
    "total_response_time_ms",
    "sum_response_time_ms",
    "avg_response_ms",
    "avg_response_time_ms",
    "min_response_ms",
    "min_response_time_ms",
    "fastest_correct_ms",
)
# Candidate names for a server-computed deterministic standing.
RANK_FIELDS = ("rank", "place", "standing")
WINNER_FIELDS = ("is_winner", "winner", "is_co_leader", "co_leader")


def _post(path: str, body: dict | None = None) -> requests.Response:
    return requests.post(f"{BASE}{path}", json=body or {}, timeout=TIMEOUT)


def _get(path: str) -> requests.Response:
    return requests.get(f"{BASE}{path}", timeout=TIMEOUT)


def pair_via_rest() -> str | None:
    """Create a lobby + start a match using only /api/pair/* endpoints.
    Returns the session_code, or None on failure."""
    _post("/api/pair/clear", {})
    time.sleep(0.2)
    r_host = _post("/api/pair/request", {"puck_id": HOST_PUCK})
    if r_host.status_code != 200:
        return None
    pair_code = r_host.json().get("pair_code")
    _post("/api/pair/request", {"puck_id": JOINER_PUCK})
    _post("/api/pair/confirm", {"puck_id": HOST_PUCK, "code": pair_code})
    r_start = _post("/api/pair/start", {"puck_id": HOST_PUCK})
    if r_start.status_code != 200:
        return None
    return r_start.json().get("session_code")


def _resolve_phase(sc: str, payload: dict) -> bool:
    """Resolve a category_pick or minigame phase via REST so the next
    load-question advances to a real question. Returns True if resolved."""
    phase = payload.get("phase")
    if phase == "category_pick":
        picker = payload.get("picker_puck_id")
        offer = payload.get("offer") or []
        if offer:
            _post(f"/api/sp/select-category/{sc}",
                  {"puck_id": picker, "category_id": int(offer[0]["id"])})
        return True
    if phase == "minigame":
        _post(f"/api/sp/minigame/finish/{sc}")
        return True
    return False


def _advance_to_question(sc: str) -> dict | None:
    """POST load-question, resolving any pick/minigame phase, until a real
    question payload (with question.id) is returned, else None."""
    for _ in range(8):
        r = _post(f"/api/sp/load-question/{sc}")
        if r.status_code == 409:
            return None  # match_complete
        if r.status_code != 200:
            time.sleep(0.3)
            continue
        body = r.json()
        if "question" in body and body["question"].get("id"):
            return body["question"]
        if _resolve_phase(sc, body):
            time.sleep(0.3)
            continue
        time.sleep(0.3)
    return None


def _answer_question(sc: str, qid: int, pucks: list[int]) -> int:
    """Each puck answers 'A' with its assigned response time. Returns the
    number of answers the server accepted (200)."""
    accepted = 0
    for pid in pucks:
        r = _post("/api/sp/answer", {
            "session_code": sc,
            "puck_id": pid,
            "question_id": qid,
            "answer": "A",
            "response_time_ms": RESPONSE_MS[pid],
        })
        if r.status_code == 200 and r.json().get("ok"):
            accepted += 1
    return accepted


def drive_full_match(sc: str, pucks: list[int]) -> int:
    """Drive every round via REST: both pucks answer 'A' (same letter, same
    tier band => equal cumulative totals), then force-reveal to close the
    round. Returns the number of rounds answered."""
    rounds = 0
    for _ in range(SP_TOTAL_ROUNDS + 2):
        q = _advance_to_question(sc)
        if not q:
            break
        _answer_question(sc, int(q["id"]), pucks)
        _post(f"/api/sp/force-reveal/{sc}")
        rounds += 1
        time.sleep(0.2)
    return rounds


def _final_results(sc: str) -> dict:
    r = _get(f"/api/sp/final-results/{sc}")
    if r.status_code != 200:
        return {}
    return r.json()


def _first_present(player: dict, names) -> str | None:
    for n in names:
        if n in player and player[n] is not None:
            return n
    return None


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------

def run() -> int:
    v = Verifier()

    sc = pair_via_rest()
    if not sc:
        v.inconclusive("setup", "pairing/start via REST failed")
        return v.report()
    log(f"session_code={sc}")

    pucks = [HOST_PUCK, JOINER_PUCK]
    rounds = drive_full_match(sc, pucks)
    log(f"drove {rounds} rounds")
    if rounds < 2:
        v.inconclusive("drive match",
                       f"only {rounds} rounds answered; cannot build a tie")
        return v.report()

    fr = _final_results(sc)
    players = fr.get("players") or []
    by_id = {int(p["puck_id"]): p for p in players}
    log(f"final-results players={players}")

    if HOST_PUCK not in by_id or JOINER_PUCK not in by_id:
        v.inconclusive(
            "both pucks present in final-results",
            f"got puck_ids={sorted(by_id)}")
        return v.report()

    host = by_id[HOST_PUCK]
    joiner = by_id[JOINER_PUCK]
    host_total = int(host.get("total") or 0)
    joiner_total = int(joiner.get("total") or 0)

    # Precondition: the two pucks must actually TIE on total for the
    # tie-break to be exercisable. Same answer + same tier band each round
    # should produce identical cumulative totals. If they didn't tie, we
    # cannot exercise the bug -> inconclusive (= fail), never a false green.
    tied = host_total == joiner_total and host_total > 0
    if not tied:
        v.inconclusive(
            "two pucks tie on total (precondition)",
            f"host_total={host_total} joiner_total={joiner_total} "
            "— identical answers should yield equal totals; cannot exercise "
            "tie-break")
        return v.report()
    log(f"TIE established: both pucks total={host_total}")

    # ---- DECISIVE ASSERTION ----------------------------------------------
    # The client (ScoreboardScreen) can only apply the documented tie-break
    # (points -> faster response -> lowest puck_id) if the payload carries a
    # field to break the tie. Accept either: (a) an aggregate response time
    # per player, OR (b) a server-computed deterministic rank/is_winner.
    resp_field = _first_present(host, RESP_FIELDS) \
        and _first_present(joiner, RESP_FIELDS)
    rank_field = _first_present(host, RANK_FIELDS) \
        and _first_present(joiner, RANK_FIELDS)
    winner_field = _first_present(host, WINNER_FIELDS) \
        or _first_present(joiner, WINNER_FIELDS)

    has_tiebreak_field = bool(resp_field or rank_field or winner_field)
    v.check(
        "scoreboard-tie-break-deterministic",
        has_tiebreak_field,
        f"resp_field={resp_field} rank_field={rank_field} "
        f"winner_field={winner_field} "
        f"payload_keys={sorted(host.keys())} — final-results must surface an "
        "aggregate response time or a server-computed rank so the client can "
        "deterministically break a points tie (points -> faster response -> "
        "lowest puck_id); the current payload exposes none, so ties resolve by "
        "engine-dependent V8 sort order")

    # ---- CORRECTNESS OF THE TIE-BREAK (only meaningful once present) -----
    # If the fix added an aggregate response time, the faster puck (joiner,
    # lower aggregate) must compare ahead of the slower puck (host).
    if resp_field:
        rf = _first_present(host, RESP_FIELDS)
        h_rt = float(host.get(rf) or 0)
        j_rt = float(joiner.get(rf) or 0)
        # avg/sum/min are all monotonic in "faster" since joiner is faster
        # on every round; faster => strictly smaller aggregate.
        v.check(
            "tie-break orders faster puck ahead (aggregate response time)",
            j_rt < h_rt,
            f"{rf}: joiner={j_rt} host={h_rt} — faster puck must have the "
            "smaller aggregate response time")

    # If the fix added a server rank, co-leaders sharing the max total must
    # both be crowned / ranked first, and rank must obey the tie-break order.
    if rank_field:
        rf = _first_present(host, RANK_FIELDS)
        h_rank = int(host.get(rf))
        j_rank = int(joiner.get(rf))
        # Faster puck (joiner) should rank ahead of host on the response-time
        # tie-break; ranks must differ deterministically (no shared arbitrary
        # ordering) yet both reflect the shared-leader total.
        v.check(
            "server rank breaks the tie deterministically (faster puck first)",
            j_rank < h_rank,
            f"{rf}: joiner_rank={j_rank} host_rank={h_rank} — faster puck "
            "must outrank slower on equal totals")

    if winner_field:
        wf = _first_present(host, WINNER_FIELDS) \
            or _first_present(joiner, WINNER_FIELDS)
        h_win = bool(host.get(wf))
        j_win = bool(joiner.get(wf))
        # On a genuine TOTAL tie the documented behaviour crowns by the
        # tie-break: exactly the faster puck wins (deterministic), OR both
        # co-leaders are crowned. Either is acceptable; what is NOT is the
        # crown landing on the SLOWER puck only.
        ok = (j_win and not h_win) or (j_win and h_win)
        v.check(
            "winner flag is deterministic on a total tie (not the slower puck)",
            ok,
            f"{wf}: joiner_win={j_win} host_win={h_win} — on equal totals the "
            "faster puck (joiner) must win, or both co-leaders are crowned; "
            "the crown must not land on the slower puck alone")

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
