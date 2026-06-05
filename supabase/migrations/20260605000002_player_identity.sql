-- ============================================================================
-- Persistent player identity (ADR 0005)
--
-- A Player is a GLOBAL, tenant-independent human identity — one row across
-- every venue/operator, unlike every other gameplay table (which is
-- location-scoped). Identity is an opaque QR-delivered token (stored only as
-- a hash) with optional phone recovery. Patrons NEVER enter auth.users
-- (that's staff). Identity is a purely additive overlay on the existing
-- puck-anchored model: sign-in is optional, and an anonymous match attaches
-- no Player.
--
-- Public handle is split from private contact:
--   players          -> id + display_name (a public handle) + created_at.
--                       Readable (display_name only) for leaderboard display.
--   player_secrets   -> token hash + optional phone hash. SERVICE-ROLE ONLY
--                       (RLS enabled, no policy => deny-all to anon/auth;
--                       only the Flask box, as service_role, touches it).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Identity tables
-- ----------------------------------------------------------------------------

create table players (
  id           uuid primary key default gen_random_uuid(),
  display_name text,
  created_at   timestamptz not null default now()
);

-- Contact / auth material, isolated so a leak of the public-handle table
-- never exposes it. One row per player.
create table player_secrets (
  player_id  uuid primary key references players(id) on delete cascade,
  -- sha256 hex of the opaque player token the patron's device holds. We
  -- never store the raw token, so a DB leak can't impersonate a player.
  token_hash text not null unique,
  -- sha256 hex of an optional phone number for cross-device recovery.
  phone_hash text,
  created_at timestamptz not null default now()
);
create index idx_player_secrets_phone on player_secrets(phone_hash)
  where phone_hash is not null;

-- ----------------------------------------------------------------------------
-- Link the Match Participant to a Player (optional)
-- ----------------------------------------------------------------------------

-- A deleted Player de-attributes from history (SET NULL) but the match and
-- its scores survive — leaderboard *truth* is never rewritten. Anonymous
-- participants leave this null (the common case).
alter table match_pucks
  add column player_id uuid references players(id) on delete set null;
create index idx_mp_player on match_pucks(player_id) where player_id is not null;

-- ----------------------------------------------------------------------------
-- Player leaderboards (a NEW table; the puck-keyed `leaderboards` is untouched)
--
-- Keyed by (player_id, game_id, location_id, period, period_start): location
-- in the key preserves per-bar ranking ("#3 this week at this bar") while a
-- profile can sum across locations for a global view. Higher-is-better within
-- a game (ADR 0003) carries over, so GREATEST upserts stay direction-free.
-- ----------------------------------------------------------------------------

create table player_leaderboards (
  id            uuid primary key default gen_random_uuid(),
  player_id     uuid not null references players(id) on delete cascade,
  game_id       uuid not null references games(id) on delete cascade,
  location_id   uuid not null references locations(id) on delete cascade,
  period        leaderboard_period not null,
  period_start  date not null,
  high_score    integer not null default 0,
  total_matches integer not null default 0,
  updated_at    timestamptz not null default now(),
  unique (player_id, game_id, location_id, period, period_start)
);
-- Ranking query: "#N this <period> at this location for this game".
create index idx_pl_location_game_period
  on player_leaderboards(location_id, game_id, period, high_score desc);
-- Profile query: a player's standings across everywhere.
create index idx_pl_player on player_leaderboards(player_id);

-- ----------------------------------------------------------------------------
-- Extend the final-score trigger to ALSO update player_leaderboards when the
-- scoring Match Participant has a Player attached. The puck-keyed upsert is
-- unchanged; the player upsert is purely additive and only fires when
-- player_id is non-null.
-- ----------------------------------------------------------------------------

create or replace function update_leaderboards_on_final_score()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_location_id uuid;
  v_game_id     uuid;
  v_puck_id     uuid;
  v_player_id   uuid;
  v_today       date := (now() at time zone 'UTC')::date;
  v_week        date := date_trunc('week',  now() at time zone 'UTC')::date;
  v_month       date := date_trunc('month', now() at time zone 'UTC')::date;
  v_all_time    date := '1970-01-01'::date;
begin
  if new.event_type <> 'final' then
    return new;
  end if;

  select m.location_id, m.game_id, mp.puck_id, mp.player_id
    into v_location_id, v_game_id, v_puck_id, v_player_id
  from matches m
    join match_pucks mp on mp.id = new.match_puck_id
  where m.id = new.match_id;

  -- Puck-keyed leaderboard (hardware analytics + anonymous fallback) — as before.
  insert into leaderboards
    (location_id, game_id, puck_id, period, period_start, high_score, total_matches, updated_at)
  values
    (v_location_id, v_game_id, v_puck_id, 'day',      v_today,    new.score_total, 1, now()),
    (v_location_id, v_game_id, v_puck_id, 'week',     v_week,     new.score_total, 1, now()),
    (v_location_id, v_game_id, v_puck_id, 'month',    v_month,    new.score_total, 1, now()),
    (v_location_id, v_game_id, v_puck_id, 'all_time', v_all_time, new.score_total, 1, now())
  on conflict (location_id, game_id, puck_id, period, period_start) do update
    set high_score    = greatest(leaderboards.high_score, excluded.high_score),
        total_matches = leaderboards.total_matches + 1,
        updated_at    = now();

  -- Player-keyed leaderboard — ONLY when a Player is attached to this Participant.
  if v_player_id is not null then
    insert into player_leaderboards
      (player_id, game_id, location_id, period, period_start, high_score, total_matches, updated_at)
    values
      (v_player_id, v_game_id, v_location_id, 'day',      v_today,    new.score_total, 1, now()),
      (v_player_id, v_game_id, v_location_id, 'week',     v_week,     new.score_total, 1, now()),
      (v_player_id, v_game_id, v_location_id, 'month',    v_month,    new.score_total, 1, now()),
      (v_player_id, v_game_id, v_location_id, 'all_time', v_all_time, new.score_total, 1, now())
    on conflict (player_id, game_id, location_id, period, period_start) do update
      set high_score    = greatest(player_leaderboards.high_score, excluded.high_score),
          total_matches = player_leaderboards.total_matches + 1,
          updated_at    = now();
  end if;

  return new;
end;
$$;

-- ----------------------------------------------------------------------------
-- Row-level security
-- ----------------------------------------------------------------------------

alter table players             enable row level security;
alter table player_secrets      enable row level security;
alter table player_leaderboards enable row level security;

-- players: a public handle, but NOT enumerable. Visible only for players who
-- appear on a leaderboard at a location the reader can see — so no operator
-- (and no anon TV) can list the global player base. Writes are service_role
-- only (no insert/update policy; the Flask box bypasses RLS).
create policy players_select on players for select using (
  is_super_admin()
  or id in (
    select player_id from player_leaderboards
    where location_id in (select * from current_user_location_ids())
  )
);
create policy players_super_admin_all on players for all
  using (is_super_admin()) with check (is_super_admin());
-- Anon TV: read the display_name of players standing on its token's location
-- leaderboard (for the scoreboard). Scoped by the token's location_id claim;
-- absent claim => NULL => zero rows (fail-closed), same pattern as the other
-- anon-by-token policies.
create policy players_anon_by_token on players for select to anon using (
  id in (
    select player_id from player_leaderboards
    where location_id = nullif(auth.jwt() ->> 'location_id', '')::uuid
  )
);

-- player_secrets: NO policy. RLS enabled + no policy = deny-all for anon and
-- authenticated; only service_role (bypassrls) reads/writes contact material.

-- player_leaderboards: same scope as the puck leaderboards.
create policy pl_select on player_leaderboards for select using (
  is_super_admin()
  or location_id in (select * from current_user_location_ids())
);
create policy pl_super_admin_all on player_leaderboards for all
  using (is_super_admin()) with check (is_super_admin());
create policy pl_anon_by_token on player_leaderboards for select to anon using (
  location_id = nullif(auth.jwt() ->> 'location_id', '')::uuid
);
