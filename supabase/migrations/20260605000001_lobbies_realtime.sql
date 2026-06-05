-- ============================================================================
-- Lobby state as a Realtime-subscribable table.
-- ============================================================================
--
-- The TV currently POLLS /api/runtime/pair/lobby-state at 1 Hz. That's a
-- busy-wait that also can't work across multiple Flask workers (the lobby
-- lives in one worker's PairingManager memory). Mirroring lobby state into
-- a table the TV subscribes to via Realtime removes the poll AND makes the
-- lobby durable + shareable: PairingManager writes here on every mutation,
-- every TV at the table sees the change pushed.
--
-- One row per (location_id, table_number). `snapshot` holds the full
-- PairingManager.lobby_snapshot() payload (code, players, host, etc).

create table if not exists lobbies (
  location_id  uuid not null references locations(id) on delete cascade,
  table_number smallint not null,
  snapshot     jsonb not null default '{}'::jsonb,
  updated_at   timestamptz not null default now(),
  primary key (location_id, table_number)
);

create index if not exists idx_lobbies_location on lobbies(location_id);

alter table lobbies enable row level security;

-- Location-scoped read for staff/admins (same model as matches).
create policy lobbies_select on lobbies for select using (
  is_super_admin()
  or location_id in (select * from current_user_location_ids())
);

-- Anon (the TV) reads its location's lobbies when its token carries the
-- matching location_id claim — the same signed-token approach as the anon
-- match-token policies. A tokenless anon sees nothing (fail-closed).
create policy lobbies_anon_by_token on lobbies for select to anon using (
  location_id = nullif(auth.jwt() ->> 'location_id', '')::uuid
);

-- Writes are server-only (postgres/service_role bypasses RLS); no client
-- write policy, matching matches/scores.
