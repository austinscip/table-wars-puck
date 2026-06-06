-- ============================================================================
-- Trivia content in Supabase (ADR 0008, gap #4)
--
-- Trivia questions lived in a per-box SQLite file, so a fleet-wide content
-- update meant pushing files to every venue and cross-venue dedup was
-- impossible. Move the content to Supabase as the source of truth; the box
-- caches it locally (offline-resilient, ADR 0004) and selects per-match from
-- the cache. A content-version string lets the box tell when to refresh.
-- ============================================================================

create table trivia_questions (
  id             bigint generated always as identity primary key,
  question_text  text not null,
  setup_text     text,
  answer_a       text not null,
  answer_b       text not null,
  answer_c       text not null,
  answer_d       text not null,
  correct_answer char(1) not null check (correct_answer in ('A', 'B', 'C', 'D')),
  category       text,
  difficulty     text,
  time_limit     smallint not null default 15,
  is_active      boolean not null default true,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);
create index idx_trivia_active on trivia_questions(is_active) where is_active;

-- Keep updated_at honest so the content version below changes on any edit.
create or replace function touch_trivia_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end;
$$;
create trigger trg_trivia_touch
  before update on trivia_questions
  for each row execute function touch_trivia_updated_at();

-- A cheap fingerprint of the active question bank. Changes whenever a
-- question is added, edited, or (de)activated — so a box can compare its
-- cached version and refresh only when content actually moved.
create or replace function trivia_content_version()
returns text
language sql
stable
security definer
set search_path = public
as $$
  select coalesce(extract(epoch from max(updated_at))::bigint::text, '0')
         || ':' || count(*)::text
  from trivia_questions
  where is_active;
$$;

-- ----------------------------------------------------------------------------
-- RLS: content is global + public-readable (active only); only super_admin
-- (or the box as service_role, which bypasses RLS) writes.
-- ----------------------------------------------------------------------------

alter table trivia_questions enable row level security;

create policy tq_select on trivia_questions for select using (
  is_active or is_super_admin()
);
create policy tq_super_admin_all on trivia_questions for all
  using (is_super_admin()) with check (is_super_admin());

-- ----------------------------------------------------------------------------
-- Seed a few starter questions so a fresh box has content on first sync.
-- ----------------------------------------------------------------------------

insert into trivia_questions
  (question_text, setup_text, answer_a, answer_b, answer_c, answer_d, correct_answer, category, difficulty, time_limit)
values
  ('Which planet is known as the Red Planet?', 'An easy one to warm up.',
   'Venus', 'Mars', 'Jupiter', 'Saturn', 'B', 'Science', 'easy', 12),
  ('What cocktail is made with rum, lime, and mint?', 'Bar trivia, naturally.',
   'Margarita', 'Mojito', 'Negroni', 'Martini', 'B', 'Food & Drink', 'easy', 12),
  ('In what year did the first iPhone launch?', 'A little harder.',
   '2005', '2006', '2007', '2008', 'C', 'Tech', 'medium', 15);
