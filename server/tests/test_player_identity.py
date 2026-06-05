"""
Real-Postgres tests for persistent player identity (ADR 0005): the schema,
the extended final-score trigger, and the deletion semantics.

These run against an actual migrated database (the gold-standard harness in
pg_harness), so the trigger logic, the GREATEST upsert, and the
ON DELETE SET NULL / CASCADE behaviour are exercised in Postgres itself, not
asserted by reading SQL. Adversarial RLS for the new tables lives in
test_player_identity_rls.py.
"""

from __future__ import annotations

import psycopg
import pytest

from pg_harness import bootstrap_migrated_db, pg_available


LOC_P = "3a000000-0000-0000-0000-0000000000a1"
MATCH_1 = "5a000000-0000-0000-0000-000000000001"
MATCH_2 = "5a000000-0000-0000-0000-000000000002"
PLAYER_1 = "7a000000-0000-0000-0000-000000000001"
# match_pucks: 1A = match1+player, 1B = match1+anonymous, 2A = match2+player.
MP_1A = "8a000000-0000-0000-0000-00000000001a"
MP_1B = "8a000000-0000-0000-0000-00000000001b"
MP_2A = "8a000000-0000-0000-0000-00000000002a"


_SEED = f"""
insert into tenants(id,name,slug,status) values
 ('1a000000-0000-0000-0000-000000000001','TenP','tenp','trial');
insert into organizations(id,tenant_id,name,slug) values
 ('2a000000-0000-0000-0000-000000000001','1a000000-0000-0000-0000-000000000001','OrgP','orgp');
insert into locations(id,organization_id,name,slug) values
 ('{LOC_P}','2a000000-0000-0000-0000-000000000001','LocP','locp');
insert into pucks(id,serial_no,hw_revision,puck_index) values
 ('6a000000-0000-0000-0000-000000000001','SNP1','RevA',1),
 ('6a000000-0000-0000-0000-000000000002','SNP2','RevA',2);
insert into players(id,display_name) values ('{PLAYER_1}','TopGunP');
insert into matches(id,location_id,game_id,table_number,status)
 select '{MATCH_1}','{LOC_P}',g.id,1,'active' from games g where g.slug='speed_pyramid';
insert into matches(id,location_id,game_id,table_number,status)
 select '{MATCH_2}','{LOC_P}',g.id,1,'active' from games g where g.slug='speed_pyramid';
-- match1: puck1 bound to PLAYER_1, puck2 anonymous.
insert into match_pucks(id,match_id,puck_id,role,player_name,player_id) values
 ('{MP_1A}','{MATCH_1}','6a000000-0000-0000-0000-000000000001','host','TopGunP','{PLAYER_1}'),
 ('{MP_1B}','{MATCH_1}','6a000000-0000-0000-0000-000000000002','sibling','Anon',null);
-- match2: puck1 bound to PLAYER_1 again (a return visit).
insert into match_pucks(id,match_id,puck_id,role,player_name,player_id) values
 ('{MP_2A}','{MATCH_2}','6a000000-0000-0000-0000-000000000001','host','TopGunP','{PLAYER_1}');
"""


@pytest.fixture(scope="module")
def dsn():
    if not pg_available():
        pytest.skip("local Postgres (initdb/pg_ctl) not available")
    with bootstrap_migrated_db(extra_sql=_SEED, port="5602") as d:
        yield d


def _final(conn, match_id, mp_id, total):
    """Insert a final score (drives the leaderboard trigger) as superuser."""
    with conn.cursor() as cur:
        cur.execute(
            "insert into scores(match_id, match_puck_id, round_number, "
            "score_delta, score_total, event_type) "
            "values (%s,%s,0,%s,%s,'final')",
            (match_id, mp_id, total, total),
        )


def test_final_with_player_writes_both_leaderboards(dsn):
    with psycopg.connect(dsn, autocommit=True) as conn:
        _final(conn, MATCH_1, MP_1A, 1000)
        with conn.cursor() as cur:
            # Player leaderboard: one row per period (day/week/month/all_time).
            cur.execute(
                "select count(*), max(high_score) from player_leaderboards "
                "where player_id=%s",
                (PLAYER_1,),
            )
            count, high = cur.fetchone()
            assert count == 4
            assert high == 1000
            # The puck-keyed leaderboard still fired too (unchanged behaviour).
            cur.execute(
                "select count(*) from leaderboards where location_id=%s",
                (LOC_P,),
            )
            assert cur.fetchone()[0] == 4


