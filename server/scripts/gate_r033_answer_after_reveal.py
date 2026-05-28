"""Gate for R033 — sp_answer must REJECT a late answer after the round was revealed.

THE BUG (server/pair_routes.py sp_answer, ~1890-1955):
  sp_answer guards only `current_question_id != question_id` (409) and
  `puck already in current_round_answers` (409). There is NO
  `revealed_for_question_id` guard. _maybe_emit_reveal sets
  revealed_for_question_id == qid but leaves current_question_id == qid
  until the next load-question (which is gated by the ~2500ms REVEAL_HOLD
  advance). In that window a late POST /api/sp/answer with the still-current
  question_id passes BOTH existing guards. It then:
    - overwrites the filled TIMEOUT entry in current_round_answers,
    - emits answer_locked (TV flips the revealed lane back to LOCKED),
    - calls _maybe_emit_reveal which early-returns (already revealed), so the
      late points NEVER reach cumulative_scores,
  YET record_answer DID write a DB row for that puck — compounding R029.

  This gate force-reveals a live round (which fills the silent puck as a
  0-point TIMEOUT with NO DB row), then fires a late /answer for that silent
  puck with the still-current question_id. It asserts the POST is rejected
  with HTTP 409 'round already revealed'. As corroboration it asserts the
  silent puck gains NO new DB answer row (final-results total unchanged),
  proving no spurious DB write / no R029 compounding.

Gate assertion name: answer-after-reveal-rejected
Proven: fail-on-current expected; pass-on-fix.

Fix sketch: in sp_answer, after the qid-match check add
  if state.get('revealed_for_question_id') == int(question_id):
      return jsonify({'error': 'round already revealed'}), 409

NOTE: This gate uses a browser session ONLY to pair + register two expected
pucks (the proven setup path). The bug itself is driven and observed purely
over the REST API (load-question / force-reveal / answer / final-results).
It writes nothing to the narration MP3s and runs no git.
"""
from __future__ import annotations

import sys
import time

import requests

from verify_lib import (
    BASE, log, session, pair_and_start, Verifier,
)


def _final_total(sc: str, puck_id: int) -> int | None:
    """Return the DB-backed cumulative total for puck_id from
    /api/sp/final-results, or None if the puck has no answer rows yet."""
    try:
        r = requests.get(f"{BASE}/api/sp/final-results/{sc}", timeout=5)
        if r.status_code != 200:
            return None
        for p in r.json().get("players", []):
            if int(p.get("puck_id")) == puck_id:
                return int(p.get("total") or 0)
    except Exception as e:
        log(f"final-results read failed: {e}")
    return None


def run() -> int:
    v = Verifier()
    with session() as (hub, tv):
        # Pair two pucks so the session has two expected pucks; a single
        # answer then does NOT auto-reveal — we control the reveal via
        # force-reveal, exercising exactly the window the bug lives in.
        sc = pair_and_start(hub, tv, goto_question=True)
        if not sc:
            v.inconclusive("setup", "no session_code after pairing")
            return v.report()

        # Load an active question over REST. (TV may have already loaded
        # one on mount; load-question is idempotent and returns the
        # active question rather than advancing.)
        qid = None
        for _ in range(20):
            r = requests.post(f"{BASE}/api/sp/load-question/{sc}", timeout=8)
            if r.status_code == 200:
                body = r.json()
                q = body.get("question") or {}
                if q.get("id") and body.get("phase") in (None, "question"):
                    qid = int(q["id"])
                    expected = body.get("expected_pucks") or []
                    log(f"active question id={qid} expected_pucks={expected}")
                    break
                # Pick / minigame phase — resolve it and retry. The pick
                # auto-defaults at its deadline; a short wait + retry lets
                # load-question fall through to a real question.
            time.sleep(0.6)

        if qid is None:
            v.inconclusive(
                "load active question",
                "could not obtain an active (non-phase) question over REST")
            return v.report()

        # Identify the two expected pucks. answerer = the one we'll keep
        # silent; we POST its late answer after the reveal.
        ms = requests.get(f"{BASE}/api/sp/match-state/{sc}", timeout=5).json()
        # expected_pucks isn't on match-state; pull from the load-question
        # body fetched above, else default to {0,1} (Hub pairs 0 + 1).
        expected_pucks = expected if expected else [0, 1]
        if len(expected_pucks) < 2:
            v.inconclusive(
                "two expected pucks",
                f"expected_pucks={expected_pucks}; need 2 to gate the "
                "force-reveal window without an auto-reveal")
            return v.report()
        silent_puck = int(sorted(expected_pucks)[1])
        other_puck = int(sorted(expected_pucks)[0])

        # Make sure the round timer is running so response_time scoring
        # behaves; not strictly required for the guard.
        requests.post(f"{BASE}/api/sp/start-timer/{sc}", timeout=5)

        # Answer with the OTHER puck only (so the round is NOT yet
        # complete — reveal won't auto-fire), then force the reveal.
        requests.post(f"{BASE}/api/sp/answer", json={
            "session_code": sc, "puck_id": other_puck,
            "question_id": qid, "answer": "A", "response_time_ms": 1200,
        }, timeout=8)

        fr = requests.post(f"{BASE}/api/sp/force-reveal/{sc}", timeout=8)
        reveal_ok = (fr.status_code == 200 and fr.json().get("emitted") is True)
        v.check("force-reveal fired", reveal_ok,
                f"status={fr.status_code} body={fr.text[:160]}")
        if not reveal_ok:
            v.inconclusive(
                "reveal precondition",
                "could not force the reveal; cannot exercise the late-answer "
                "window")
            return v.report()

        # The silent puck was filled as a 0-point TIMEOUT by force-reveal
        # with NO DB write. Snapshot its DB total (likely None / 0).
        total_before = _final_total(sc, silent_puck)
        log(f"silent puck {silent_puck} DB total before late answer: "
            f"{total_before}")

        # THE LATE ANSWER. current_question_id is still == qid (load-question
        # hasn't advanced yet), but revealed_for_question_id == qid now.
        # A correct, fast answer would score big if (wrongly) accepted.
        late = requests.post(f"{BASE}/api/sp/answer", json={
            "session_code": sc, "puck_id": silent_puck,
            "question_id": qid, "answer": "A", "response_time_ms": 300,
        }, timeout=8)
        log(f"late /answer -> status={late.status_code} body={late.text[:200]}")

        # DECISIVE: the late answer must be rejected with 409 'round
        # already revealed'. Current build returns 200 ok (+ points).
        try:
            late_body = late.json()
        except Exception:
            late_body = {}
        rejected = (
            late.status_code == 409
            and "already revealed" in str(late_body.get("error", "")).lower()
        )
        v.check("answer-after-reveal-rejected", rejected,
                f"status={late.status_code} body={str(late_body)[:200]} "
                f"(want 409 'round already revealed')")

        # CORROBORATION: no spurious DB row was written for the silent
        # puck (no R029 compounding). On the buggy build the 200 answer
        # calls record_answer, so a row appears (total becomes non-None /
        # may change). On the fixed build the 409 short-circuits before
        # record_answer, so the DB total is unchanged.
        total_after = _final_total(sc, silent_puck)
        log(f"silent puck {silent_puck} DB total after late answer: "
            f"{total_after}")
        no_db_write = (total_after == total_before)
        v.check("no-db-row-written-after-reveal", no_db_write,
                f"before={total_before} after={total_after} "
                "(a changed/new total proves a spurious record_answer write)")

    return v.report()


if __name__ == "__main__":
    sys.exit(run())
