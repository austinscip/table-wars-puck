# Manual items — what needs you (not code)

Everything below is something I could not do or fully verify from inside
the sandbox: it needs your live environment (Supabase project, a device
build, a deploy target) or a decision/credential only you hold. Grouped by
urgency for the pilot.

## 1. Secrets / env vars to set in production

Set these on the venue's Flask box (and staging). The code reads them; it
runs in safe/open mode when they're absent.

| Var | Purpose | Notes |
|---|---|---|
| `PUCK_JWT_SECRET` | Enables puck input auth (item 13). | **≥32 bytes.** Generate: `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Without it, input is unauthenticated. |
| `SUPABASE_JWT_SECRET` | Enables the TV match-token mint (item 17). | This is your Supabase project's **JWT secret** (Dashboard → Settings → API → JWT Secret). Must match so Realtime accepts the token. |
| `PUCK_AUTOPROVISION=0` | Locks the fleet in prod (item, Tier 4). | Unknown puck_index then raises instead of self-registering. Pre-provision pucks first. |
| `SCRUB_SECRETS_AFTER_BOOT=1` | Drops DATABASE_URL/secrets from env after boot (item 16). | Safe in this codebase (verified). |
| `SENTRY_DSN` (+ `pip install sentry-sdk`) | Error reporting (item 8). | Optional `ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE`. |
| `LOCATION_ID` | Pins the Flask box to one venue. | Already used; confirm it's set per venue. |
| `REDIS_URL` | Enables the durable match store + restart recovery + shared idempotency. | Set it + run Redis; a redeploy/crash mid-match then recovers active matches on boot. |
| `CORS_ALLOWED_ORIGINS` | Locks CORS to the portal/TV origins (comma-separated). | Defaults to `*` (dev). Set before launch. |
| `PLAYER_PHONE_PEPPER` | Enables optional phone-based player recovery (ADR 0005). | **Optional, ≥32 bytes.** Without it, phone numbers are never hashed/stored — the QR token is the only identity. The pepper makes the (enumerable) phone space safe to key on; keep it secret + stable (rotating it orphans existing phone links). |
| `DATABASE_URL` | Point at Supabase's **transaction pooler** (`:6543`) at fleet scale (ADR 0007). | Direct Postgres (`:5432`) doesn't scale to many venues. Use the pooler URL from Dashboard → Settings → Database → Connection pooling (Transaction mode). The writer auto-detects `:6543` and disables prepared statements; no code change. `PGBOUNCER_TRANSACTION_MODE=1` forces it if your URL hides the port. |

## 2. Supabase — apply migrations + enable Realtime

These I cannot push to your live project (I won't touch `~/tablewars/.env`
without you). On the Supabase project (`tfctjqjrtjfaduirtcyk`):

1. **Apply the new migrations** (in order):
   - `supabase/migrations/20260605000000_anon_match_token_rls.sql` — anon
     read scoped by signed match token.
   - `supabase/migrations/20260605000001_lobbies_realtime.sql` — lobbies
     table + RLS.
   - `supabase/migrations/20260605000002_player_identity.sql` — players +
     player_secrets + match_pucks.player_id + player_leaderboards + the
     extended final-score trigger + RLS (ADR 0005). Verified end-to-end
     against local Postgres (test_player_identity*, incl. the adversarial
     RLS suite).
   - `supabase/migrations/20260605000003_data_retention.sql` — the
     `purge_old_matches(retention_days)` function + index (ADR 0006).
     Verified against local Postgres (test_data_retention).
   - `supabase/migrations/20260605000004_trivia_content.sql` — the
     `trivia_questions` table + `trivia_content_version()` + RLS (public
     reads active; super_admin writes) + 3 starter questions (ADR 0008).
     Verified against local Postgres (test_trivia_content_db). After
     applying, **load your real question bank** into `trivia_questions`
     (import from the legacy SQLite `trivia_database` or the portal); the box
     syncs it into a local cache on boot. Optionally set `TRIVIA_CACHE_PATH`
     (defaults to `/tmp/tablewars_trivia_cache.json`) to a durable path so
     the cache survives reboots for offline-first cold starts.
   Use the Supabase CLI (`supabase db push`) or paste into the SQL editor.
1b. **Schedule retention** (ADR 0006): the purge function ships but does NOT
   self-schedule. Either enable Supabase **pg_cron** and
   `select cron.schedule('purge-matches','0 4 * * *', $$select purge_old_matches(90)$$);`
   or call `purge_old_matches(...)` from a Flask box maintenance task. Pick a
   window per operator (default 90d raw data; leaderboard aggregates are kept
   forever). There is no undo — export anything you need beyond the window
   first.
2. **Enable Realtime** on the `matches` and `lobbies` tables (Dashboard →
   Database → Replication / Publications → add them to
   `supabase_realtime`). Without this the TV gets no pushes.
3. **Confirm anon grants**: the policies assume `anon`/`authenticated`
   have table-level `SELECT` grants (Supabase's default). If you've
   tightened grants, re-grant `select` on matches/match_pucks/scores/
   leaderboards/lobbies to `anon`.
4. **Re-run the RLS audit against the real project** if you want
   belt-and-suspenders: the suite (`server/tests/test_rls.py`) is verified
   against a local Postgres with a Supabase-auth *shim*. The real
   `auth.jwt()`/`auth.uid()` behave the same, but a live run confirms it.

## 3. TV app (React Native) — build + deploy + verify

Needs Xcode/Android Studio + a device/emulator, which the sandbox doesn't
have.

1. **Verify the match-token Realtime flow live**: with `SUPABASE_JWT_SECRET`
   set, load a TV on a match and confirm it receives snapshot updates (the
   server-minted token + anon RLS path). I verified token minting and the
   RLS policy independently; the live Realtime `setAuth` handshake is the
   one piece only a device can confirm.
2. **RN Sentry** (item 8, RN side — not wired):
   - `npm i @sentry/react-native`
   - `npx @sentry/wizard -i reactNative` (sets up native iOS/Android), or
     follow the manual native steps; `cd ios && pod install`.
   - In `App.tsx`: `import * as Sentry from '@sentry/react-native';
     Sentry.init({ dsn: <DSN>, environment: <env> });` and wrap the root
     with `Sentry.wrap(App)`.
   I left this out of `package.json` so I didn't break your build with an
   unlinked native dep.
3. **Lobby Realtime swap** (deferred half of item 12): the server now
   publishes lobby state to the `lobbies` table, but `useLobbyState` still
   polls. Swapping to Realtime needs a TV **location-token** (a token with
   a `location_id` claim) + the TV knowing its `table_number`. Wire a
   `/location-token` mint + `supabase.realtime.setAuth` + subscribe, like
   `useMatchState`. No regression today — the poll works.
4. **Play Store / Leanback** submission + banner image (original handoff
   step 4).

## 4. Deploy / ops

- **Single runtime worker** (gunicorn `--workers 1`) OR sticky-by-match
  routing. Match state is now serializable + restart-recoverable (set
  `REDIS_URL`), but the per-match *ownership claim* that makes N concurrent
  workers safe isn't wired yet (see `server/runtime/CONTEXT.md`). Don't run
  N workers naively — until ownership lands, two could tick the same match.
  Restart-recovery (redeploy/crash) is covered.
- **Redis**: run one if you enable `RedisIdempotencyCache`/`RedisLock`.
- **TLS at the venue edge**: puck auth raises the floor but tokens ride
  plain HTTP today; terminate TLS so they can't be sniffed/replayed.
- **Backups**: daily `pg_dump` to S3 (Supabase free-tier PITR is limited).
- **Staging Supabase project** + Supabase CLI migration tooling (dev/prod
  currently share one project).

## 5. Not done (code follow-ups — tracked, not manual)

These are remaining engineering tasks (I scoped but didn't implement),
listed so nothing's lost:

- **Question dedup** — needs per-puck `trivia_answers` history plumbed into
  the runtime SpeedPyramid load path.
- **Multi-worker ownership claim** — the last step: wrap per-request match
  processing in the (already-built, tested) `RedisLock` so exactly one
  worker owns a match. Serialization + store + recovery + lock are all
  done. Largely YAGNI given per-venue boxes; do it only if one box must run
  multiple runtime workers.
- **Legacy `app.py` logging sweep** — convert remaining `print()`s.
- **CSRF** — assessed **not applicable**: the app has no session/cookie
  authentication (no `session[...]`, no login), so there are no ambient
  credentials for a cross-site request to abuse, and the state-changing
  routes are JSON APIs called by non-browser clients (pucks, portal). Add
  Flask-WTF `CSRFProtect` (with the `/api/*` blueprints exempted) **only if**
  a cookie-authenticated admin UI is introduced later.
- **Admin endpoint auth (the real gap)** — `/api/admin/*` routes (e.g.
  `POST /api/admin/bars/<slug>/pucks`) currently have **no authentication**.
  Gate them behind an admin token / Supabase-auth `org_admin` check before
  exposing the portal publicly. This is an authz gap surfaced while
  assessing CSRF; it touches the portal (which calls these), so it's
  flagged here rather than changed blind.
- **Deployment story** — Dockerfile audit, production WSGI unit (gunicorn
  `--workers 1` for the runtime). `/api/runtime/health` is now available
  for the load-balancer probe.
- **CI for the portal/legacy app**, mypy, ESLint-in-CI.

- **Activate the local-first TV path (ADR 0004)** — the server side ships
  (the Flask box pushes match state over a LAN SocketIO room; the native TV
  has the full source-selector + seq-reconciliation + cloud fallback). The
  local socket is **dormant until you install the client dep and rebuild
  the TV app**, because adding a native dep + the RN rebuild is your
  environment, not the sandbox's. Until then the TV transparently runs on
  the cloud-Realtime fallback (i.e. today's behaviour), so nothing breaks.
  To activate:
  1. ~~`npm install socket.io-client`~~ — **DONE** (committed to
     `package.json` + `package-lock.json`). socket.io-client is pure JS (no
     native module), so no `pod install` / native linking is needed.
  2. Rebuild/redeploy the TV app's JS bundle (`react-native run-ios` /
     `run-android`, or your TV deploy path) — this is the activation step:
     the next bundle includes the client and the local path goes live.
  3. Set each TV's `API_BASE_URL` (in `~/tablewars/.env` → `src/config.ts`)
     to the venue Flask box's LAN address (DHCP reservation or a `.local`
     hostname), not `localhost`.
  4. Keep the Flask box on gunicorn `--workers 1` and **without
     `--preload`** (ADR 0004: the tick/emit greenlet must spawn post-fork,
     post-gevent-monkey-patch).
  `createLocalSocketSource` already lazy-loads `socket.io-client` and
  degrades to cloud if it's missing, so step 1 is the activation switch.

- **Player-bind front-end (ADR 0005)** — the server side ships: the bind
  endpoint (`POST /api/runtime/match/<id>/bind`), token mint/resolve, the
  `match_pucks.player_id` link, and the `player_leaderboards` trigger are all
  done and tested (incl. real-DB + adversarial RLS). Still UI work, not done:
  1. **TV QR** — render a QR on the TV that deep-links to the phone profile
     with the match/table context (the TV already knows its `match_id`).
  2. **Phone web profile** — a lightweight page where a returning patron is
     auto-identified by their stored token (or a new one is minted), picks
     their seat/colour in the live lobby, and POSTs the bind. This is the
     "pick your colour" step from the ADR; it's the patron-facing surface
     and needs a North Star pass.
  3. **Live name reflection (optional polish)** — reflect a mid-match bind on
     the TV immediately (in-memory participant rename + re-emit a frame).
     Attribution already works without it; this is cosmetic.
  4. **Engagement surfaces** — "you're #3 this week" / personal stats now
     have a data source (`player_leaderboards`, scoped per
     `(player_id, game_id, location_id, period)`); wire them into the TV /
     phone profile when the front-end lands.
