# ADR 0008 — Trivia Content in Supabase, Cached Locally

**Status:** Accepted
**Date:** 2026-06-05

## Context

Trivia questions lived in a per-box SQLite file (`trivia_database.py`). The
runtime's Speed Pyramid pulled from it at match creation. Two scale problems
(gap #4): a fleet-wide content update meant pushing files to every venue box,
and cross-venue dedup ("don't re-serve a question this player saw at another
bar") was impossible because there was no shared source. The `exclude_ids`
dedup plumbing already exists in the load path, waiting on a central history.

But the box must keep serving trivia through a venue internet drop
(local-first, ADR 0004) — so "just read from Supabase per match" is wrong: a
WAN blip would freeze the game.

## Decision

**Supabase is the source of truth for trivia content; the box syncs the
active bank into a local cache and selects every match's questions from the
cache.** Gameplay never waits on (or fails because of) the cloud.

- A `trivia_questions` table (mirroring the SQLite columns) with public-read
  RLS on **active** questions and super_admin/service_role writes. A
  `trivia_content_version()` fingerprint changes on any content edit.
- A `TriviaContentCache` (`runtime/trivia_content.py`) syncs the whole
  active bank + version into memory and a JSON file (`refresh()`), then
  serves `load(count, difficulty, exclude_ids)` by filtering + random-
  sampling the cache **in-process**. Refresh is **version-gated** (skip when
  unchanged) and **best-effort**: any failure keeps the existing cache, so an
  outage degrades to stale-but-working, never empty. A cold boot offline
  reads the last JSON cache from disk.
- Speed Pyramid gains a pluggable module-level question source; the runtime
  container wires it to the cache's `load`. The source order is **cloud
  cache → legacy local SQLite → built-in defaults**, so a fresh dev box and
  the tests work with no content configured.

## Consequences

- Fleet content updates are a Supabase edit; boxes pick them up on their next
  version-gated refresh — no file pushes. Content is authored/managed in one
  place.
- The box holds the whole active bank in memory (questions are small; a few
  thousand rows is nothing), so per-match selection is instant and offline-
  safe. The trade is staleness between refreshes, bounded by how often the
  box refreshes (boot + future periodic/▲on-version-change).
- **Still open (explicitly out of scope here): cross-venue dedup.**
  `exclude_ids` is honored by the cache, but sourcing those ids — a central
  per-player question history — needs the runtime to persist `question_id`
  per answer (a `player_question_history` write keyed by the ADR 0005
  `player_id`). That's the natural next step now that both a central content
  source (this ADR) and a global player identity (ADR 0005) exist.
- Periodic/background refresh and a manual "refresh now" admin trigger are
  follow-ups; today the cache refreshes at container boot (best-effort) and
  lazily on first use.
- The legacy SQLite path and `trivia_database.py` remain as the fallback and
  for the legacy (non-runtime) trivia stack; they are no longer the runtime's
  primary content source.
