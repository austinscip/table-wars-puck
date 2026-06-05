"""
Adversarial RLS for the player-identity tables (ADR 0005), against a REAL
Postgres. A global, tenant-independent table is a new RLS shape, so we prove
the load-bearing guarantees in the database itself:

- players is a public HANDLE but NOT enumerable: a reader sees only players
  who stand on a leaderboard at a location they can see — never the global
  base.
- player_secrets (token + phone hashes) is reachable by NOBODY except
  service_role (RLS enabled, no policy).
- player_leaderboards is location-scoped like the puck leaderboards.
- anon (the TV) is scoped by its signed location_id token and fails closed
  with no token.
- clients never write identity rows (service_role only).
"""

from __future__ import annotations

import json

import psycopg
import pytest

from pg_harness import bootstrap_migrated_db, pg_available


ORG_A = "92000000-0000-0000-0000-00000000000a"
ORG_B = "92000000-0000-0000-0000-00000000000b"
LOC_A = "93000000-0000-0000-0000-0000000000aa"
LOC_B = "93000000-0000-0000-0000-0000000000bb"
USER_A = "94000000-0000-0000-0000-00000000000a"
USER_B = "94000000-0000-0000-0000-00000000000b"
USER_SUPER = "94000000-0000-0000-0000-00000000000f"
P1 = "97000000-0000-0000-0000-000000000001"  # plays at LOC_A
P2 = "97000000-0000-0000-0000-000000000002"  # plays at LOC_B


_SEED = f"""
insert into tenants(id,name,slug,status) values
 ('91000000-0000-0000-0000-000000000001','T1','t1','trial'),
 ('91000000-0000-0000-0000-000000000002','T2','t2','trial');
insert into organizations(id,tenant_id,name,slug) values
 ('{ORG_A}','91000000-0000-0000-0000-000000000001','OA','oa'),
 ('{ORG_B}','91000000-0000-0000-0000-000000000002','OB','ob');
insert into locations(id,organization_id,name,slug) values
 ('{LOC_A}','{ORG_A}','LA','la'),('{LOC_B}','{ORG_B}','LB','lb');
insert into auth.users(id,email) values
 ('{USER_A}','a@x.com'),('{USER_B}','b@x.com'),('{USER_SUPER}','s@x.com');
insert into user_org_roles(user_id,organization_id,role) values
 ('{USER_A}','{ORG_A}','org_admin'),
 ('{USER_B}','{ORG_B}','org_admin'),
 ('{USER_SUPER}','{ORG_A}','super_admin');
insert into players(id,display_name) values ('{P1}','AAA'),('{P2}','BBB');
insert into player_secrets(player_id,token_hash,phone_hash) values
 ('{P1}','tokhash1','phonehash1'),
 ('{P2}','tokhash2','phonehash2');
insert into player_leaderboards(player_id,game_id,location_id,period,period_start,high_score,total_matches)
 select '{P1}',g.id,'{LOC_A}','all_time','1970-01-01',1000,1 from games g where g.slug='speed_pyramid';
insert into player_leaderboards(player_id,game_id,location_id,period,period_start,high_score,total_matches)
 select '{P2}',g.id,'{LOC_B}','all_time','1970-01-01',2000,1 from games g where g.slug='speed_pyramid';
"""


@pytest.fixture(scope="module")
def dsn():
    if not pg_available():
        pytest.skip("local Postgres (initdb/pg_ctl) not available")
    with bootstrap_migrated_db(extra_sql=_SEED, port="5603") as d:
        yield d


def _count_as(dsn, table, *, role, sub=None, claims=None, where=""):
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(f"set role {role}")
            if sub is not None:
                cur.execute(
                    "select set_config('request.jwt.claim.sub', %s, true)", (sub,)
                )
            if claims is not None:
                cur.execute(
                    "select set_config('request.jwt.claims', %s, true)", (claims,)
                )
            cur.execute(f"select count(*) from {table} {where}")
            n = cur.fetchone()[0]
        conn.rollback()
    return n


