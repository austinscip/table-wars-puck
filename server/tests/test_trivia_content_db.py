"""
Real-Postgres tests for trivia content (ADR 0008): the writer reader, the
content-version fingerprint, and the RLS (public reads active questions;
only super_admin / service_role writes).
"""

from __future__ import annotations

import psycopg
import pytest

from pg_harness import bootstrap_migrated_db, pg_available


ORG_A = "a2000000-0000-0000-0000-00000000000a"
USER_SUPER = "a4000000-0000-0000-0000-00000000000f"

_SEED = f"""
insert into tenants(id,name,slug,status) values
 ('a1000000-0000-0000-0000-000000000001','T','t','trial');
insert into organizations(id,tenant_id,name,slug) values
 ('{ORG_A}','a1000000-0000-0000-0000-000000000001','O','o');
insert into auth.users(id,email) values ('{USER_SUPER}','s@x.com');
insert into user_org_roles(user_id,organization_id,role) values
 ('{USER_SUPER}','{ORG_A}','super_admin');
"""


@pytest.fixture(scope="module")
def dsn():
    if not pg_available():
        pytest.skip("local Postgres (initdb/pg_ctl) not available")
    with bootstrap_migrated_db(extra_sql=_SEED, port="5606") as d:
        yield d


def _writer(dsn):
    from supabase_client import SupabaseWriter

    return SupabaseWriter(dsn=dsn)


def test_reader_returns_seeded_bank_in_question_shape(dsn):
    w = _writer(dsn)
    bank = w.get_active_trivia_questions()
    assert len(bank) == 3  # the migration's seed
    row = bank[0]
    # Shape the runtime's Question mapper expects (category aliased).
    for key in (
        "id", "question_text", "answer_a", "answer_b", "answer_c",
        "answer_d", "correct_answer", "category_name", "time_limit",
    ):
        assert key in row


def test_content_version_changes_on_edit(dsn):
    w = _writer(dsn)
    before = w.trivia_content_version()
    assert before and before != "0"
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into trivia_questions(question_text,answer_a,answer_b,"
                "answer_c,answer_d,correct_answer,category) "
                "values ('New?','a','b','c','d','A','Test')"
            )
    after = w.trivia_content_version()
    assert after != before  # the box would now know to refresh


def _count_as(dsn, *, role, sub=None, where=""):
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(f"set role {role}")
            if sub is not None:
                cur.execute(
                    "select set_config('request.jwt.claim.sub', %s, true)", (sub,)
                )
            cur.execute(f"select count(*) from trivia_questions {where}")
            n = cur.fetchone()[0]
        conn.rollback()
    return n


def test_anon_reads_active_only(dsn):
    # Insert one inactive question; anon must not see it.
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into trivia_questions(question_text,answer_a,answer_b,"
                "answer_c,answer_d,correct_answer,is_active) "
                "values ('Hidden?','a','b','c','d','A',false)"
            )
    active = _count_as(dsn, role="service_role",
                       where="where is_active")
    anon_visible = _count_as(dsn, role="anon")
    assert anon_visible == active  # anon sees exactly the active set
    assert _count_as(dsn, role="anon", where="where is_active = false") == 0


def test_super_admin_sees_inactive_too(dsn):
    total = _count_as(dsn, role="service_role")
    admin_visible = _count_as(dsn, role="authenticated", sub=USER_SUPER)
    assert admin_visible == total  # super_admin sees active + inactive


def test_anon_cannot_write_questions(dsn):
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("set role anon")
            with pytest.raises(psycopg.errors.Error):
                cur.execute(
                    "insert into trivia_questions(question_text,answer_a,"
                    "answer_b,answer_c,answer_d,correct_answer) "
                    "values ('Hax?','a','b','c','d','A')"
                )
        conn.rollback()
