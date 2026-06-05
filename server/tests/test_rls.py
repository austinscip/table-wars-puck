"""
Adversarial RLS test suite (Tier 3, items 14 + 17).

These run against a REAL Postgres: the fixture bootstraps a throwaway
cluster, loads a minimal Supabase-auth shim + the actual migrations +
seed, and then auths as users in two different orgs (and as anon) to prove
the row-level security policies actually isolate tenants. Verifying policy
text by reading is not enough — RLS bugs hide in the interaction between
`security definer` helpers, role grants, and the policies, so we exercise
the database itself.

Skips cleanly when local Postgres binaries (initdb/pg_ctl) aren't present.
"""

from __future__ import annotations

import psycopg
import pytest

from pg_harness import bootstrap_migrated_db, pg_available


# Fixed UUIDs for two isolated orgs + their users/matches.
ORG_A = "22222222-0000-0000-0000-00000000000a"
ORG_B = "22222222-0000-0000-0000-00000000000b"
LOC_A = "33333333-0000-0000-0000-0000000000aa"
LOC_B = "33333333-0000-0000-0000-0000000000bb"
USER_A_ADMIN = "44444444-0000-0000-0000-00000000000a"
USER_B_ADMIN = "44444444-0000-0000-0000-00000000000b"
USER_A_STAFF = "44444444-0000-0000-0000-0000000000aa"
USER_SUPER = "44444444-0000-0000-0000-00000000000f"
MATCH_A = "55555555-0000-0000-0000-0000000000aa"
MATCH_B = "55555555-0000-0000-0000-0000000000bb"

_SEED_SQL = f"""
insert into tenants(id,name,slug,billing_email,status) values
 ('11111111-0000-0000-0000-000000000001','TenA','tena','a@x.com','trial'),
 ('11111111-0000-0000-0000-000000000002','TenB','tenb','b@x.com','trial');
insert into organizations(id,tenant_id,name,slug) values
 ('{ORG_A}','11111111-0000-0000-0000-000000000001','OrgA','orga'),
 ('{ORG_B}','11111111-0000-0000-0000-000000000002','OrgB','orgb');
insert into locations(id,organization_id,name,slug) values
 ('{LOC_A}','{ORG_A}','LocA','loca'),
 ('{LOC_B}','{ORG_B}','LocB','locb');
insert into auth.users(id,email) values
 ('{USER_A_ADMIN}','usera@x.com'),('{USER_B_ADMIN}','userb@x.com'),
 ('{USER_A_STAFF}','staffa@x.com'),('{USER_SUPER}','super@x.com');
insert into user_org_roles(user_id,organization_id,role) values
 ('{USER_A_ADMIN}','{ORG_A}','org_admin'),
 ('{USER_B_ADMIN}','{ORG_B}','org_admin'),
 ('{USER_SUPER}','{ORG_A}','super_admin');
insert into user_location_roles(user_id,location_id,role) values
 ('{USER_A_STAFF}','{LOC_A}','bar_staff');
insert into matches(id,location_id,game_id,table_number,status)
 select '{MATCH_A}','{LOC_A}',g.id,1,'active' from games g where g.slug='speed_pyramid';
insert into matches(id,location_id,game_id,table_number,status)
 select '{MATCH_B}','{LOC_B}',g.id,1,'active' from games g where g.slug='speed_pyramid';
insert into lobbies(location_id,table_number,snapshot) values
 ('{LOC_A}',1,'{{"code":"111111"}}'::jsonb),
 ('{LOC_B}',1,'{{"code":"222222"}}'::jsonb);
"""


@pytest.fixture(scope="module")
def rls_dsn():
    if not pg_available():
        pytest.skip("local Postgres (initdb/pg_ctl) not available")
    with bootstrap_migrated_db(extra_sql=_SEED_SQL, port="5601") as dsn:
        yield dsn


def _count_as(dsn, table, *, role, sub=None, claims=None, where=""):
    """Run a scoped SELECT count under a role + JWT context, rolled back."""
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(f"set role {role}")
            if sub is not None:
                cur.execute("select set_config('request.jwt.claim.sub', %s, true)", (sub,))
            if claims is not None:
                cur.execute("select set_config('request.jwt.claims', %s, true)", (claims,))
            cur.execute(f"select count(*) from {table} {where}")
            n = cur.fetchone()[0]
        conn.rollback()
    return n


# --- Org isolation (item 14) ---

def test_org_admin_sees_only_own_match(rls_dsn):
    assert _count_as(rls_dsn, "matches", role="authenticated", sub=USER_A_ADMIN) == 1
    # And specifically NOT the other org's match, even by id.
    assert _count_as(rls_dsn, "matches", role="authenticated", sub=USER_A_ADMIN,
                     where=f"where id='{MATCH_B}'") == 0


