-- ============================================================================
-- Schema hardening (deep-review audit 2026-06-06): leaderboard timezone
-- correctness, player_count maintenance, FK indexes + ON DELETE fixes,
-- contact/trivia constraints, batched retention, updated_at + autovacuum,
-- and defense-in-depth grants. Idempotent where practical.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1.1 — Leaderboards bucket in the LOCATION's timezone, not UTC.
-- "Today's high score" must reset at local midnight and "this week" must be the
-- bar's week, not an ISO-Monday-UTC week. locations.timezone already exists.
-- Rewrites the final-score trigger (preserving the player_leaderboards branch).
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
  v_tz          text;
  v_today       date;
  v_week        date;
  v_month       date;
  v_all_time    date := '1970-01-01'::date;
begin
  if new.event_type <> 'final' then
    return new;
  end if;

  select m.location_id, m.game_id, mp.puck_id, mp.player_id, l.timezone
    into v_location_id, v_game_id, v_puck_id, v_player_id, v_tz
  from matches m
    join match_pucks mp on mp.id = new.match_puck_id
    join locations  l  on l.id = m.location_id
  where m.id = new.match_id;

  v_tz    := coalesce(v_tz, 'UTC');
  v_today := (now() at time zone v_tz)::date;
  v_week  := date_trunc('week',  now() at time zone v_tz)::date;
  v_month := date_trunc('month', now() at time zone v_tz)::date;

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
-- 2.4 — matches.player_count is read by the bar portal but was never written
-- (always 0). Maintain it from match_pucks so the dashboard shows real counts.
-- ----------------------------------------------------------------------------

create or replace function refresh_match_player_count()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_match uuid := coalesce(new.match_id, old.match_id);
begin
  update matches
     set player_count = (
       select count(*) from match_pucks where match_id = v_match
     )
   where id = v_match;
  return null;
end;
$$;

create trigger trg_match_pucks_player_count
  after insert or delete on match_pucks
  for each row execute function refresh_match_player_count();

-- Backfill existing matches.
update matches m
   set player_count = (select count(*) from match_pucks mp where mp.match_id = m.id);

-- ----------------------------------------------------------------------------
-- 2.3 — matches.updated_at (the snapshot/finish/abandon write path mutates the
-- row constantly with no last-changed timestamp) + aggressive autovacuum on
-- the hot, frequently-rewritten matches table to bound MVCC bloat.
-- ----------------------------------------------------------------------------

alter table matches add column if not exists updated_at timestamptz not null default now();

create or replace function touch_matches_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

create trigger trg_matches_touch
  before update on matches
  for each row execute function touch_matches_updated_at();

alter table matches set (
  autovacuum_vacuum_scale_factor = 0.05,
  autovacuum_analyze_scale_factor = 0.05
);

-- ----------------------------------------------------------------------------
-- 2.2 — FK-backing indexes (Postgres does not auto-index FKs). Without these,
-- deleting a game/puck/player seq-scans the big aggregate tables per row.
-- ----------------------------------------------------------------------------

create index if not exists idx_lb_game     on leaderboards(game_id);
create index if not exists idx_lb_puck     on leaderboards(puck_id);
create index if not exists idx_pl_game     on player_leaderboards(game_id);

-- 2.2 — a puck whose firmware record is deleted should just have unknown
-- firmware, not block the delete (was ON DELETE NO ACTION).
alter table pucks drop constraint if exists pucks_current_firmware_id_fkey;
alter table pucks add constraint pucks_current_firmware_id_fkey
  foreign key (current_firmware_id) references firmware_versions(id) on delete set null;

-- ----------------------------------------------------------------------------
-- 2.4 — contact + content constraints.
-- phone_hash must be UNIQUE (recovery does a single-row lookup); difficulty and
-- time_limit on trivia must be sane.
-- ----------------------------------------------------------------------------

drop index if exists idx_player_secrets_phone;
create unique index uniq_player_secrets_phone
  on player_secrets(phone_hash) where phone_hash is not null;

alter table trivia_questions
  add constraint trivia_difficulty_ck
  check (difficulty is null or difficulty in ('easy', 'medium', 'hard'));
alter table trivia_questions
  add constraint trivia_time_limit_ck check (time_limit > 0);

-- ----------------------------------------------------------------------------
-- 2.5 — batched retention. The single-statement purge_old_matches stays for
-- steady-state daily use; this PROCEDURE deletes in committed batches for a
-- large initial backfill so it never holds one giant transaction / WAL spike.
-- ----------------------------------------------------------------------------

create or replace procedure purge_old_matches_batched(
  retention_days integer default 90,
  batch_size     integer default 5000
)
language plpgsql
as $$
declare
  v_cutoff timestamptz := now() - make_interval(days => retention_days);
  v_batch  integer;
begin
  loop
    delete from matches
     where id in (
       select id from matches
        where status in ('finished', 'abandoned')
          and coalesce(ended_at, started_at) < v_cutoff
        limit batch_size
     );
    get diagnostics v_batch = row_count;
    commit;  -- release locks + WAL between batches
    exit when v_batch = 0;
  end loop;
end;
$$;

-- ----------------------------------------------------------------------------
-- 2.1 — defense-in-depth grants. RLS is the primary gate, but the gameplay /
-- content / identity tables are written ONLY by the server (service_role,
-- which bypasses RLS). Revoke client DML on them so a future permissive
-- policy can't silently expose writes, and we don't rely on Supabase dashboard
-- defaults. SELECT stays (RLS scopes it); user-profile tables are untouched so
-- the portal's profile writes still work.
-- ----------------------------------------------------------------------------

revoke insert, update, delete on
  matches, match_pucks, scores, leaderboards, player_leaderboards,
  players, player_secrets, trivia_questions, lobbies, pucks, puck_assignments
from anon, authenticated;
