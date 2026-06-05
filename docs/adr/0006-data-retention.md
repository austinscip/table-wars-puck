# ADR 0006 — Data Retention by Match Age

**Status:** Accepted
**Date:** 2026-06-05

## Context

`matches`, `match_pucks`, and `scores` grow without bound — every play-through
adds rows forever. At one bar that's nothing; across a chain it's the bulk of
the data and the dominant cost. The handoff (gap #5a) flags designing
retention/archival now, while it's cheap to change.

The obvious move — range-**partition `scores` by time** and drop old
partitions — collides with two facts of the existing schema:

1. **The per-match-puck unique-final constraint spans all time.**
   `uniq_final_score_per_match_puck` is `unique(match_id, match_puck_id)
   where event_type='final'`. Postgres requires a partition key to be part
   of every unique index, so partitioning `scores` by `recorded_at` would
   force the constraint to include time — letting a match_puck have two
   `final` rows in different months. That silently breaks leaderboard
   integrity (the constraint exists precisely so a buggy engine can't
   inflate a high score).
2. **FK topology.** Partitioning `matches` by `started_at` makes its PK
   `(id, started_at)`, so every FK into it (`scores`, `match_pucks`,
   `leaderboards`) must carry `started_at` too — a wide, invasive change.

## Decision

**Retention is by whole-match age, not by time-partitioning. A match and its
children are one unit: deleting a finished/abandoned match older than the
retention window cascades to its `match_pucks` and `scores`. The leaderboard
aggregates are kept forever.**

- A `purge_old_matches(retention_days int default 90)` SQL function
  (`security definer`) deletes `matches` in status `finished`/`abandoned`
  whose end time is older than the window. The existing
  `on delete cascade` FKs remove the match's `match_pucks` and `scores`
  with it, so the unique-final constraint is preserved (whole matches go,
  never partial history). A partial index on terminal matches by `ended_at`
  keeps the purge cheap.
- `leaderboards` and `player_leaderboards` are **retained** — they are small,
  pre-aggregated, and the long-term product value ("this month's high
  scores", a player's history). They reference location/game/puck/player,
  not `match`, so a match purge never touches them.
- The function is **defined but not self-scheduled**: invoke it from
  Supabase `pg_cron` (once enabled) or a Flask box maintenance call. The
  window is a parameter, not baked in, so different operators/tiers can pick
  their own (raw data 90d default; aggregates forever).

## Consequences

- Raw per-input history (`scores` `round` rows, mid-match snapshots) is the
  bulk of the volume and ages out with its match; the durable competition
  record (leaderboards) persists. This matches what the product actually
  queries long-term.
- Deletion (vs. dropping a partition) is more expensive per row, but the
  unit is a whole match and the partial index bounds the scan; at chain
  scale the purge runs incrementally (by window) off-peak. If a single venue
  ever generates enough `scores` that per-row deletion hurts, partitioning
  `scores` by `match_id`-hash (NOT time) remains a compatible future step —
  it keeps the unique-final constraint intact.
- Anything that needs raw history beyond the window (analytics, audits) must
  export/aggregate it before the purge — there is no undo. The default 90d
  window is deliberately generous; shorten per-operator only with that in
  mind.
- A purge is **idempotent and safe to re-run**; it only ever removes
  terminal matches past the cutoff.
