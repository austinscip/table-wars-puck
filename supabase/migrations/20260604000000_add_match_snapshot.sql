-- ============================================================================
-- matches.snapshot - JSONB game state written by MatchManager every
-- input / tick that changes visible state. TVs subscribe to matches
-- UPDATE events via Realtime; the snapshot column is the payload.
--
-- We do not store full per-game state history here; this is "current
-- state for the TV". Score history lives in the scores table.
-- ============================================================================

alter table matches add column snapshot jsonb;

-- The matches publication is automatic in Supabase (all tables are
-- members of supabase_realtime by default). To verify the column is
-- broadcast on UPDATE:
--
--   select pubname, schemaname, tablename, attnames
--   from pg_publication_tables
--   where pubname = 'supabase_realtime' and tablename = 'matches';
