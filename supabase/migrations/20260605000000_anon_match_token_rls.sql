-- ============================================================================
-- Anon read access for the TV, scoped by a signed match token.
-- ============================================================================
--
-- The TV renders a match using the Supabase ANON key. The initial schema
-- enabled RLS on matches/match_pucks/scores/leaderboards but only wrote
-- policies for super_admin + location-scoped *authenticated* users — so an
-- anon session reads NOTHING (verified: anon -> 0 rows). The TV therefore
-- could only ever work by either disabling RLS (unacceptable) or by a
-- capability-URL (knowing the match_id), which the security review flags:
-- "if you knew bar B's match_id you could subscribe from bar A".
--
-- The right fix: the TV authenticates to Supabase Realtime with a
-- short-lived token MINTED BY THE SERVER (signed with the Supabase JWT
-- secret) carrying a `match_id` (and `location_id`) claim and `role: anon`.
-- These policies then let an anon session read ONLY the exact match its
-- token names. Knowing another venue's match_id is not enough — you need a
-- token the server signed for it.
--
-- Token claims expected:  { role: 'anon', match_id: <uuid>, location_id: <uuid>, exp, iat }
-- The server mints it (see server/runtime/auth.py :: TvMatchTokenAuthority)
-- and the TV passes it via supabase.realtime.setAuth(token).
--
-- Safety: when the claim is absent (a plain anon key with no token),
-- auth.jwt() ->> 'match_id' is NULL, every comparison is NULL, and the
-- policies expose zero rows — fail-closed.

-- matches: read exactly the token's match.
create policy matches_anon_by_token on matches for select to anon using (
  id = nullif(auth.jwt() ->> 'match_id', '')::uuid
);

-- match_pucks: rows belonging to the token's match.
create policy mp_anon_by_token on match_pucks for select to anon using (
  match_id = nullif(auth.jwt() ->> 'match_id', '')::uuid
);

-- scores: rows belonging to the token's match (mid-match + final).
create policy scores_anon_by_token on scores for select to anon using (
  match_id = nullif(auth.jwt() ->> 'match_id', '')::uuid
);

-- leaderboards: the scoreboard shows a location's standings, scoped to the
-- token's location_id claim (not match_id).
create policy lb_anon_by_token on leaderboards for select to anon using (
  location_id = nullif(auth.jwt() ->> 'location_id', '')::uuid
);

-- games is already public-read (games_select using (true)); the TV needs it
-- to resolve a match's game_slug, so no change required there.
