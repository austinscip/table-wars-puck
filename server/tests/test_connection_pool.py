"""
Tests for the SupabaseWriter connection pool (Tier 2, item 11).

When a pool is configured, every write must borrow from it rather than
open a fresh psycopg connection; when it isn't, the direct-connect path is
unchanged (covered by test_match_creation). These use a fake pool/conn so
they run with no database.
"""

from __future__ import annotations

from contextlib import contextmanager

import psycopg

from supabase_client import SupabaseWriter


class _FakeCursor:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self.executed.append(sql)

    def fetchone(self):
        return {"id": "x"}


class _FakeConn:
    def __init__(self) -> None:
        self.cur = _FakeCursor()

    def cursor(self):
        return self.cur

    def transaction(self):
        @contextmanager
        def _txn():
            yield

        return _txn()


class _FakePool:
    def __init__(self, conn: _FakeConn) -> None:
        self._conn = conn
        self.borrows = 0
        self.closed = False

    @contextmanager
    def connection(self):
        self.borrows += 1
        yield self._conn

    def close(self):
        self.closed = True


def test_pooled_writer_borrows_from_pool(monkeypatch):
    # Guard: if anything tries to open a direct connection, fail loudly.
    def boom(*a, **k):
        raise AssertionError("pooled writer must not call psycopg.connect")

    monkeypatch.setattr(psycopg, "connect", boom)

    conn = _FakeConn()
    pool = _FakePool(conn)
    writer = SupabaseWriter(pool=pool)

    from datetime import datetime, timezone

    writer.update_match_snapshot("m1", {"k": "v"})
    writer.update_match_finished("m1", datetime.now(timezone.utc))

    assert pool.borrows == 2, "each write should borrow exactly one connection"
    assert any("update matches set snapshot" in s for s in conn.cur.executed)
    assert any("status = 'finished'" in s for s in conn.cur.executed)


def test_pooled_writer_create_match_uses_one_borrow(monkeypatch):
    monkeypatch.setattr(
        psycopg,
        "connect",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("should not direct-connect")
        ),
    )
    conn = _FakeConn()
    pool = _FakePool(conn)
    writer = SupabaseWriter(pool=pool)

    match_id, mp_ids = writer.create_match(
        location_id="loc",
        game_slug="speed_pyramid",
        table_number=1,
        pucks=[("u1", "host", "P1"), ("u2", "sibling", "P2")],
        snapshot={"s": 1},
    )
    assert pool.borrows == 1, "atomic create must use a single pooled connection"
    assert match_id == "x"
    assert mp_ids == ["x", "x"]


def test_close_closes_pool():
    pool = _FakePool(_FakeConn())
    writer = SupabaseWriter(pool=pool)
    writer.close()
    assert pool.closed


def test_direct_writer_close_is_noop():
    # No pool -> close() must not raise.
    writer = SupabaseWriter(dsn="postgresql://fake/db")
    writer.close()