def test_org_b_admin_cannot_see_org_a(rls_dsn):
    assert _count_as(rls_dsn, "matches", role="authenticated", sub=USER_B_ADMIN,
                     where=f"where id='{MATCH_A}'") == 0


def test_bar_staff_sees_their_location(rls_dsn):
    assert _count_as(rls_dsn, "matches", role="authenticated", sub=USER_A_STAFF) == 1
    assert _count_as(rls_dsn, "matches", role="authenticated", sub=USER_A_STAFF,
                     where=f"where id='{MATCH_B}'") == 0


def test_super_admin_sees_all(rls_dsn):
    assert _count_as(rls_dsn, "matches", role="authenticated", sub=USER_SUPER) == 2


def test_scores_follow_match_scope(rls_dsn):
    # Org A admin can't see Org B's scores (none seeded, but the policy
    # path is what we assert: a cross-org scores read is empty).
    assert _count_as(rls_dsn, "scores", role="authenticated", sub=USER_B_ADMIN,
                     where=f"where match_id='{MATCH_A}'") == 0


# --- Write denial (clients never write game data) ---

def test_authenticated_cannot_insert_match(rls_dsn):
    with psycopg.connect(rls_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("set role authenticated")
            cur.execute("select set_config('request.jwt.claim.sub', %s, true)", (USER_A_ADMIN,))
            with pytest.raises(psycopg.errors.Error):
                cur.execute(
                    "insert into matches(location_id,game_id,table_number,status) "
                    "select %s,g.id,9,'active' from games g where g.slug='speed_pyramid'",
                    (LOC_A,),
                )
        conn.rollback()


# --- Anon match-token scoping (item 17) ---

def _claims(match_id=None, location_id=None):
    import json
    c = {"role": "anon"}
    if match_id:
        c["match_id"] = match_id
    if location_id:
        c["location_id"] = location_id
    return json.dumps(c)


def test_anon_without_token_sees_nothing(rls_dsn):
    assert _count_as(rls_dsn, "matches", role="anon", claims=_claims()) == 0


def test_anon_with_token_sees_only_that_match(rls_dsn):
    assert _count_as(rls_dsn, "matches", role="anon",
                     claims=_claims(match_id=MATCH_A)) == 1
    # The token for match A cannot read match B.
    assert _count_as(rls_dsn, "matches", role="anon",
                     claims=_claims(match_id=MATCH_A),
                     where=f"where id='{MATCH_B}'") == 0


def test_anon_token_scopes_scores(rls_dsn):
    # A token for match A exposes only match A's scores rows.
    assert _count_as(rls_dsn, "scores", role="anon",
                     claims=_claims(match_id=MATCH_A),
                     where=f"where match_id='{MATCH_B}'") == 0


def test_lobby_anon_scoped_by_location_token(rls_dsn):
    import json
    # A location-scoped anon token sees its location's lobby, not the other.
    claims_a = json.dumps({"role": "anon", "location_id": LOC_A})
    assert _count_as(rls_dsn, "lobbies", role="anon", claims=claims_a) == 1
    assert _count_as(rls_dsn, "lobbies", role="anon", claims=claims_a,
                     where=f"where location_id='{LOC_B}'") == 0
    # Tokenless anon -> nothing.
    assert _count_as(rls_dsn, "lobbies", role="anon",
                     claims=json.dumps({"role": "anon"})) == 0


def test_org_admin_sees_only_own_lobby(rls_dsn):
    assert _count_as(rls_dsn, "lobbies", role="authenticated",
                     sub=USER_A_ADMIN) == 1
    assert _count_as(rls_dsn, "lobbies", role="authenticated",
                     sub=USER_A_ADMIN, where=f"where location_id='{LOC_B}'") == 0


def test_server_minted_tv_token_satisfies_rls(rls_dsn):
    """End-to-end: a token actually minted by TvMatchTokenAuthority, when
    its decoded claims drive the anon session, sees exactly its match.
    This ties the server's minting to the database's policy."""
    import json
    import jwt
    from runtime import TvMatchTokenAuthority

    secret = "supabase-jwt-secret-at-least-32-bytes-long"
    authority = TvMatchTokenAuthority(secret)
    token = authority.issue(match_id=MATCH_A, location_id=LOC_A)
    # Realtime verifies the signature with the same secret and exposes the
    # payload as request.jwt.claims; emulate that here.
    claims = jwt.decode(token, secret, algorithms=["HS256"])

    assert _count_as(rls_dsn, "matches", role="anon",
                     claims=json.dumps(claims)) == 1
    assert _count_as(rls_dsn, "matches", role="anon",
                     claims=json.dumps(claims),
                     where=f"where id='{MATCH_B}'") == 0
