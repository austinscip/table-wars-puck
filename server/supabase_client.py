"""
SupabaseWriter — direct Postgres connection to Supabase using
DATABASE_URL. Connects as the `postgres` role, which bypasses RLS the
same way the service_role JWT does on PostgREST.

Used by the runtime MatchManager and any other server-side write path
that should not be subject to RLS (puck telemetry, firmware manifest
updates, etc.).

The class routes every write through `_connection()`. By default that
opens a fresh psycopg connection per call (simple, no shared state). In
production, build the writer with `SupabaseWriter.with_pool(...)` so calls
borrow from a `psycopg_pool.ConnectionPool` instead of paying TCP+TLS
setup on every score write. The method bodies are identical either way —
only where the connection comes from changes.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Iterator, Optional

import psycopg
from psycopg.rows import dict_row

from datetime import datetime

try:  # psycopg_pool is optional — the direct-connect path needs only psycopg.
    from psycopg_pool import ConnectionPool
except ImportError:  # pragma: no cover - exercised only where the lib is absent
    ConnectionPool = None  # type: ignore[assignment, misc]


class SupabaseWriter:
    def __init__(
        self,
        dsn: Optional[str] = None,
        pool: Optional["ConnectionPool"] = None,
    ) -> None:
        if pool is not None:
            # Pooled mode: the pool owns the DSN + connection config.
            self._pool = pool
            self.dsn: Optional[str] = None
            return
        dsn = dsn or os.environ.get("DATABASE_URL")
        if not dsn:
            raise RuntimeError(
                "DATABASE_URL is not set. Source ~/tablewars/.env first."
            )
        self.dsn = dsn
        self._pool = None

    @classmethod
    def with_pool(
        cls,
        dsn: Optional[str] = None,
        *,
        min_size: int = 1,
        max_size: int = 8,
    ) -> "SupabaseWriter":
        """Build a writer backed by a connection pool. Falls back to the
        poolless writer when psycopg_pool isn't installed, so a minimal
        deploy still works. The pool fills lazily in the background, so
        construction doesn't block on (or fail because of) the database
        being momentarily unreachable."""
        if ConnectionPool is None:
            return cls(dsn=dsn)
        dsn = dsn or os.environ.get("DATABASE_URL")
        if not dsn:
            raise RuntimeError(
                "DATABASE_URL is not set. Source ~/tablewars/.env first."
            )
        pool = ConnectionPool(
            dsn,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
            open=True,
        )
        return cls(pool=pool)

    @contextmanager
    def _connection(self) -> Iterator["psycopg.Connection"]:
        """Yield a connection — borrowed from the pool when one is
        configured, otherwise freshly opened. Either way the context
        commits on success and rolls back on exception, so callers wrap
        multi-statement work in `with conn.transaction():` as before."""
        if self._pool is not None:
            with self._pool.connection() as conn:
                yield conn
        else:
            with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
                yield conn

    def close(self) -> None:
        """Close the pool if we own one. No-op in direct-connect mode."""
        if self._pool is not None:
            self._pool.close()

    # === Matches ===

    def create_match(
        self,
        location_id: str,
        game_slug: str,
        table_number: int,
        pucks: list[tuple[str, str, Optional[str]]],
        snapshot: dict,
    ) -> tuple[str, list[str]]:
        """Create a match, its match_pucks rows, and the seed snapshot in a
        SINGLE transaction. Either the whole match exists or none of it
        does — a crash mid-create can't leave an orphan matches row with
        no pucks, or pucks with no snapshot for the TV to paint.

        pucks is a list of (puck_uuid, role, player_name) in seating
        order. Returns (match_id, match_puck_ids) where match_puck_ids is
        in the same order as pucks.
        """
        with self._connection() as conn:
            with conn.transaction():
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
                    match_id = cur.fetchone()["id"]

                    match_puck_ids: list[str] = []
                    for puck_uuid, role, player_name in pucks:
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
                        match_puck_ids.append(cur.fetchone()["id"])

                    cur.execute(
                        "update matches set snapshot = %s::jsonb "
                        "where id = %s",
                        (json.dumps(snapshot), match_id),
                    )
        return match_id, match_puck_ids

    def insert_match(
        self, location_id: str, game_slug: str, table_number: int
    ) -> str:
        with self._connection() as conn:
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
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "update matches "
                    "set status = 'finished', ended_at = %s "
                    "where id = %s",
                    (ended_at, match_id),
                )

    def update_match_abandoned(
        self, match_id: str, ended_at: datetime
    ) -> None:
        """Mark a match abandoned — everyone walked away before it
        finished. Distinct from 'finished' so analytics can tell a real
        result from a dead table. No final scores are written (there's no
        meaningful result). Guarded to only touch a still-active row so a
        late sweep can't stomp a match that finished in the meantime."""
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "update matches "
                    "set status = 'abandoned', ended_at = %s "
                    "where id = %s and status = 'active'",
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
        with self._connection() as conn:
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
        with self._connection() as conn:
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
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "update matches set snapshot = %s::jsonb where id = %s",
                    (json.dumps(snapshot), match_id),
                )

    # === Lobbies (Realtime-published pairing state) ===

    def upsert_lobby(
        self, location_id: str, table_number: int, snapshot: dict
    ) -> None:
        """Publish a table's lobby snapshot so the TV's Realtime
        subscription wakes. One row per (location_id, table_number)."""
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "insert into lobbies (location_id, table_number, snapshot, updated_at) "
                    "values (%s, %s, %s::jsonb, now()) "
                    "on conflict (location_id, table_number) do update "
                    "  set snapshot = excluded.snapshot, updated_at = now()",
                    (location_id, table_number, json.dumps(snapshot)),
                )

    def delete_lobby(self, location_id: str, table_number: int) -> None:
        """Remove a table's lobby row when it's cancelled/expired."""
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "delete from lobbies where location_id = %s and table_number = %s",
                    (location_id, table_number),
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
        with self._connection() as conn:
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
