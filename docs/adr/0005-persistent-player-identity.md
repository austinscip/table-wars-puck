# ADR 0005 — Persistent Player Identity

**Status:** Accepted
**Date:** 2026-06-05

## Context

A "player" today is a Puck at a Table for one Match. `match_pucks` carries a
per-match `player_name`; `scores` reference `match_puck_id`; `leaderboards`
are keyed by **`puck_id`** — the *hardware*, not the human. No row ties a
person's Matches across Tables, sessions, or visits. The glossary even
admitted this: *Player — the human holding a Puck, identified by Puck ID for
now.*

The consequence is the missing engagement engine: no "you're #3 this week,"
no personal stats, no return-visit hook — the biggest patron-UX gap.
Retrofitting human identity *after* scores and leaderboards have accumulated
is painful, so the schema is decided now, before the data piles up.

Two boundaries already in the schema shape the design:

- `users` / `auth.users` are **bar staff and admins**, not patrons (the
  glossary's `_Avoid_: user` line is deliberate). Patrons must not land in
  the staff auth pool.
- Every gameplay table is **location-scoped**. A persistent human is not —
  the same person plays at different operators' venues.

## Decision

**Introduce a `Player`: a persistent, global, tenant-independent human
identity, represented by a standalone `players` row, identified by an opaque
QR-delivered token with optional phone recovery. Sign-in is optional;
identity is an overlay on the existing puck-anchored model, not a
replacement.**

### What a Player is (glossary, updated in `CONTEXT.md`)

- **Player** — one human, **one `players` row across every venue/operator**
  (global; owned by no Tenant/Org/Location, unlike all other gameplay
  tables). Distinct from the Puck they hold and from staff (`users`).
- **Match Participant** — the per-Match binding (`match_pucks` row) of a
  Puck and *optionally* a Player to one Match. The transient role; the
  Player is the persistent identity.

### Identity substrate

A **standalone global `players` table**, *not* Supabase Auth. Identity is an
**opaque player token (UUID)** delivered via QR and persisted on the
patron's phone (a lightweight web profile / deep link). **Phone is
optional**, verified lazily only for cross-device recovery. Patrons never
enter `auth.users`, preserving the staff/patron boundary, and the global
`players` table stays decoupled from tenant-scoped staff auth.

Rationale: the product goal is *persistence and engagement*, not strong
authentication. The threat model is low (worst case: someone claims a
bar-game high score). At a bar, an SMS-OTP-per-visit wall would kill
adoption. A QR token gives durable cross-visit identity at zero friction and
zero SMS cost; phone-recovery backstops the one case that needs it (cleared
browser / new device). Accepted limitation: a token on a device is only as
strong as the device — that is the right trade for a bar game.

### Schema linkage

- `match_pucks` gains a **nullable `player_id` FK → `players`**. The Match
  Participant *is* the join row (it already holds `player_name`). Null =
  anonymous participant (the common case).
- **`scores` is unchanged.** Player attribution rides through
  `match_puck_id` → `match_pucks.player_id`. We deliberately do **not**
  denormalise `player_id` onto `scores` (it would drift from the
  participant row).
- A **new `player_leaderboards` table**, keyed by
  **`(player_id, game_id, location_id, period, period_start)`**, populated
  by **extending the existing `final`-score trigger**: when the scoring
  `match_pucks.player_id` is non-null, the trigger upserts a player row *in
  addition to* the existing puck row. The puck-keyed `leaderboards` table is
  **untouched** — it remains hardware analytics and the anonymous fallback.
  Including `location_id` in the key preserves **per-bar** ranking ("#3 this
  week at this bar" is a filtered query) while letting a Player profile
  **sum across locations** for a global "your stats everywhere" view. The
  higher-is-better-within-a-game invariant (ADR 0003) carries over, so
  `GREATEST` upserts stay direction-free.

### Binding flow

A **TV-displayed QR** carries table/match context. The patron scans it,
opens a phone web profile (their token auto-identifies a returning patron, or
mints one on first scan), sees the live lobby's seats/colors, and taps their
color to bind their `player_id` to that Match Participant. **No firmware
change** — the Puck firmware stays ignorant of the human. Binding is allowed
during **lobby _or_ active**, any time before `_finalize` writes the `final`
row (the trigger reads `match_pucks.player_id` at `final`-insert, so
late-identify still counts). All writes go through the Flask box
(service_role).

### Privacy / RLS (a new, global-table shape)

Public handle is split from private contact:

- **`players`** holds only `id`, **`display_name`** (a chosen public
  handle), `created_at` — readable for leaderboard display so staff and the
  anon TV can render "TopGun88 is #1."
- **`player_secrets`** holds the token hash + optional **phone hash**,
  **service-role-only** — no anon/staff RLS policy exists; only the Flask
  box (service_role, bypasses RLS) touches it.
- **All writes via Flask service_role**, like every other gameplay write —
  the box mints/looks up tokens; patrons never write directly.
- **Deletion (GDPR "forget me"):** `match_pucks.player_id` is
  **`ON DELETE SET NULL`** (a deleted Player de-attributes from history but
  Matches/scores survive — leaderboard *truth* is not rewritten);
  `player_leaderboards` is **`ON DELETE CASCADE`** (personal aggregates go).
- **Enumeration:** `players` exposes only `display_name`, and only for rows
  surfaced through a location's own leaderboard query, so one operator
  cannot enumerate the global player base or read any phone/token. Global
  identity exists, but contact info never crosses the service-role boundary.

## Consequences

- The puck-anchored model is untouched and remains the default: anonymous
  play needs zero identity. Player identity is a **purely additive overlay**
  (`match_pucks.player_id` nullable; a new leaderboard table; an additive
  trigger branch). No existing query or the puck leaderboard changes
  behaviour.
- The engagement surfaces ("#3 this week," personal stats, cross-visit
  history) are now expressible as queries over `player_leaderboards` and
  `match_pucks.player_id` — none were before.
- A **global, tenant-independent** table now exists in an otherwise
  strictly location-scoped schema. Its RLS is bespoke (public handle vs
  service-role-only contact) and must be proven by the adversarial RLS suite
  (`server/tests/test_rls.py`), the same gold standard used for cross-org
  isolation.
- Identity strength is intentionally weak (device-held token). If a future
  product needs verified identity (e.g. real-money or cross-device-critical
  features), it layers phone/OTP verification onto the existing `players`
  row — it does not require a re-key.
- The `final`-score trigger now writes up to two leaderboard rows. The
  extension must be covered by a real-flow regression test that drives a
  Match with a bound Player through to `final` and asserts both the puck row
  and the player row land — and that an anonymous (null `player_id`) Match
  writes only the puck row.
- New PII (optional phone) enters the system, isolated to a
  service-role-only table and hashed. The log redactor and secret-scrubbing
  already in place must cover it; it must never be echoed.