def test_anonymous_final_writes_only_puck_leaderboard(dsn):
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("select count(*) from player_leaderboards")
            before = cur.fetchone()[0]
        _final(conn, MATCH_1, MP_1B, 500)  # MP_1B has no player_id
        with conn.cursor() as cur:
            cur.execute("select count(*) from player_leaderboards")
            assert cur.fetchone()[0] == before, "anon final touched player LB"
            # But its puck leaderboard row exists.
            cur.execute(
                "select count(*) from leaderboards lb join pucks p on p.id=lb.puck_id "
                "where p.serial_no='SNP2'"
            )
            assert cur.fetchone()[0] == 4


def test_player_leaderboard_greatest_and_match_count(dsn):
    # Two finals for one player (a return visit): high_score is the GREATEST
    # of the two and total_matches counts both. Self-contained — its own
    # player + match + match_pucks — so it doesn't depend on test order.
    pid = "7a000000-0000-0000-0000-0000000000c3"
    m3 = "5a000000-0000-0000-0000-000000000003"
    mp_a = "8a000000-0000-0000-0000-0000000000c3"
    mp_b = "8a000000-0000-0000-0000-0000000000c4"
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into players(id,display_name) values (%s,'Repeat')", (pid,)
            )
            cur.execute(
                "insert into matches(id,location_id,game_id,table_number,status) "
                "select %s,%s,g.id,1,'active' from games g where g.slug='speed_pyramid'",
                (m3, LOC_P),
            )
            cur.execute(
                "insert into match_pucks(id,match_id,puck_id,role,player_id) values "
                "(%s,%s,'6a000000-0000-0000-0000-000000000001','host',%s),"
                "(%s,%s,'6a000000-0000-0000-0000-000000000002','sibling',%s)",
                (mp_a, m3, pid, mp_b, m3, pid),
            )
        _final(conn, m3, mp_a, 1000)
        _final(conn, m3, mp_b, 1500)
        with conn.cursor() as cur:
            cur.execute(
                "select high_score, total_matches from player_leaderboards "
                "where player_id=%s and period='all_time'",
                (pid,),
            )
            high, matches = cur.fetchone()
            assert high == 1500  # GREATEST(1000, 1500)
            assert matches == 2


def test_delete_player_setnull_keeps_history_and_cascades_lb(dsn):
    # Use an isolated player so this destructive test doesn't perturb others.
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into players(id,display_name) values "
                "('7a000000-0000-0000-0000-0000000000de','Doomed') returning id"
            )
            pid = cur.fetchone()[0]
            cur.execute(
                "insert into match_pucks(id,match_id,puck_id,role,player_id) values "
                "('8a000000-0000-0000-0000-0000000000de',%s,"
                "'6a000000-0000-0000-0000-000000000002','sibling',%s)",
                (MATCH_2, pid),
            )
        _final(conn, MATCH_2, "8a000000-0000-0000-0000-0000000000de", 700)
        with conn.cursor() as cur:
            cur.execute(
                "select count(*) from player_leaderboards where player_id=%s", (pid,)
            )
            assert cur.fetchone()[0] == 4

            cur.execute("delete from players where id=%s", (pid,))

            # player_leaderboards CASCADE-deleted...
            cur.execute(
                "select count(*) from player_leaderboards where player_id=%s", (pid,)
            )
            assert cur.fetchone()[0] == 0
            # ...but the match_pucks row survives, de-attributed (SET NULL)...
            cur.execute(
                "select player_id from match_pucks where id="
                "'8a000000-0000-0000-0000-0000000000de'"
            )
            assert cur.fetchone()[0] is None
            # ...and the score (leaderboard truth) is untouched.
            cur.execute(
                "select count(*) from scores where match_puck_id="
                "'8a000000-0000-0000-0000-0000000000de' and event_type='final'"
            )
            assert cur.fetchone()[0] == 1
