"""
Regression tests for transactional match creation (Tier 1, item 3).

Two layers:
  - Manager level: if the atomic writer call fails, the manager registers
    nothing — no half-created match in memory, no heartbeat/scheduler
    state pointing at a row that doesn't exist.
  - Writer level: SupabaseWriter.create_match issues the match row, every
    match_puck row, and the seed snapshot inside ONE connection and ONE
    transaction, and a failure mid-create propagates out of the
    transaction context (rollback), leaving nothing committed.

The writer test fakes psycopg so it runs with no database.
"""

from __future__ import annotations

import pytest

import psycopg

from runtime import MatchManager, registry as game_registry
from supabase_client import SupabaseWriter

from conftest import make_players
from games.speed_pyramid import Question


def _fixture():
    return [
        Question(
            id=1,
            setup="s",
            question="q",
            answers={"A": "a", "B": "b", "C": "c", "D": "d"},
            correct="A",
            category="T",
            time_limit_ms=10_000,
        )
    ]


# ---------------------------------------------------------------------------
# Manager level
# ---------------------------------------------------------------------------


def test_manager_create_failure_registers_nothing(manager, writer):
    players = make_players(2)

    def boom(**kwargs):
        raise RuntimeError("db down mid-create")

    writer.create_match = boom

    with pytest.raises(RuntimeError):
        manager.create(
            location_id="loc",
            game_slug="speed_pyramid",
            table_number=1,
            players=players,
            questions=_fixture(),
        )

    assert manager.matches == {}, "a failed create left a match registered"
    # No heartbeat state was seeded for a match that never came to exist.
    assert manager.heartbeat._beats == {}


def test_manager_create_happy_path_maps_puck_ids(manager, writer):
    players = make_players(3)
    match = manager.create(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        players=players,
        questions=_fixture(),
    )
    # Every puck_index maps to the match_puck id the writer returned, in
    # order.
    for p in players:
        assert match.match_puck_ids[p.puck_index] == writer.match_pucks[
            (match.id, p.puck_uuid)
        ]
    # A seed snapshot was written as part of creation (the TV paints
    # immediately, no blank frame).
    assert any(mid == match.id for mid, _ in writer.snapshots)


# ---------------------------------------------------------------------------
# Writer level — single connection, single transaction, rollback on failure
# ---------------------------------------------------------------------------


class _Recorder:
    def __init__(self) -> None:
        self.connect_calls = 0
        self.executes: list[str] = []
        self.transactions_entered = 0
        self.transaction_exit_excs: list = []
        self.fail_on: str | None = None


class _FakeCursor:
    def __init__(self, rec: _Recorder) -> None:
        self.rec = rec
        self._last = ""
        self._mp = 0

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self.rec.executes.append(sql)
        self._last = sql
        if self.rec.fail_on and self.rec.fail_on in sql:
            raise RuntimeError("db boom")

    def fetchone(self):
        s = self._last
        if "from games" in s:
            return {"id": "game-1"}
        if "insert into matches" in s:
            return {"id": "match-1"}
        if "insert into match_pucks" in s:
            self._mp += 1
            return {"id": f"mp-{self._mp}"}
        return None


class _FakeTxn:
    def __init__(self, rec: _Recorder) -> None:
        self.rec = rec

    def __enter__(self):
        self.rec.transactions_entered += 1
        return self

    def __exit__(self, exc_type, exc, tb):
        self.rec.transaction_exit_excs.append(exc_type)
        return False  # propagate any exception (real psycopg rolls back)


class _FakeConn:
    def __init__(self, rec: _Recorder) -> None:
        self.rec = rec
        self._cur = _FakeCursor(rec)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def transaction(self):
        return _FakeTxn(self.rec)

    def cursor(self):
        return self._cur


@pytest.fixture
def fake_psycopg(monkeypatch):
    rec = _Recorder()

    def fake_connect(dsn, **kwargs):
        rec.connect_calls += 1
        return _FakeConn(rec)

    monkeypatch.setattr(psycopg, "connect", fake_connect)
    return rec


def test_create_match_is_single_transaction(fake_psycopg):
    writer = SupabaseWriter(dsn="postgresql://fake/db")
    match_id, mp_ids = writer.create_match(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        pucks=[("uuid-1", "host", "P1"), ("uuid-2", "sibling", "P2")],
        snapshot={"hello": "world"},
    )

    rec = fake_psycopg
    assert rec.connect_calls == 1, "create must use exactly one connection"
    assert rec.transactions_entered == 1, "all writes must share one txn"
    # Match insert, both puck inserts, and the snapshot update all ran.
    assert any("insert into matches" in s for s in rec.executes)
    assert sum("insert into match_pucks" in s for s in rec.executes) == 2
    assert any("update matches set snapshot" in s for s in rec.executes)
    # Committed cleanly — the transaction context exited with no exception.
    assert rec.transaction_exit_excs == [None]
    assert match_id == "match-1"
    assert mp_ids == ["mp-1", "mp-2"]


def test_create_match_rolls_back_on_failure(fake_psycopg):
    fake_psycopg.fail_on = "update matches set snapshot"
    writer = SupabaseWriter(dsn="postgresql://fake/db")

    with pytest.raises(RuntimeError):
        writer.create_match(
            location_id="loc",
            game_slug="speed_pyramid",
            table_number=1,
            pucks=[("uuid-1", "host", "P1")],
            snapshot={"x": 1},
        )

    rec = fake_psycopg
    assert rec.connect_calls == 1
    # The transaction context saw the exception, so the real driver would
    # roll back the partial match + puck rows.
    assert rec.transaction_exit_excs and rec.transaction_exit_excs[-1] is RuntimeError
