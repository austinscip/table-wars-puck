"""Game-logic edge regression tests for the runtime (audit
runtime-games-2026-06-06):

- Speed Pyramid normalizes / drops content rows with a dirty `correct` letter.
- The MatchManager force-abandons a match that exceeds the hard duration cap.
- MatchManager.tick floors dt at 0 so a timed game can't run backward.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from runtime import InputEvent

from conftest import make_players

import games.speed_pyramid as sp


def test_speed_pyramid_normalizes_and_drops_dirty_correct(monkeypatch):
    """A content row with ' a ' is normalized to 'A' (scoreable); a row with
    an invalid correct letter is dropped rather than loaded unscoreable."""
    rows = [
        {"id": 1, "question_text": "q1", "setup_text": "s",
         "answer_a": "a", "answer_b": "b", "answer_c": "c", "answer_d": "d",
         "correct_answer": " a ", "category_name": "T", "time_limit": 10},
        {"id": 2, "question_text": "q2", "setup_text": "s",
         "answer_a": "a", "answer_b": "b", "answer_c": "c", "answer_d": "d",
         "correct_answer": "X", "category_name": "T", "time_limit": 10},
    ]
    monkeypatch.setattr(sp, "_fetch_rows", lambda *a, **k: rows)
    qs = sp._load_questions_from_db(2)
    assert len(qs) == 1, "the invalid-letter row should be dropped"
    assert qs[0].correct == "A", "whitespace/case must be normalized"


def test_speed_pyramid_all_dirty_rows_falls_back_to_defaults(monkeypatch):
    """If EVERY content row is unscoreable, fall back to the built-ins — an
    empty pool would IndexError at match construction (self-review of RG-5)."""
    rows = [
        {"id": 1, "question_text": "q", "setup_text": "s",
         "answer_a": "a", "answer_b": "b", "answer_c": "c", "answer_d": "d",
         "correct_answer": "1", "category_name": "T", "time_limit": 10},
        {"id": 2, "question_text": "q", "setup_text": "s",
         "answer_a": "a", "answer_b": "b", "answer_c": "c", "answer_d": "d",
         "correct_answer": "the second one", "category_name": "T", "time_limit": 10},
    ]
    monkeypatch.setattr(sp, "_fetch_rows", lambda *a, **k: rows)
    qs = sp._load_questions_from_db(2)
    assert qs, "must not return an empty pool"
    assert qs == list(sp.DEFAULT_QUESTIONS)
    # And a match constructs without raising on the fallback pool.
    game = sp.SpeedPyramid(make_players(2))
    assert game.get_state() is not None


def test_match_force_abandons_past_duration_cap(manager, writer):
    """A match older than MAX_MATCH_DURATION_S is closed out even if it never
    reached a natural end and a puck is still nominally present."""
    players = make_players(2)
    match = manager.create(
        location_id="loc", game_slug="speed_pyramid", table_number=1,
        players=players,
        questions=[sp.Question(id=1, setup="s", question="q",
                               answers={"A": "a", "B": "b", "C": "c", "D": "d"},
                               correct="A", category="T", time_limit_ms=10_000)],
    )
    # Age the match past the hard ceiling.
    match.started_at = datetime.now(timezone.utc) - timedelta(
        seconds=manager.MAX_MATCH_DURATION_S + 1
    )
    manager.tick(match.id)
    assert match.status == "abandoned"
    assert any(mid == match.id for mid, _ in writer.abandoned)


def test_tick_floors_dt_at_zero(manager, writer):
    """A negative dt must not run a timed game's clock backward."""
    players = make_players(2)
    match = manager.create(
        location_id="loc", game_slug="puck_racer", table_number=1,
        players=players,
    )
    manager.on_input(match.id, InputEvent(puck_index=1, button_hold=True))
    manager.tick(match.id)  # advance a little
    before = match.game.elapsed_s
    manager.tick(match.id, dt=-5.0)  # would rewind 5s without the clamp
    assert match.game.elapsed_s >= before, "negative dt ran the race clock backward"
