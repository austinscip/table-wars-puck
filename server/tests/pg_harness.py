"""
Shared real-Postgres bootstrap for the gold-standard DB tests.

Spins up a throwaway Postgres cluster, loads a minimal Supabase-auth shim,
applies the actual migrations in order, and grants the Supabase roles — so a
test can exercise real RLS policies, triggers, and constraints against the
database itself rather than re-implementing them. Used by both the
adversarial RLS suite (test_rls.py) and the player-identity DB tests
(test_player_identity.py).

Skips cleanly (via the helpers returning None) when local Postgres binaries
aren't present; callers pytest.skip on that.
"""

from __future__ import annotations

import contextlib
import glob
import os
import shutil
import subprocess
import tempfile
import time
from typing import Iterator, Optional

import psycopg


_MIGRATIONS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "supabase", "migrations")
)

_PG_BIN_DIRS = [
    "/opt/homebrew/opt/postgresql@14/bin",
    "/usr/local/opt/postgresql@14/bin",
    "/opt/homebrew/bin",
    "/usr/local/bin",
]
# Debian/Ubuntu (CI) install Postgres binaries here, not on PATH.
_PG_BIN_GLOBS = ["/usr/lib/postgresql/*/bin", "/usr/pgsql-*/bin"]


def find_pg_binary(binary: str) -> Optional[str]:
    for d in _PG_BIN_DIRS:
        cand = os.path.join(d, binary)
        if os.path.exists(cand):
            return cand
    for pattern in _PG_BIN_GLOBS:
        for d in sorted(glob.glob(pattern), reverse=True):
            cand = os.path.join(d, binary)
            if os.path.exists(cand):
                return cand
    return shutil.which(binary)


# Just enough Supabase auth surface for the real migrations + RLS to run.
SHIM_SQL = """
create schema if not exists auth;
create table if not exists auth.users (
  id uuid primary key default gen_random_uuid(),
  email text,
  raw_user_meta_data jsonb default '{}'::jsonb
);
create or replace function auth.uid() returns uuid language sql stable as $$
  select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;
create or replace function auth.jwt() returns jsonb language sql stable as $$
  select coalesce(nullif(current_setting('request.jwt.claims', true), ''), '{}')::jsonb
$$;
do $$ begin
  if not exists (select from pg_roles where rolname='anon') then create role anon nologin; end if;
  if not exists (select from pg_roles where rolname='authenticated') then create role authenticated nologin; end if;
  if not exists (select from pg_roles where rolname='service_role') then create role service_role nologin bypassrls; end if;
end $$;
grant usage on schema public, auth to anon, authenticated, service_role;
"""

GRANTS_SQL = """
grant select, insert, update, delete on all tables in schema public to authenticated, service_role;
grant select on all tables in schema public to anon;
"""


@contextlib.contextmanager
def bootstrap_migrated_db(
    extra_sql: str = "", port: str = "5601"
) -> Iterator[str]:
    """Yield a DSN to a freshly-migrated throwaway DB, then tear it down.

    extra_sql runs once after migrations + grants (e.g. a test's seed).
    Raises RuntimeError if Postgres binaries are missing — callers check
    pg_available() / pytest.skip first.
    """
    initdb, pg_ctl = find_pg_binary("initdb"), find_pg_binary("pg_ctl")
    if not initdb or not pg_ctl:
        raise RuntimeError("local Postgres (initdb/pg_ctl) not available")

    root = tempfile.mkdtemp(prefix="tw_pg_test_")
    data = os.path.join(root, "data")
    sock = os.path.join(root, "sock")
    os.makedirs(sock)
    try:
        subprocess.run(
            [initdb, "-D", data, "-U", "postgres", "--auth=trust"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [pg_ctl, "-D", data, "-o",
             f"-k {sock} -p {port} -c listen_addresses=''",
             "-l", os.path.join(root, "log"), "start"],
            check=True,
            capture_output=True,
        )

        admin_dsn = f"host={sock} port={port} user=postgres dbname=postgres"
        deadline = time.time() + 15
        while True:
            try:
                with psycopg.connect(admin_dsn, autocommit=True) as c:
                    c.execute("select 1")
                break
            except Exception:
                if time.time() > deadline:
                    raise
                time.sleep(0.25)

        with psycopg.connect(admin_dsn, autocommit=True) as c:
            c.execute("create database tw")

        db_dsn = f"host={sock} port={port} user=postgres dbname=tw"
        migrations = sorted(
            os.path.join(_MIGRATIONS_DIR, f)
            for f in os.listdir(_MIGRATIONS_DIR)
            if f.endswith(".sql")
        )
        with psycopg.connect(db_dsn, autocommit=True) as c:
            c.execute(SHIM_SQL)
            for path in migrations:
                with open(path) as fh:
                    c.execute(fh.read())
            c.execute(GRANTS_SQL)
            if extra_sql:
                c.execute(extra_sql)

        yield db_dsn
    finally:
        subprocess.run([pg_ctl, "-D", data, "stop", "-m", "immediate"],
                       capture_output=True)
        shutil.rmtree(root, ignore_errors=True)


def pg_available() -> bool:
    return bool(find_pg_binary("initdb") and find_pg_binary("pg_ctl"))
