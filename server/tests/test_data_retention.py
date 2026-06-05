"""
Real-Postgres tests for data retention (ADR 0006): purge_old_matches deletes
terminal matches past the window — cascading to their match_pucks + scores —
while keeping recent matches and the leaderboard aggregates.
"""

from __future__ import annotations

import psycopg
import pytest

from pg_harness import bootstrap_migrated_db, pg_available


LOC = "3c000000-0000-0000-0000-0000000000a1"
PUCK = "6c000000-0000-0000-0000-000000000001"

_SEED = f"""
insert into tenants(id,name,slug,status) values
 ('1c000000-0000-0000-0000-000000000001','TR','tr','trial');
insert into organizations(id,tenant_id,name,slug) values
 ('2c000000-0000-0000-0000-000000000001','1c000000-0000-0000-0000-000000000001','OR','or');
insert into locations(id,organization_id,name,slug) values
 ('{LOC}','2c000000-0000-0000-0000-000000000001','LR','lr');
insert into pucks(id,serial_no,hw_revision,puck_index) values
 ('{PUCK}','SNR1','RevA',1);
"""


@pytest.fixture(scope="module")
def dsn():
    if not pg_available():
        pytest.skip("local Postgres (initdb/pg_ctl) not available")
    with bootstrap_migrated_db(extra_sql=_SEED, port="5604") as d:
        yield d


def _finished_match(conn, match_id, mp_id, *, ended_days_ago, score):
    """A finished match with a final score (drives the leaderboard trigger),
    its end time backdated by ended_days_ago."""
    with conn.cursor() as cur:
        cur.execute(
            "insert into matches(id,location_id,game_id,table_number,status,ended_at) "
            "select %s,%s,g.id,1,'finished', now() - make_interval(days => %s) "
            "from games g where g.slug='speed_pyramid'",
            (match_id, LOC, ended_days_ago),
        )
        cur.execute(
            "insert into match_pucks(id,match_id,puck_id,role) values (%s,%s,%s,'host')",
            (mp_id, match_id, PUCK),
        )
        cur.execute(
            "insert into scores(match_id,match_puck_id,round_number,score_delta,"
            "score_total,event_type) values (%s,%s,0,%s,%s,'final')",
            (match_id, mp_id, score, score),
        )


def test_purge_removes_old_match_and_cascades_scores(dsn):
    old_m = "5c000000-0000-0000-0000-0000000000a1"
    old_mp = "8c000000-0000-0000-0000-0000000000a1"
    new_m = "5c000000-0000-0000-0000-0000000000b1"
    new_mp = "8c000000-0000-0000-0000-0000000000b1"
    with psycopg.connect(dsn, autocommit=True) as conn:
        _finished_match(conn, old_m, old_mp, ended_days_ago=120, score=1000)
        _finished_match(conn, new_m, new_mp, ended_days_ago=5, score=2000)

        with conn.cursor() as cur:
            cur.execute("select purge_old_matches(90)")
            purged = cur.fetchone()[0]
            assert purged == 1  # only the 120-day-old match

            # Old match + its scores cascade-deleted...
            cur.execute("select count(*) from matches where id=%s", (old_m,))
            assert cur.fetchone()[0] == 0
            cur.execute("select count(*) from scores where match_id=%s", (old_m,))
            assert cur.fetchone()[0] == 0
            cur.execute("select count(*) from match_pucks where id=%s", (old_mp,))
            assert cur.fetchone()[0] == 0

            # ...recent match untouched...
            cur.execute("select count(*) from matches where id=%s", (new_m,))
            assert cur.fetchone()[0] == 1
            cur.execute("select count(*) from scores where match_id=%s", (new_m,))
            assert cur.fetchone()[0] == 1

            # ...and the leaderboard aggregates are RETAINED (both matches'
            # finals upserted them; the purge doesn't touch them).
            cur.execute("select count(*) from leaderboards where location_id=%s", (LOC,))
            assert cur.fetchone()[0] == 4  # day/week/month/all_time, kept


def test_purge_keeps_active_matches_regardless_of_age(dsn):
    # A still-active match older than the window must NOT be purged.
    active = "5c000000-0000-0000-0000-0000000000c1"
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into matches(id,location_id,game_id,table_number,status,started_at,ended_at) "
                "select %s,%s,g.id,1,'active', now() - make_interval(days => 200), null "
                "from games g where g.slug='speed_pyramid'",
                (active, LOC),
            )
            cur.execute("select purge_old_matches(1)")
            cur.execute("select count(*) from matches where id=%s", (active,))
            assert cur.fetchone()[0] == 1  # active is never purged


def test_purge_is_idempotent(dsn):
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("select purge_old_matches(90)")
            cur.execute("select purge_old_matches(90)")
            second = cur.fetchone()[0]
            assert second == 0  # nothing left to purge on the second pass
