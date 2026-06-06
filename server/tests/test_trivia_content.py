"""
Unit + integration tests for the trivia content cache (ADR 0008): cloud
sync with version-skip, offline resilience (keep cache on failure), local
selection, the JSON cache file, and Speed Pyramid pulling from the source.
No DB — a fake reader stands in for the SupabaseWriter.
"""

from __future__ import annotations

import pytest

from runtime import TriviaContentCache

import games.speed_pyramid as sp
from games.speed_pyramid import SpeedPyramid, DEFAULT_QUESTIONS
from conftest import make_players


def _q(qid, difficulty="easy"):
    return {
        "id": qid,
        "question_text": f"Q{qid}?",
        "setup_text": "s",
        "answer_a": "a", "answer_b": "b", "answer_c": "c", "answer_d": "d",
        "correct_answer": "A",
        "category_name": "Test",
        "difficulty": difficulty,
        "time_limit": 12,
    }


class FakeReader:
    def __init__(self, bank, version="v1"):
        self.bank = bank
        self.version = version
        self.fail = False
        self.bank_fetches = 0

    def get_active_trivia_questions(self):
        if self.fail:
            raise RuntimeError("offline")
        self.bank_fetches += 1
        return list(self.bank)

    def trivia_content_version(self):
        if self.fail:
            raise RuntimeError("offline")
        return self.version


@pytest.fixture
def cache_path(tmp_path):
    return str(tmp_path / "trivia.json")


@pytest.fixture(autouse=True)
def _clear_source():
    # The question source is a module global; never leak it across tests.
    yield
    sp.set_question_source(None)


def test_refresh_populates_bank_and_version(cache_path):
    reader = FakeReader([_q(1), _q(2)], version="v9")
    cache = TriviaContentCache(reader, cache_path=cache_path)
    assert cache.refresh() is True
    assert cache.size == 2
    assert cache.version == "v9"


def test_refresh_skips_when_version_unchanged(cache_path):
    reader = FakeReader([_q(1)], version="v1")
    cache = TriviaContentCache(reader, cache_path=cache_path)
    cache.refresh()
    assert reader.bank_fetches == 1
    # Same version -> no re-fetch of the bank.
    assert cache.refresh() is False
    assert reader.bank_fetches == 1


def test_refresh_keeps_cache_when_offline(cache_path):
    reader = FakeReader([_q(1), _q(2)], version="v1")
    cache = TriviaContentCache(reader, cache_path=cache_path)
    cache.refresh()
    reader.fail = True  # internet drops
    assert cache.refresh() is False
    assert cache.size == 2  # cache intact — still serving trivia


def test_load_filters_difficulty_and_excludes(cache_path):
    reader = FakeReader(
        [_q(1, "easy"), _q(2, "hard"), _q(3, "easy"), _q(4, "easy")]
    )
    cache = TriviaContentCache(reader, cache_path=cache_path)
    cache.refresh()
    got = cache.load(10, difficulty="easy", exclude_ids=[1])
    ids = {q["id"] for q in got}
    assert ids <= {3, 4}  # only easy, not the excluded #1, not the hard #2


def test_load_relaxes_exclusions_when_pool_empty(cache_path):
    reader = FakeReader([_q(1), _q(2)])
    cache = TriviaContentCache(reader, cache_path=cache_path)
    cache.refresh()
    # Player has "seen" everything — still gets a game rather than nothing.
    got = cache.load(2, exclude_ids=[1, 2])
    assert got and len(got) == 2


def test_load_returns_none_when_empty(cache_path):
    reader = FakeReader([], version="v0")
    cache = TriviaContentCache(reader, cache_path=cache_path)
    assert cache.load(5) is None


def test_cache_file_survives_restart_offline(cache_path):
    # First cache populates the file.
    TriviaContentCache(FakeReader([_q(1), _q(2)]), cache_path=cache_path).refresh()
    # A fresh cache whose reader is offline still serves from the file.
    offline = FakeReader([], version="v0")
    offline.fail = True
    cache2 = TriviaContentCache(offline, cache_path=cache_path)
    assert cache2.size == 2
    assert cache2.load(2) is not None


def test_speed_pyramid_pulls_from_configured_source(cache_path):
    reader = FakeReader([_q(101), _q(102), _q(103)])
    cache = TriviaContentCache(reader, cache_path=cache_path)
    cache.refresh()
    sp.set_question_source(cache.load)

    game = SpeedPyramid(players=make_players(2), question_count=3)
    assert len(game.questions) == 3
    assert all(q.id in {101, 102, 103} for q in game.questions)


def test_load_skips_invalid_rows(cache_path):
    # Audit 2.8: a corrupt/poisoned cache row must be skipped, not crash load.
    cache = TriviaContentCache(FakeReader([_q(1)]), cache_path=cache_path)
    cache.refresh()
    cache._bank.append({"id": 2})  # missing required keys
    got = cache.load(10)
    assert got and all(q["id"] == 1 for q in got)


def test_load_returns_none_on_all_invalid(cache_path):
    cache = TriviaContentCache(FakeReader([]), cache_path=cache_path)
    cache._bank = [{"garbage": True}]  # no valid rows
    assert cache.load(5) is None  # graceful fallback, no crash


def test_speed_pyramid_clamps_bad_question_count():
    # Audit 2.7: a bad question_count can't crash construction.
    g0 = SpeedPyramid(players=make_players(2), question_count=0)
    assert len(g0.questions) >= 1
    gneg = SpeedPyramid(players=make_players(2), question_count=-5)
    assert len(gneg.questions) >= 1


def test_speed_pyramid_falls_back_gracefully_without_source():
    # No source configured -> the game still gets a playable question set
    # (legacy local SQLite if present, else built-in defaults). The
    # guarantee is "never crash / never empty", not which fallback wins.
    sp.set_question_source(None)
    game = SpeedPyramid(players=make_players(2), question_count=3)
    assert len(game.questions) >= 1
