"""
SupabaseWriter — direct Postgres connection to Supabase using
DATABASE_URL. Connects as the `postgres` role, which bypasses RLS the
same way the service_role JWT does on PostgREST.

Used by the runtime MatchManager and any other server-side write path
that should not be subject to RLS (puck telemetry, firmware manifest
updates, etc.).

The class is a thin wrapper around psycopg connections. Every method
opens a fresh connection from the pool, runs its SQL, and closes — no
sessions are held across requests. If write volume grows, swap to a
psycopg_pool.ConnectionPool.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

import psycopg
from psycopg.rows import dict_row


class SupabaseWriter:
    def __init__(self, dsn: Optional[str] = None) -> None:
        dsn = dsn or os.environ.get("DATABASE_URL")
        if not dsn:
            raise RuntimeError(
                "DATABASE_URL is not set. Source ~/tablewars/.env first."
            )
        self.dsn = dsn

    # === Matches ===

    def insert_match(
        self, location_id: str, game_slug: str, table_number: int
    ) -> str:
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select id from games where slug = %s", (game_slug,)
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Unknown game slug: {game_slug!r}")
                game_id = row["id"]
                cur.execute(
                    "insert into matches "
                    "(location_id, game_id, table_number, status) "
                    "values (%s, %s, %s, 'active') "
                    "returning id",
                    (location_id, game_id, table_number),
                )
                return cur.fetchone()["id"]

    def update_match_finished(
        self, match_id: str, ended_at: datetime
    ) -> None:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "update matches "
                    "set status = 'finished', ended_at = %s "
                    "where id = %s",
                    (ended_at, match_id),
                )

    # === Match pucks ===

    def upsert_match_puck(
        self,
        match_id: str,
        puck_uuid: str,
        role: str,
        player_name: Optional[str],
    ) -> str:
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "insert into match_pucks "
                    "(match_id, puck_id, role, player_name) "
                    "values (%s, %s, %s, %s) "
                    "on conflict (match_id, puck_id) do update "
                    "  set role = excluded.role, "
                    "      player_name = excluded.player_name "
                    "returning id",
                    (match_id, puck_uuid, role, player_name),
                )
                return cur.fetchone()["id"]

    # === Scores ===

    def insert_score(
        self,
        match_id: str,
        match_puck_id: str,
        round_number: int,
        score_delta: int,
        score_total: int,
        event_type: str,
    ) -> None:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "insert into scores "
                    "(match_id, match_puck_id, round_number, "
                    " score_delta, score_total, event_type) "
                    "values (%s, %s, %s, %s, %s, %s)",
                    (
                        match_id,
                        match_puck_id,
                        round_number,
                        score_delta,
                        score_total,
                        event_type,
                    ),
                )
