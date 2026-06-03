-- ============================================================================
-- TABLE WARS — Initial multi-tenant schema
-- Hierarchy: Tenant → Organization → Location
--
-- All writes from the Flask server use the Supabase service_role key, which
-- bypasses RLS. RLS protects logged-in bar staff (bar portal), super-admins
-- (observability app), and public/anon reads (TV view).
-- ============================================================================

create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- ============================================================================
-- ENUM TYPES
-- ============================================================================

create type tenant_status       as enum ('trial', 'active', 'suspended');
create type org_role            as enum ('super_admin', 'tenant_admin', 'org_admin');
create type location_role       as enum ('bar_manager', 'bar_staff');
create type hw_revision         as enum ('RevA', 'RevB', 'Casino');
create type firmware_channel    as enum ('stable', 'beta', 'dev');
create type match_status        as enum ('lobby', 'active', 'finished', 'abandoned');
create type puck_role           as enum ('host', 'sibling');
create type score_event_type    as enum ('round', 'final');
create type leaderboard_period  as enum ('day', 'week', 'month', 'all_time');

-- ============================================================================
-- TENANCY LAYER
-- ============================================================================

create table tenants (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  slug          text not null unique,
  billing_email text,
  status        tenant_status not null default 'trial',
  created_at    timestamptz not null default now()
);

create table organizations (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenants(id) on delete cascade,
  name        text not null,
  slug        text not null,
  created_at  timestamptz not null default now(),
  unique (tenant_id, slug)
);
create index idx_organizations_tenant on organizations(tenant_id);

create table locations (
  id              uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  name            text not null,
  slug            text not null,
  city            text,
  state           text,
  timezone        text not null default 'America/Detroit',
  table_count     smallint not null default 4,
  is_active       boolean not null default true,
  created_at      timestamptz not null default now(),
  unique (organization_id, slug)
);
create index idx_locations_org on locations(organization_id);

-- 1:1 mirror of auth.users. Profile fields live here so RLS policies on app
-- tables can join against a public-schema table without crossing schemas.
create table users (
  id           uuid primary key references auth.users(id) on delete cascade,
  email        text not null,
  display_name text,
  created_at   timestamptz not null default now()
);

create table user_org_roles (
  user_id         uuid not null references users(id) on delete cascade,
  organization_id uuid not null references organizations(id) on delete cascade,
  role            org_role not null,
  created_at      timestamptz not null default now(),
  primary key (user_id, organization_id, role)
);
create index idx_uor_user on user_org_roles(user_id);
create index idx_uor_org  on user_org_roles(organization_id);

create table user_location_roles (
  user_id     uuid not null references users(id) on delete cascade,
  location_id uuid not null references locations(id) on delete cascade,
  role        location_role not null,
  created_at  timestamptz not null default now(),
  primary key (user_id, location_id, role)
);
create index idx_ulr_user     on user_location_roles(user_id);
create index idx_ulr_location on user_location_roles(location_id);

-- Mirror new auth.users rows into public.users automatically.
create or replace function handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.users(id, email, display_name)
  values (new.id, new.email,
          coalesce(new.raw_user_meta_data->>'display_name', new.email))
  on conflict (id) do nothing;
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function handle_new_auth_user();

-- ============================================================================
-- HARDWARE LAYER
-- ============================================================================

create table firmware_versions (
  id            uuid primary key default gen_random_uuid(),
  version       text not null,
  channel       firmware_channel not null default 'dev',
  hw_revision   hw_revision not null,
  signed_url    text,
  sha256        text,
  release_notes text,
  released_at   timestamptz not null default now(),
  unique (version, hw_revision)
);
create index idx_firmware_channel_hw on firmware_versions(channel, hw_revision);

create table pucks (
  id                  uuid primary key default gen_random_uuid(),
  serial_no           text not null unique,
  hw_revision         hw_revision not null,
  puck_index          smallint check (puck_index between 1 and 8),
  current_firmware_id uuid references firmware_versions(id),
  battery_pct         smallint check (battery_pct between 0 and 100),
  is_online           boolean not null default false,
  last_seen           timestamptz,
  created_at          timestamptz not null default now()
);
create index idx_pucks_firmware  on pucks(current_firmware_id);
create index idx_pucks_last_seen on pucks(last_seen desc);

create table puck_assignments (
  id           uuid primary key default gen_random_uuid(),
  puck_id      uuid not null references pucks(id) on delete cascade,
  location_id  uuid not null references locations(id) on delete cascade,
  table_number smallint,
  assigned_at  timestamptz not null default now(),
  removed_at   timestamptz
);
-- A puck is assigned to at most one location at a time.
create unique index uniq_active_assignment_per_puck
  on puck_assignments(puck_id) where removed_at is null;
create index idx_pa_location_active
  on puck_assignments(location_id) where removed_at is null;

