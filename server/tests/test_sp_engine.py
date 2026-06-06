"""Real-flow regression tests for the LIVE Speed Pyramid engine
(audit live-speed-pyramid-2026-06-06).

These drive the actual `pair_routes` Flask blueprints against a throwaway
SQLite DB (see `sp_harness.py`) — the deployed request path, not a
re-implementation. Before this file the live engine had no endpoint tests.
"""
from __future__ import annotations

import pair_routes

from sp_harness import sp_harness


def test_smoke_pair_start_load_answer_reveal(monkeypatch, tmp_path):
    """A 2-puck match pairs, starts, loads Q1, both answer, reveal fires and
    cumulative scores accrue exactly once."""
    with sp_harness(monkeypatch, tmp_path) as h:
        sc = h.pair_full([1, 2])
        assert sc

        body = h.advance_to_question(sc)
        qid = body["question"]["id"]
        assert body["round"] == 1

        # Puck 1 correct & fast (LEGENDARY=1000); puck 2 wrong (0).
        a1 = h.answer(sc, 1, qid, "A", rt_ms=1000).get_json()
        assert a1["is_correct"] is True
        assert a1["points"] == 1000
        a2 = h.answer(sc, 2, qid, "B", rt_ms=1000).get_json()
        assert a2["is_correct"] is False
        assert a2["points"] == 0
        # Both answered -> reveal emitted exactly once.
        reveals = h.sio.events("reveal")
        assert len(reveals) == 1
        results = {r["puck_id"]: r for r in reveals[0]["results"]}
        assert results[1]["cumulative_total"] == 1000
        assert results[2]["cumulative_total"] == 0


def test_double_reveal_does_not_double_score(monkeypatch, tmp_path):
    """SP-S1: under gevent the DB read inside _maybe_emit_reveal is a yield
    point, so a force-reveal and the last puck's answer can both pass the
    guard and double-score. We simulate that interleaving deterministically:
    while the last answer's reveal is doing its correct-answer DB lookup, a
    concurrent force-reveal runs (re-entry). With the atomic claim, the
    second one bails; cumulative is scored exactly once."""
    with sp_harness(monkeypatch, tmp_path) as h:
        sc = h.pair_full([1, 2])
        qid = h.advance_to_question(sc)["question"]["id"]

        # Puck 1 answers (LEGENDARY); not all answered yet so no reveal.
        h.answer(sc, 1, qid, "A", rt_ms=1000)
        assert h.sio.events("reveal") == []

        real_eq = pair_routes.execute_query
        fired = {"n": 0}

        def racing_eq(query, *a, **k):
            # The reveal's lookup is the only query selecting host_commentary.
            if fired["n"] == 0 and "host_commentary_correct" in query:
                fired["n"] += 1
                # The "other greenlet" runs while we're blocked on this I/O.
                pair_routes._maybe_emit_reveal(sc, force=True)
            return real_eq(query, *a, **k)

        monkeypatch.setattr(pair_routes, "execute_query", racing_eq)
        # Puck 2's answer triggers the reveal that re-enters mid-lookup.
        h.answer(sc, 2, qid, "B", rt_ms=1000)
        monkeypatch.setattr(pair_routes, "execute_query", real_eq)

        # The re-entry happened, proving the race window was exercised...
        assert fired["n"] == 1
        # ...but puck 1 was scored exactly once (1000, not 2000).
        st = pair_routes._SP_STATE[sc]
        assert st["cumulative_scores"][1] == 1000
        # Exactly one reveal reached the TV.
        assert len(h.sio.events("reveal")) == 1


