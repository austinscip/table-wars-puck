-- ============================================================================
-- Data retention by match age (ADR 0006)
--
-- matches/match_pucks/scores grow forever. Retention is by WHOLE MATCH:
-- deleting a terminal (finished/abandoned) match older than the window
-- cascades to its match_pucks + scores via the existing ON DELETE CASCADE
-- FKs, so the per-match-puck unique-final constraint is never partially
-- violated. Leaderboard aggregates (leaderboards, player_leaderboards) are
-- retained — they're small, pre-aggregated, and the long-term value, and
-- they don't reference matches.
--
-- Time-partitioning scores was rejected: the partition key would have to
-- join the unique-final index, allowing two finals per match_puck across
-- partitions. See ADR 0006.
-- ============================================================================

-- Cheap lookup of purge candidates: terminal matches by end time.
create index if not exists idx_matches_terminal_ended
  on matches(ended_at)
  where status in ('finished', 'abandoned');

-- Delete terminal matches older than retention_days; cascades to their
-- match_pucks + scores. Returns the number of matches purged. Idempotent and
-- safe to re-run (only removes terminal matches past the cutoff).
create or replace function purge_old_matches(retention_days integer default 90)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  v_cutoff timestamptz := now() - make_interval(days => retention_days);
  v_count  integer;
begin
  delete from matches
   where status in ('finished', 'abandoned')
     and coalesce(ended_at, started_at) < v_cutoff;
  get diagnostics v_count = row_count;
  return v_count;
end;
$$;

-- Scheduling is intentionally left to the operator (ADR 0006): enable
-- pg_cron and e.g.
--   select cron.schedule('purge-matches', '0 4 * * *',
--                         $$select purge_old_matches(90)$$);
-- or call purge_old_matches(...) from a Flask box maintenance task. We don't
-- hard-require the pg_cron extension here.
