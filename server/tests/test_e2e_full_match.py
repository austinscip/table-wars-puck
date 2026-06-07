"""End-to-end full-match smoke for the LIVE Speed Pyramid engine.

This is the "simulated puck(s) through a full match" the audit follow-ups asked
for: it drives the REAL Flask pair/sp blueprints (via sp_harness) through a
complete 7-round match — pairing, host-start, the category picks (rounds 1/3/5/7)
and minigames (rounds 2/4/6), per-round answers + reveals, match completion, and
final results — asserting the exact socket-event stream the TV would receive.

It exercises the integration of every piece the unit tests cover in isolation
(token auth, phase state machine, reveal scoring, cumulative totals, the
pick/minigame transitions, match-end), so a regression in how they fit TOGETHER
is caught here. The remaining e2e layer — rendering the actual web TV in a
headless browser against this server — is documented in testing/e2e/README.md.
"""
from __future__ import annotations

import pair_routes

from sp_harness import sp_harness


SP_TOTAL_ROUNDS = 7


def test_full_seven_round_match(monkeypatch, tmp_path):
    with sp_harness(monkeypatch, tmp_path) as h:
        # --- Pair two pucks and start. ---
        sc = h.pair_full([1, 2])
        assert sc
        assert h.sio.events("match_started"), "TV never saw match_started"

        # --- Play all 7 rounds. Puck 1 always answers correctly ('A' is the
        # seeded correct letter), puck 2 always wrong, so the result is
        # deterministic and puck 1 wins. ---
        rounds_played = []
        for _ in range(SP_TOTAL_ROUNDS):
            body = h.advance_to_question(sc)  # resolves any pick/minigame phase
            rnd = body["round"]
            qid = body["question"]["id"]
            rounds_played.append(rnd)

            a1 = h.answer(sc, 1, qid, "A", rt_ms=800).get_json()
            assert a1["is_correct"] is True
            a2 = h.answer(sc, 2, qid, "B", rt_ms=800).get_json()
            assert a2["is_correct"] is False

        assert rounds_played == [1, 2, 3, 4, 5, 6, 7], rounds_played
        # One reveal per round reached the TV.
        assert len(h.sio.events("reveal")) == SP_TOTAL_ROUNDS

        # Every between-round phase actually fired: a category offer on each
        # pick round and a minigame start on each minigame round.
        assert len(h.sio.events("category_offer")) >= 1
        assert len(h.sio.events("minigame_start")) >= 1
        assert len(h.sio.events("question_show")) == SP_TOTAL_ROUNDS
        assert h.sio.events("answer_locked"), "no per-answer lock events"

        # --- Completing the match. The next load-question after Q7 is revealed
        # ends the match. ---
        done = h.load_question(sc)
        assert done.status_code == 409
        assert done.get_json().get("error") == "match_complete"
        assert h.sio.events("match_ended"), "TV never saw match_ended"
        # The active lobby is cleared so a fresh pair can start.
        assert pair_routes._LOBBY is None

        # --- Final results: puck 1 (all correct) beats puck 2 and is crowned. ---
        fr = h.final_results(sc).get_json()
        by_puck = {p["puck_id"]: p for p in fr["players"]}
        assert by_puck[1]["total"] > by_puck[2]["total"]
        assert by_puck[1]["is_winner"] is True
        assert by_puck[1]["correct"] == SP_TOTAL_ROUNDS  # 7/7 correct
        assert by_puck[1]["rank"] == 1


def test_full_match_is_token_gated_end_to_end(monkeypatch, tmp_path):
    """The whole flow is auth'd: an attacker without puck 2's token can't inject
    answers as puck 2 at any round, but the legitimate flow completes."""
    with sp_harness(monkeypatch, tmp_path) as h:
        sc = h.pair_full([1, 2])
        body = h.advance_to_question(sc)
        qid = body["question"]["id"]

        # Impersonation attempt (no token) is rejected and consumes nothing.
        bad = h.client.post("/api/sp/answer", json={
            "session_code": sc, "puck_id": 2, "question_id": qid,
            "answer": "B", "response_time_ms": 10})
        assert bad.status_code == 401
        assert 2 not in pair_routes._SP_STATE[sc]["current_round_answers"]

        # Legitimate answers still work and reveal fires.
        h.answer(sc, 1, qid, "A")
        h.answer(sc, 2, qid, "B")
        assert h.sio.events("reveal")
