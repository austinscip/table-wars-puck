"""
Tier 4: fleet-provisioning gate on ensure_puck.

In prod (PUCK_AUTOPROVISION=0) an unknown puck_index must NOT mint itself a
puck identity — it raises so the fleet stays explicitly managed. In dev
(default) it auto-provisions for a frictionless first pair. Uses a faked
psycopg so no DB is needed.
"""

from __future__ import annotations

import psycopg
import pytest

from supabase_client import SupabaseWriter, PuckNotProvisionedError


class _Cursor:
    def __init__(self):
        self._sql = ""

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self._sql = sql

    def fetchone(self):
        if "select p.id from pucks" in self._sql:
            return None  # puck not provisioned
        return {"id": "new-puck-uuid"}  # inserts return an id


class _Conn:
    def __init__(self):
        self._cur = _Cursor()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def cursor(self):
        return self._cur


@pytest.fixture
def fake_pg(monkeypatch):
    monkeypatch.setattr(psycopg, "connect", lambda *a, **k: _Conn())


def test_unknown_puck_raises_when_autoprovision_off(fake_pg, monkeypatch):
    monkeypatch.setenv("PUCK_AUTOPROVISION", "0")
    w = SupabaseWriter(dsn="postgresql://fake/db")
    with pytest.raises(PuckNotProvisionedError):
        w.ensure_puck(puck_index=7, location_id="loc-1")


def test_unknown_puck_autoprovisions_by_default(fake_pg, monkeypatch):
    monkeypatch.delenv("PUCK_AUTOPROVISION", raising=False)
    w = SupabaseWriter(dsn="postgresql://fake/db")
    uuid = w.ensure_puck(puck_index=7, location_id="loc-1")
    assert uuid == "new-puck-uuid"