create table tvs (
  id              uuid primary key default gen_random_uuid(),
  location_id     uuid not null references locations(id) on delete cascade,
  device_name     text not null,
  table_number    smallint,
  app_version     text,
  storage_free_kb integer,
  is_online       boolean not null default false,
  last_seen       timestamptz,
  created_at      timestamptz not null default now()
);
create index idx_tvs_location on tvs(location_id);

-- ============================================================================
-- GAMEPLAY LAYER
-- ============================================================================

create table games (
  id              uuid primary key default gen_random_uuid(),
  slug            text not null unique,
  display_name    text not null,
  min_players     smallint not null default 1,
  max_players     smallint not null default 8,
  runtime_version text not null default '0.1.0',
  is_published    boolean not null default false,
  created_at      timestamptz not null default now()
);

create table matches (
  id            uuid primary key default gen_random_uuid(),
  location_id   uuid not null references locations(id) on delete cascade,
  game_id       uuid not null references games(id),
  table_number  smallint,
  status        match_status not null default 'lobby',
  started_at    timestamptz not null default now(),
  ended_at      timestamptz,
  player_count  smallint not null default 0
);
create index idx_matches_location_started on matches(location_id, started_at desc);
create index idx_matches_game on matches(game_id);
create index idx_matches_open on matches(status) where status in ('lobby', 'active');

create table match_pucks (
  id          uuid primary key default gen_random_uuid(),
  match_id    uuid not null references matches(id) on delete cascade,
  puck_id     uuid not null references pucks(id),
  role        puck_role not null default 'sibling',
  player_name text,
  joined_at   timestamptz not null default now(),
  left_at     timestamptz,
  unique (match_id, puck_id)
);
create index idx_mp_match on match_pucks(match_id);
create index idx_mp_puck  on match_pucks(puck_id);

create table scores (
  id            uuid primary key default gen_random_uuid(),
  match_id      uuid not null references matches(id) on delete cascade,
  match_puck_id uuid not null references match_pucks(id) on delete cascade,
  round_number  smallint not null default 0,
  score_delta   integer not null,
  score_total   integer not null,
  event_type    score_event_type not null default 'round',
  recorded_at   timestamptz not null default now()
);
create index idx_scores_match      on scores(match_id);
create index idx_scores_match_puck on scores(match_puck_id);
create index idx_scores_final      on scores(match_id) where event_type = 'final';
-- A match emits at most one `final` event per puck. Enforced at the DB layer
-- so leaderboard counters can't inflate from a buggy game engine.
create unique index uniq_final_score_per_match_puck
  on scores(match_id, match_puck_id) where event_type = 'final';

-- ============================================================================
-- LEADERBOARDS (materialized table, updated by trigger on `final` scores)
-- ============================================================================

create table leaderboards (
  id            uuid primary key default gen_random_uuid(),
  location_id   uuid not null references locations(id) on delete cascade,
  game_id       uuid not null references games(id) on delete cascade,
  puck_id       uuid not null references pucks(id) on delete cascade,
  period        leaderboard_period not null,
  period_start  date not null,
  high_score    integer not null default 0,
  total_matches integer not null default 0,
  updated_at    timestamptz not null default now(),
  unique (location_id, game_id, puck_id, period, period_start)
);
create index idx_lb_location_game_period
  on leaderboards(location_id, game_id, period, high_score desc);

-- Only `final` events count toward leaderboards; `round` events are mid-match.
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
  v_today       date := (now() at time zone 'UTC')::date;
  v_week        date := date_trunc('week',  now() at time zone 'UTC')::date;
  v_month       date := date_trunc('month', now() at time zone 'UTC')::date;
  v_all_time    date := '1970-01-01'::date;
begin
  if new.event_type <> 'final' then
    return new;
  end if;

  select m.location_id, m.game_id, mp.puck_id
    into v_location_id, v_game_id, v_puck_id
  from matches m
    join match_pucks mp on mp.id = new.match_puck_id
  where m.id = new.match_id;

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

  return new;
end;
$$;

create trigger trg_scores_update_leaderboards
  after insert on scores
  for each row execute function update_leaderboards_on_final_score();

-- ============================================================================
-- RLS HELPER FUNCTIONS
-- All are SECURITY DEFINER so policies can call them without recursing into
-- their own RLS. STABLE so the planner can fold them into queries.
-- ============================================================================

create or replace function current_user_org_ids()
returns setof uuid
language sql
stable
security definer
set search_path = public
as $$
  select organization_id from user_org_roles where user_id = auth.uid()
$$;

create or replace function current_user_location_ids()
returns setof uuid
language sql
stable
security definer
set search_path = public
as $$
  select id from locations
    where organization_id in (select * from current_user_org_ids())
  union
  select location_id from user_location_roles where user_id = auth.uid()
$$;

create or replace function is_super_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from user_org_roles
    where user_id = auth.uid() and role = 'super_admin'
  )
$$;

-- ============================================================================
-- ROW-LEVEL SECURITY
-- ============================================================================

