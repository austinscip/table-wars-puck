# Handoff — Table Wars: scale-architecture phase

## User intent (verbatim, do not soften)

> "this has to be so fucking architecturally sound with no gaps whatsoever
> across any fucking aspect"
>
> "do whatever it takes to get everything done completely and the right way"

The prior phase hardened the runtime (Tiers 1–3 + durability + ops). This
phase tackles the **product/scale-architecture** gaps that sit a layer
above the runtime — the things that bite at bar-chain scale and in patron
UX. The user explicitly asked, before this handoff, to "fix numbers 1–5"
(the five gaps in §3). They are NOT quick fixes — two are schema/data-flow
decisions that need an ADR + design grilling BEFORE code.

## 1. State of the world — read these, don't re-derive

- **Branch:** `sandbox`, pushed to `origin/sandbox`
  (github.com/austinscip/table-wars-puck). 16 commits this session,
  `git log --oneline 44d7ab1..HEAD`. Every commit message is substantive.
- **Runtime contract + the deferred-work spec:** `server/runtime/CONTEXT.md`
  — READ THIS FIRST. It documents disconnect handling, durable state,
  multi-lobby, the Redis seams, and the EXACT 4-part spec for true
  multi-worker.
- **Full edge-case review:** `docs/audit/runtime-hardening-review-2026-06-05.md`
  (every case tagged Handled/Accepted/Open + an addendum).
- **What needs the USER (env vars, live Supabase, RN build, infra):**
  `docs/audit/manual-items-2026-06-05.md`. This is the master "manual"
  list — do not re-list it, point the user at it.
- **Decisions:** `docs/adr/0003-score-direction-and-cross-game-ranking.md`.
- **Deploy:** `deploy/README.md`, `deploy/tablewars-runtime.service`,
  `deploy/tablewars.env.example`, root `Dockerfile`.
- **Domain vocab:** `CONTEXT.md`. **Schema:** `supabase/migrations/`
  (three new this session: `20260605000000_anon_match_token_rls.sql`,
  `20260605000001_lobbies_realtime.sql`, plus the snapshot one).

## 2. What this session shipped (so you don't redo it)

All tested. **120 pytest + 6 jest green; mypy, eslint `.`, tsc all clean.**
Test harness is `server/tests/` (run `cd server && ./venv/bin/python -m
pytest`). The RLS suite (`test_rls.py`) bootstraps a REAL local Postgres
with a Supabase-auth shim — it's the verification gold standard here.

- **Tier 1:** per-game disconnect adapters; pytest+jest harness + CI;
  transactional match creation; input idempotency; abandoned-match sweep;
  monotonic cue `seq` (server+TV); TV Realtime resubscribe; structured
  logging + optional Sentry.
- **Tier 2:** multi-lobby per `(location_id, table_number)`; connection
  pool (`SupabaseWriter.with_pool`); Redis idempotency + distributed lock
  (built+tested, pluggable via `MatchManager(lock_provider=...)`); lobby
  published to a `lobbies` table for Realtime.
- **Tier 3 (security, verified on real Postgres):** puck JWT auth
  (`MatchTokenAuthority`); rate limiting; secret scrubbing + log redaction;
  RLS adversarial suite proving cross-org isolation; anon match-token RLS +
  `TvMatchTokenAuthority` so the TV reads exactly its match.
- **Durability (the real architectural item from last thread):** every
  game serializes/deserializes (monotonic clocks re-based); `MatchStore`
  (in-memory + Redis); `MatchManager.recover()` rebuilds active matches on
  boot. **Restart recovery verified end-to-end against real Redis.**
- **Ops/quality:** `/api/runtime/health`; CORS locked via
  `CORS_ALLOWED_ORIGINS`; mypy + ESLint gating CI; Dockerfile audit +
  systemd unit; Smash KO last-hitter fix; fleet-provisioning gate
  (`PUCK_AUTOPROVISION`); question-dedup `exclude_ids` plumbing.

