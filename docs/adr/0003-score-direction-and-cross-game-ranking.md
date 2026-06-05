# ADR 0003 — Score Direction and Cross-Game Ranking

**Status:** Accepted
**Date:** 2026-06-05

## Context

Each runtime game emits a `score_total` with its own direction and units:

| Game | `score_total` meaning | Direction |
|---|---|---|
| Speed Pyramid | sum of speed-tiered points (1000/500/200/0) | higher = better |
| Puck Golf | `sum(strokes) * -1` (negative) | higher = better (least-negative = fewest strokes) |
| Puck Racer | clamped position + finish-rank bonus | higher = better |
| Smash | `stocks*1000 + kos*200` | higher = better |

The `leaderboards` table is keyed by `(location_id, game_id, puck_id,
period, period_start)` and stores `high_score`, upserted with `GREATEST`.
So **every game's direction was deliberately normalised to "higher is
better"** — Puck Golf negates strokes precisely so `GREATEST` picks the
fewest-strokes round. Within a game, the leaderboard is coherent.

The open question (raised in the hardening review): the *magnitudes* are
not comparable across games — 1000 points in Speed Pyramid, -8 in Golf,
3200 in Smash all live in the same column. Should we normalise so scores
can be ranked across games?

## Decision

**No cross-game ranking. Leaderboards are per-game, and `score_total`
magnitude is only meaningful within a single `game_id`.**

- The schema already isolates this: `leaderboards` rows carry `game_id`,
  and every query/leaderboard view MUST filter by `game_id`. There is no
  product surface that ranks a player's Golf score against their Smash
  score, and none is planned — "best Speed Pyramid player this week" is
  the unit of competition, not "best overall."
- The only invariant we rely on is **higher-is-better within a game**,
  which every game already satisfies (Golf via negation). That keeps
  `GREATEST`-based upserts correct without a per-game direction flag.

## Consequences

- Do **not** sum, average, or compare `score_total` across different
  `game_id`s. Any "overall" leaderboard would be meaningless and is out of
  scope.
- If a future product wants a cross-game "channel points" or "house
  ranking", it needs a separate normalised currency (e.g. points awarded
  per match placement, identical scale across games) written to a new
  column/table — NOT a reinterpretation of `score_total`.
- New games must keep the higher-is-better convention for `score_total`
  (negate/invert internally if their natural metric is lower-is-better,
  as Puck Golf does), so the leaderboards trigger stays direction-free.