def test_reveal_db_failure_rolls_back_claim(monkeypatch, tmp_path):
    """Self-review of SP-S1: if the reveal's correct-answer DB read fails after
    the atomic claim, the claim must roll back so a retry can still reveal —
    otherwise the round is marked revealed but never scored and the match hangs."""
    with sp_harness(monkeypatch, tmp_path) as h:
        sc = h.pair_full([1, 2])
        qid = h.advance_to_question(sc)["question"]["id"]
        h.answer(sc, 1, qid, "A", rt_ms=1000)  # puck 1; not all answered yet

        real_eq = pair_routes.execute_query
        boom = {"armed": True}

        def failing_eq(query, *a, **k):
            if boom["armed"] and "host_commentary_correct" in query:
                boom["armed"] = False
                raise RuntimeError("simulated DB blip")
            return real_eq(query, *a, **k)

        monkeypatch.setattr(pair_routes, "execute_query", failing_eq)
        # Puck 2 answers -> reveal attempt hits the failing DB read.
        h.answer(sc, 2, qid, "B", rt_ms=1000)
        st = pair_routes._SP_STATE[sc]
        assert st["revealed_for_question_id"] is None, "claim was not rolled back"
        assert h.sio.events("reveal") == [], "should not have revealed on failure"

        # DB recovers; a force-reveal now succeeds and scores exactly once.
        monkeypatch.setattr(pair_routes, "execute_query", real_eq)
        h.force_reveal(sc)
        assert st["revealed_for_question_id"] == qid
        assert len(h.sio.events("reveal")) == 1
        assert st["cumulative_scores"][1] == 1000


def test_ghost_swept_puck_is_readded_on_reconnect(monkeypatch, tmp_path):
    """SP-S2: a puck aged out by the ghost sweep is re-added to
    expected_pucks when it resumes polling, instead of being stranded while
    the match marches on without it."""
    with sp_harness(monkeypatch, tmp_path) as h:
        sc = h.pair_full([1, 2])
        h.advance_to_question(sc)
        st = pair_routes._SP_STATE[sc]
        assert st["expected_pucks"] == {1, 2}

        # Simulate puck 2 going silent past the ghost timeout, then a poll
        # that triggers the sweep (puck 1 still alive).
        pair_routes._LOBBY["players"][2]["last_seen"] = (
            pair_routes._now() - pair_routes.GHOST_TIMEOUT_S - 5
        )
        h.match_state(sc, puck_id=1)
        assert st["expected_pucks"] == {1}, "ghost sweep should have dropped puck 2"

        # Puck 2's Wi-Fi recovers and it polls again -> re-added.
        h.match_state(sc, puck_id=2)
        assert 2 in st["expected_pucks"], "reconnecting puck should be re-added"
        assert h.sio.events("player_rejoined")


def test_deliberate_leaver_is_not_readded(monkeypatch, tmp_path):
    """SP-S2 guard: a puck that explicitly left (HOLD_3S /leave-match) must
    NOT be resurrected by the reconnect reconcile even if it keeps polling."""
    with sp_harness(monkeypatch, tmp_path) as h:
        sc = h.pair_full([1, 2])
        h.advance_to_question(sc)
        h.client.post("/api/sp/leave-match",
                      json={"session_code": sc, "puck_id": 2})
        st = pair_routes._SP_STATE[sc]
        assert 2 not in st["expected_pucks"]
        assert 2 in st["left_match_pucks"]

        # Even a poll from the departed puck does not re-add it.
        h.match_state(sc, puck_id=2)
        assert 2 not in st["expected_pucks"]


def test_negative_response_time_is_clamped(monkeypatch, tmp_path):
    """SP-S3: a negative puck-reported response_time_ms must not be stored
    (it would corrupt the response-time tie-break in final-results)."""
    with sp_harness(monkeypatch, tmp_path) as h:
        sc = h.pair_full([1])
        qid = h.advance_to_question(sc)["question"]["id"]
        body = h.answer(sc, 1, qid, "A", rt_ms=-500).get_json()
        assert body["response_time_ms"] >= 0
        # And the persisted aggregate is non-negative.
        fr = h.final_results(sc).get_json()
        p1 = next(p for p in fr["players"] if p["puck_id"] == 1)
        assert p1["sum_response_time_ms"] >= 0
        assert p1["avg_response_ms"] >= 0


def test_play_again_reset_keeps_powerup_fields(monkeypatch, tmp_path):
    """SP-CR3: sp_reset used to overwrite state with a dict missing every
    Slice E field, so the first power-up grant after a Play-Again hit a
    KeyError. The shared _fresh_sp_state factory keeps them present."""
    with sp_harness(monkeypatch, tmp_path) as h:
        sc = h.pair_full([1, 2])
        h.advance_to_question(sc)
        h.client.post(f"/api/sp/reset/{sc}")
        st = pair_routes._SP_STATE[sc]
        for field in ("power_up_inventories", "power_up_arms",
                      "pending_category_pick", "pending_minigame",
                      "minigame_resolved_round", "next_category_id",
                      "last_round_winner_puck_id", "left_match_pucks"):
            assert field in st, f"reset dropped {field}"
