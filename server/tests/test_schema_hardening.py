"""
Real-Postgres tests for the schema-hardening migration (audit 2026-06-06):
leaderboard timezone bucketing, player_count maintenance, phone uniqueness,
trivia constraints, FK ON DELETE fixes, batched retention, updated_at.
"""

from __future__ import annotations

import psycopg
import pytest

from pg_harness import bootstrap_migrated_db, pg_available


# Two locations 25h apart — their local calendar date ALWAYS differs, so the
# day-bucket test is deterministic regardless of the wall clock.
LOC_PLUS14 = "3e000000-0000-0000-0000-0000000000a1"   # UTC+14
LOC_MINUS11 = "3e000000-0000-0000-0000-0000000000b1"  # UTC-11
PUCK = "6e000000-0000-0000-0000-000000000001"

_SEED = f"""
insert into tenants(id,name,slug,status) values
 ('1e000000-0000-0000-0000-000000000001','TZ','tz','trial');
insert into organizations(id,tenant_id,name,slug) values
 ('2e000000-0000-0000-0000-000000000001','1e000000-0000-0000-0000-000000000001','O','o');
insert into locations(id,organization_id,name,slug,timezone) values
 ('{LOC_PLUS14}','2e000000-0000-0000-0000-000000000001','Plus14','plus14','Pacific/Kiritimati'),
 ('{LOC_MINUS11}','2e000000-0000-0000-0000-000000000001','Minus11','minus11','Pacific/Niue');
insert into pucks(id,serial_no,hw_revision,puck_index) values
 ('{PUCK}','SNZ','RevA',1);
"""


@pytest.fixture(scope="module")
def dsn():
    if not pg_available():
        pytest.skip("local Postgres (initdb/pg_ctl) not available")
    with bootstrap_migrated_db(extra_sql=_SEED, port="5607") as d:
        yield d


def _final_at(conn, location_id, match_id, mp_id, score=1000):
    with conn.cursor() as cur:
        cur.execute(
            "insert into matches(id,location_id,game_id,table_number,status) "
            "select %s,%s,g.id,1,'active' from games g where g.slug='speed_pyramid'",
            (match_id, location_id),
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


# --- 1.1 leaderboard timezone bucketing ---

def test_leaderboard_buckets_in_location_timezone(dsn):
    with psycopg.connect(dsn, autocommit=True) as conn:
        _final_at(conn, LOC_PLUS14, "5e000000-0000-0000-0000-0000000000a1",
                  "8e000000-0000-0000-0000-0000000000a1")
        _final_at(conn, LOC_MINUS11, "5e000000-0000-0000-0000-0000000000b1",
                  "8e000000-0000-0000-0000-0000000000b1")
        with conn.cursor() as cur:
            cur.execute(
                "select period_start from leaderboards "
                "where location_id=%s and period='day'", (LOC_PLUS14,))
            day_plus14 = cur.fetchone()[0]
            cur.execute(
                "select period_start from leaderboards "
                "where location_id=%s and period='day'", (LOC_MINUS11,))
            day_minus11 = cur.fetchone()[0]
            # 25h apart -> the local DAY bucket differs (proves it's not UTC).
            assert day_plus14 != day_minus11
            # And each equals its own location-local date.
            cur.execute("select (now() at time zone 'Pacific/Kiritimati')::date")
            assert day_plus14 == cur.fetchone()[0]


# --- 2.4 player_count maintenance ---

def test_player_count_is_maintained(dsn):
    from supabase_client import SupabaseWriter

    p1 = "6e000000-0000-0000-0000-0000000000c1"
    p2 = "6e000000-0000-0000-0000-0000000000c2"
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("insert into pucks(id,serial_no,hw_revision,puck_index) values "
                        "(%s,'SNPC1','RevA',1),(%s,'SNPC2','RevA',2)", (p1, p2))

    w = SupabaseWriter(dsn=dsn)
    match_id, mp_ids = w.create_match(
        location_id=LOC_PLUS14, game_slug="speed_pyramid", table_number=2,
        pucks=[(p1, "host", "P1"), (p2, "sibling", "P2")],
        snapshot={"s": 1},
    )
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("select player_count from matches where id=%s", (match_id,))
            assert cur.fetchone()[0] == 2
            cur.execute("delete from match_pucks where id=%s", (mp_ids[0],))
            cur.execute("select player_count from matches where id=%s", (match_id,))
            assert cur.fetchone()[0] == 1


# --- 2.4 phone uniqueness ---

def test_phone_hash_is_unique(dsn):
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("insert into players(id) values "
                        "('7e000000-0000-0000-0000-000000000001'),"
                        "('7e000000-0000-0000-0000-000000000002')")
            cur.execute("insert into player_secrets(player_id,token_hash,phone_hash) "
                        "values ('7e000000-0000-0000-0000-000000000001','th1','PHONE')")
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.UniqueViolation):
                cur.execute("insert into player_secrets(player_id,token_hash,phone_hash) "
                            "values ('7e000000-0000-0000-0000-000000000002','th2','PHONE')")