**Findings that were deliberately NOT coded (correct calls, documented):**
- CSRF — N/A (no cookie auth); real gap is `/api/admin/*` has no auth.
- Full multi-worker — partial impl would be silently wrong (per-puck
  heartbeat isn't shared). The 4-part spec is in `CONTEXT.md`. Lock seam +
  idempotency are cross-worker-ready; reload-under-lock, single ticker, and
  shared heartbeat state remain.

## 3. THE WORK: 5 scale-architecture gaps (priority order)

Full reasoning is in this conversation; condensed here. **#1 and #2 are
load-bearing — get them wrong late and the rewrite is brutal. Do an ADR +
grill the design BEFORE coding them.**

**#1 — Gameplay state round-trips through the cloud (latency + the TV is a
hostage to venue internet). HIGHEST.**
All actors are local (pucks, Flask box, TV) but state flows
`puck→Flask(local)→Postgres(cloud)→Realtime(cloud)→TV(local)`. Two harms:
(a) real-time games (Racer/Smash @10Hz) inherit cloud round-trip latency —
Mike flagged Racer as riskiest for exactly this; (b) a venue internet drop
blanks the TVs mid-match even though everything local is fine (bars have
flaky Wi-Fi). The TV gameplay view subscribes ONLY to Supabase Realtime
(`TableWarsTV/src/lib/useMatchState.ts`); no local fallback.
*Suggested approach:* **local-first** — Flask serves TV state over a LAN
WebSocket; async-sync to Supabase for persistence/analytics. Fixes latency
AND offline-resilience together. This is a TV data-layer rewrite + a local
WS path — ADR first.

**#2 — No persistent player identity (the engagement engine is missing).
HIGHEST.**
A "player" today = a puck at a table for one match (`match_pucks.player_name`
is per-match). No account ties a person's matches across tables/sessions/
visits → no "you're #3 this week", no personal stats, no return-visit hook.
Retrofitting after scores/leaderboards accumulate is painful, so decide the
schema now (a `players` identity via phone/QR sign-in; link `scores` /
`match_pucks` to it). Biggest patron-UX gap. ADR first.

**#3 — Shared Supabase won't scale to a chain as-built. HIGH.**
(a) `SupabaseWriter.with_pool` connects DIRECTLY to Postgres
(`DATABASE_URL`); 100 venues × pool will exceed Postgres's connection
ceiling — must move to Supabase's **transaction pooler (pgbouncer, :6543)**,
which breaks session features incl. the `with conn.transaction()` in
`create_match` (needs a refactor). (b) Realtime fan-out + per-input
full-snapshot writes = high write/broadcast volume on one shared project.

**#4 — Trivia content is local SQLite per box. MEDIUM.**
Runtime pulls questions from `server/trivia_database.py` (SQLite ON the
venue box), not Supabase. Fleet-wide question updates = pushing files to
every box; cross-venue dedup impossible. Move content to Supabase + a
distribution/versioning story. (The `exclude_ids` dedup plumbing already
exists, waiting on a central history source.)

**#5 — Data retention + tick fidelity. MEDIUM.**
(a) `scores`/`matches` grow forever — no partitioning/archival; cheaper to
design now. (b) Game time is `tick_count`-based; if the box lags, ticks
advance slower than wall-clock → timed games run in slow-motion. Scale
ticks by real elapsed (or wall-clock).

## 4. Where to start

1. Read `server/runtime/CONTEXT.md` + the §1 docs.
2. Acknowledge the user-intent quote.
3. For **#1** and **#2**: ADR + design grilling FIRST (see skills below),
   then implement. For **#3–#5**: scope + implement with tests, same
   rigor as this session (real-DB/Redis verification where possible —
   local `psql`/`redis-server` are available).
4. Land every change with a regression test on the REAL flow (the
   `feedback_no_unguarded_fixes` policy). Keep CI green
   (pytest+mypy+jest+eslint+tsc).

## 5. Suggested skills for the next session

- **`grill-with-docs`** — stress-test the #1 (local-first) and #2 (player
  identity) designs against `CONTEXT.md` + the ADRs BEFORE coding.
- **`to-adr` / write an ADR** under `docs/adr/` for #1 and #2 (follow the
  0003 format) — these are load-bearing decisions.
- **`supabase`** — for #3 (pooler/transaction-mode) and #4 (content to
  Supabase) and any RLS on new tables.
- **`tdd`** — every gap fix is "write a real-flow regression test, then
  make it pass."
- **`diagnose`** — for the #1 latency work (measure the real round-trip,
  don't guess).

## 6. Don't (per the feedback memories that govern behaviour)

- Don't menu at handoff points if the plan is clear — follow it.
- Don't claim "fixed" without a regression test on the real flow.
- Don't kill the user's apps (Chrome/IDE/Flask) — tell them what to restart.
- Don't echo Supabase keys / JWTs / DB passwords (the log redactor handles
  runtime logs; you still must not print them).
- Don't touch the LIVE Supabase project without explicit OK (migrations are
  applied by the user — see manual-items doc).