alter table tenants             enable row level security;
alter table organizations       enable row level security;
alter table locations           enable row level security;
alter table users               enable row level security;
alter table user_org_roles      enable row level security;
alter table user_location_roles enable row level security;
alter table firmware_versions   enable row level security;
alter table pucks               enable row level security;
alter table puck_assignments    enable row level security;
alter table tvs                 enable row level security;
alter table games               enable row level security;
alter table matches             enable row level security;
alter table match_pucks         enable row level security;
alter table scores              enable row level security;
alter table leaderboards        enable row level security;

-- tenants
create policy tenants_select on tenants for select using (
  is_super_admin()
  or id in (
    select tenant_id from organizations
    where id in (select * from current_user_org_ids())
  )
);
create policy tenants_super_admin_all on tenants for all
  using (is_super_admin()) with check (is_super_admin());

-- organizations
create policy organizations_select on organizations for select using (
  is_super_admin() or id in (select * from current_user_org_ids())
);
create policy organizations_super_admin_all on organizations for all
  using (is_super_admin()) with check (is_super_admin());

-- locations
create policy locations_select on locations for select using (
  is_super_admin() or id in (select * from current_user_location_ids())
);
create policy locations_super_admin_all on locations for all
  using (is_super_admin()) with check (is_super_admin());

-- users (profile)
create policy users_select_self on users for select
  using (id = auth.uid() or is_super_admin());
create policy users_update_self on users for update
  using (id = auth.uid()) with check (id = auth.uid());

-- user_org_roles / user_location_roles
create policy uor_select on user_org_roles for select
  using (user_id = auth.uid() or is_super_admin());
create policy uor_super_admin_all on user_org_roles for all
  using (is_super_admin()) with check (is_super_admin());

create policy ulr_select on user_location_roles for select
  using (user_id = auth.uid() or is_super_admin());
create policy ulr_super_admin_all on user_location_roles for all
  using (is_super_admin()) with check (is_super_admin());

-- firmware_versions: pucks fetch manifest anonymously; super_admin manages.
create policy firmware_select on firmware_versions for select using (true);
create policy firmware_super_admin_all on firmware_versions for all
  using (is_super_admin()) with check (is_super_admin());

-- pucks: visible to people who can see the puck's current location.
create policy pucks_select on pucks for select using (
  is_super_admin()
  or id in (
    select puck_id from puck_assignments
    where removed_at is null
      and location_id in (select * from current_user_location_ids())
  )
);

-- puck_assignments
create policy pa_select on puck_assignments for select using (
  is_super_admin()
  or location_id in (select * from current_user_location_ids())
);

-- tvs
create policy tvs_select on tvs for select using (
  is_super_admin()
  or location_id in (select * from current_user_location_ids())
);

-- games: public read
create policy games_select on games for select using (true);
create policy games_super_admin_all on games for all
  using (is_super_admin()) with check (is_super_admin());

-- matches / match_pucks / scores: scoped by location.
-- TV view reads anonymously; a follow-up migration will add an anon policy
-- gated on a signed match token once we wire the TV view auth.
create policy matches_select on matches for select using (
  is_super_admin()
  or location_id in (select * from current_user_location_ids())
);

create policy mp_select on match_pucks for select using (
  is_super_admin()
  or match_id in (
    select id from matches
    where location_id in (select * from current_user_location_ids())
  )
);

create policy scores_select on scores for select using (
  is_super_admin()
  or match_id in (
    select id from matches
    where location_id in (select * from current_user_location_ids())
  )
);

-- leaderboards: same scope as matches.
create policy leaderboards_select on leaderboards for select using (
  is_super_admin()
  or location_id in (select * from current_user_location_ids())
);

-- ============================================================================
-- SEED DATA
-- ============================================================================

-- Pilot tenant / org / location: collapses to 1/1/1 for the friendly-bar pilot.
with t as (
  insert into tenants(name, slug, billing_email, status)
  values ('Lead Bounty', 'lead-bounty', 'info@leadbountymi.com', 'trial')
  returning id
),
o as (
  insert into organizations(tenant_id, name, slug)
  select id, 'Pilot Bar Co', 'pilot-bar-co' from t
  returning id
),
l as (
  insert into locations(organization_id, name, slug, city, state, timezone, table_count)
  select id, 'Friendly Bar', 'friendly-bar-detroit', 'Detroit', 'MI', 'America/Detroit', 4 from o
  returning id
)
select 1;

-- The 4 games on the multi-game runtime. Unpublished until each is wired in.
insert into games(slug, display_name, min_players, max_players, runtime_version, is_published) values
  ('speed_pyramid', 'Speed Pyramid', 1, 8, '0.1.0', false),
  ('puck_golf',     'Puck Golf',     1, 8, '0.1.0', false),
  ('puck_racer',    'Puck Racer',    2, 8, '0.1.0', false),
  ('smash',         'Smash',         2, 4, '0.1.0', false);