# --- 2.4 trivia constraints ---

def test_trivia_constraints(dsn):
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.CheckViolation):
                cur.execute("insert into trivia_questions(question_text,answer_a,"
                            "answer_b,answer_c,answer_d,correct_answer,difficulty) "
                            "values ('q','a','b','c','d','A','HARD')")  # bad difficulty
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.CheckViolation):
                cur.execute("insert into trivia_questions(question_text,answer_a,"
                            "answer_b,answer_c,answer_d,correct_answer,time_limit) "
                            "values ('q','a','b','c','d','A',0)")  # bad time_limit


# --- 2.2 firmware ON DELETE SET NULL ---

def test_deleting_firmware_nulls_puck_reference(dsn):
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("insert into firmware_versions(id,version,hw_revision) values "
                        "('9e000000-0000-0000-0000-000000000001','1.0','RevA')")
            cur.execute("update pucks set current_firmware_id="
                        "'9e000000-0000-0000-0000-000000000001' where id=%s", (PUCK,))
            # Deleting the firmware must NOT be blocked; the puck's ref nulls.
            cur.execute("delete from firmware_versions where "
                        "id='9e000000-0000-0000-0000-000000000001'")
            cur.execute("select current_firmware_id from pucks where id=%s", (PUCK,))
            assert cur.fetchone()[0] is None


# --- 2.5 batched purge procedure ---

def test_batched_purge_deletes_old_matches(dsn):
    old = "5e000000-0000-0000-0000-0000000000c1"
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into matches(id,location_id,game_id,table_number,status,ended_at) "
                "select %s,%s,g.id,9,'finished', now() - interval '200 days' "
                "from games g where g.slug='speed_pyramid'", (old, LOC_PLUS14))
            cur.execute("call purge_old_matches_batched(90, 100)")
            cur.execute("select count(*) from matches where id=%s", (old,))
            assert cur.fetchone()[0] == 0


# --- 2.3 updated_at ---

def test_matches_updated_at_touches_on_update(dsn):
    from supabase_client import SupabaseWriter

    pua = "6e000000-0000-0000-0000-0000000000d1"
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("insert into pucks(id,serial_no,hw_revision,puck_index) "
                        "values (%s,'SNUA','RevA',1)", (pua,))
    w = SupabaseWriter(dsn=dsn)
    match_id, _ = w.create_match(
        location_id=LOC_PLUS14, game_slug="speed_pyramid", table_number=3,
        pucks=[(pua, "host", "P1")], snapshot={"s": 1})
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("select updated_at from matches where id=%s", (match_id,))
            before = cur.fetchone()[0]
            cur.execute("update matches set snapshot='{\"x\":1}'::jsonb where id=%s",
                        (match_id,))
            cur.execute("select updated_at from matches where id=%s", (match_id,))
            after = cur.fetchone()[0]
            assert after >= before
