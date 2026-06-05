"""
Tests for transaction-pooler compatibility (ADR 0007): the SupabaseWriter
detects Supabase's :6543 pooler and disables server-side prepared statements
(which break in transaction mode), while direct connections keep them. A
real-Postgres test proves the pooler-safe config still drives the writer.
"""

from __future__ import annotations

import psycopg
import pytest

from supabase_client import (
    SupabaseWriter,
    _conn_kwargs,
    _is_transaction_pooler,
)

from pg_harness import bootstrap_migrated_db, pg_available


# --- detection ---

def test_detects_pooler_by_port():
    direct = "postgresql://postgres:pw@db.abc.supabase.co:5432/postgres"
    pooler = "postgresql://postgres.abc:pw@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
    assert _is_transaction_pooler(direct) is False
    assert _is_transaction_pooler(pooler) is True
    assert _is_transaction_pooler(None) is False


def test_env_override_forces_pooler(monkeypatch):
    monkeypatch.setenv("PGBOUNCER_TRANSACTION_MODE", "1")
    # Even a :5432 DSN is treated as pooler when ops force it.
    assert _is_transaction_pooler("postgresql://x:y@h:5432/db") is True


def test_conn_kwargs_disable_prepared_statements_on_pooler():
    direct = "postgresql://x:y@h:5432/db"
    pooler = "postgresql://x:y@h:6543/db"
    assert "prepare_threshold" not in _conn_kwargs(direct)
    assert _conn_kwargs(pooler)["prepare_threshold"] is None
    # row_factory is always set so cur.fetchone()['id'] works.
    assert _conn_kwargs(direct)["row_factory"] is not None


def test_writer_picks_up_pooler_kwargs():
    w = SupabaseWriter(dsn="postgresql://x:y@h:6543/db")
    assert w._connect_kwargs.get("prepare_threshold") is None
    w2 = SupabaseWriter(dsn="postgresql://x:y@h:5432/db")
    assert "prepare_threshold" not in w2._connect_kwargs


# --- real Postgres: pooler-safe config still drives the writer ---

_SEED = """
insert into tenants(id,name,slug,status) values
 ('1d000000-0000-0000-0000-000000000001','TP','tp','trial');
insert into organizations(id,tenant_id,name,slug) values
 ('2d000000-0000-0000-0000-000000000001','1d000000-0000-0000-0000-000000000001','OP','op');
insert into locations(id,organization_id,name,slug) values
 ('3d000000-0000-0000-0000-0000000000a1','2d000000-0000-0000-0000-000000000001','LP','lp');
insert into pucks(id,serial_no,hw_revision,puck_index) values
 ('6d000000-0000-0000-0000-000000000001','SNP','RevA',1);
"""


@pytest.fixture(scope="module")
def dsn():
    if not pg_available():
        pytest.skip("local Postgres (initdb/pg_ctl) not available")
    with bootstrap_migrated_db(extra_sql=_SEED, port="5605") as d:
        yield d


def test_writer_works_with_prepared_statements_disabled(dsn, monkeypatch):
    # Force pooler mode so the writer connects with prepare_threshold=None,
    # then prove the full write path (incl. create_match's transaction)
    # still works against real Postgres.
    monkeypatch.setenv("PGBOUNCER_TRANSACTION_MODE", "1")
    writer = SupabaseWriter(dsn=dsn)
    assert writer._connect_kwargs.get("prepare_threshold") is None

    match_id, mp_ids = writer.create_match(
        location_id="3d000000-0000-0000-0000-0000000000a1",
        game_slug="speed_pyramid",
        table_number=1,
        pucks=[("6d000000-0000-0000-0000-000000000001", "host", "P1")],
        snapshot={"seed": True},
    )
    assert match_id and len(mp_ids) == 1

    # A couple more round-trips to exercise statements that psycopg would
    # normally prepare after repetition — must work with preparing disabled.
    from datetime import datetime, timezone

    for _ in range(6):
        writer.insert_score(
            match_id=match_id, match_puck_id=mp_ids[0], round_number=1,
            score_delta=10, score_total=10, event_type="round",
        )
    writer.update_match_finished(match_id, datetime.now(timezone.utc))

    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("select status from matches where id=%s", (match_id,))
            assert cur.fetchone()[0] == "finished"
            cur.execute("select count(*) from scores where match_id=%s", (match_id,))
            assert cur.fetchone()[0] == 6
