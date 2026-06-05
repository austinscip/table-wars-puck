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

    def update_match_snapshot(self, match_id: str, snapshot: dict) -> None:
        """Write the current game state snapshot to matches.snapshot so
        the TV Realtime subscription wakes up. Called from MatchManager
        after every input or tick that changes visible state."""
        import json

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "update matches set snapshot = %s::jsonb where id = %s",
                    (json.dumps(snapshot), match_id),
                )

    # === Pucks ===

    def ensure_puck(self, puck_index: int, location_id: str) -> str:
        """Look up the UUID for a (location_id, puck_index) pair. If no
        puck has been provisioned yet at this index, auto-create one
        plus its puck_assignments row. Returns the pucks.id UUID.

        Auto-provisioning keeps the dev / pilot flow simple — no manual
        seeding needed before first pair. Production would gate this
        behind explicit fleet management (admin assigns serial -> index
        before the puck ships).
        """
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select p.id from pucks p "
                    "join puck_assignments pa on pa.puck_id = p.id "
                    "where pa.location_id = %s "
                    "  and pa.removed_at is null "
                    "  and p.puck_index = %s",
                    (location_id, puck_index),
                )
                row = cur.fetchone()
                if row is not None:
                    return row["id"]

                # Auto-provision. Serial number is a synthetic
                # location-scoped slug — replaceable later when the real
                # hardware serial is known.
                serial_no = f"auto-{location_id[:8]}-{puck_index}"
                cur.execute(
                    "insert into pucks "
                    "(serial_no, hw_revision, puck_index, is_online) "
                    "values (%s, 'RevB', %s, false) "
                    "returning id",
                    (serial_no, puck_index),
                )
                puck_uuid = cur.fetchone()["id"]
                cur.execute(
                    "insert into puck_assignments "
                    "(puck_id, location_id) "
                    "values (%s, %s)",
                    (puck_uuid, location_id),
                )
                return puck_uuid