def _loc_claims(location_id):
    return json.dumps({"role": "anon", "location_id": location_id})


# --- players: public handle, but not enumerable ---

def test_admin_sees_only_local_leaderboard_players(dsn):
    # Org A admin sees P1 (on a LOC_A leaderboard) and NOT P2 (only LOC_B).
    assert _count_as(dsn, "players", role="authenticated", sub=USER_A) == 1
    assert _count_as(dsn, "players", role="authenticated", sub=USER_A,
                     where=f"where id='{P2}'") == 0


def test_no_operator_can_enumerate_global_players(dsn):
    # Org B admin sees only its own (P2), never P1 — no global enumeration.
    assert _count_as(dsn, "players", role="authenticated", sub=USER_B) == 1
    assert _count_as(dsn, "players", role="authenticated", sub=USER_B,
                     where=f"where id='{P1}'") == 0


def test_super_admin_sees_all_players(dsn):
    assert _count_as(dsn, "players", role="authenticated", sub=USER_SUPER) == 2


# --- player_secrets: service_role ONLY ---

def test_player_secrets_hidden_from_authenticated(dsn):
    # Even for their OWN location's player, contact material is invisible.
    assert _count_as(dsn, "player_secrets", role="authenticated", sub=USER_A) == 0
    assert _count_as(dsn, "player_secrets", role="authenticated", sub=USER_SUPER) == 0


def test_player_secrets_hidden_from_anon(dsn):
    assert _count_as(dsn, "player_secrets", role="anon",
                     claims=_loc_claims(LOC_A)) == 0


def test_player_secrets_readable_by_service_role(dsn):
    # The Flask box (service_role, bypassrls) is the only reader.
    assert _count_as(dsn, "player_secrets", role="service_role") == 2


# --- player_leaderboards: location-scoped ---

def test_player_leaderboards_scoped_to_location(dsn):
    assert _count_as(dsn, "player_leaderboards", role="authenticated",
                     sub=USER_A) == 1
    assert _count_as(dsn, "player_leaderboards", role="authenticated",
                     sub=USER_A, where=f"where location_id='{LOC_B}'") == 0


# --- anon TV: scoped by its signed location token, fail-closed ---

def test_anon_with_location_token_sees_local_only(dsn):
    # Sees P1 + the LOC_A leaderboard...
    assert _count_as(dsn, "players", role="anon",
                     claims=_loc_claims(LOC_A)) == 1
    assert _count_as(dsn, "player_leaderboards", role="anon",
                     claims=_loc_claims(LOC_A)) == 1
    # ...and never the other venue's.
    assert _count_as(dsn, "players", role="anon",
                     claims=_loc_claims(LOC_A), where=f"where id='{P2}'") == 0
    assert _count_as(dsn, "player_leaderboards", role="anon",
                     claims=_loc_claims(LOC_A),
                     where=f"where location_id='{LOC_B}'") == 0


def test_anon_without_token_sees_nothing(dsn):
    # No location claim => fail-closed.
    assert _count_as(dsn, "players", role="anon") == 0
    assert _count_as(dsn, "player_leaderboards", role="anon") == 0


# --- write denial: clients never write identity rows ---

def test_authenticated_cannot_write_players(dsn):
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("set role authenticated")
            cur.execute("select set_config('request.jwt.claim.sub', %s, true)",
                        (USER_A,))
            with pytest.raises(psycopg.errors.Error):
                cur.execute("insert into players(display_name) values ('hax')")
        conn.rollback()


def test_anon_cannot_write_player_secrets(dsn):
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("set role anon")
            cur.execute("select set_config('request.jwt.claims', %s, true)",
                        (_loc_claims(LOC_A),))
            with pytest.raises(psycopg.errors.Error):
                cur.execute(
                    "insert into player_secrets(player_id,token_hash) "
                    f"values ('{P1}','sneaky')"
                )
        conn.rollback()
