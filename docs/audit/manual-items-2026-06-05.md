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
| `REDIS_URL` | Only if/when you wire the Redis backends (multi-worker). | See §4. |

## 2. Supabase — apply migrations + enable Realtime

These I cannot push to your live project (I won't touch `~/tablewars/.env`
without you). On the Supabase project (`tfctjqjrtjfaduirtcyk`):

1. **Apply the two new migrations** (in order):
   - `supabase/migrations/20260605000000_anon_match_token_rls.sql` — anon
     read scoped by signed match token.
   - `supabase/migrations/20260605000001_lobbies_realtime.sql` — lobbies
     table + RLS.
   Use the Supabase CLI (`supabase db push`) or paste into the SQL editor.
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
  routing until match state is shared (see `server/runtime/CONTEXT.md` —
  the Redis lock/idempotency seams are ready but match *state* still lives
  in one worker). Don't run N workers naively or matches will 404 on the
  wrong worker.
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
- **Multi-worker match state** — serialise `Game` state to Redis +
  reconstruct (the real blocker; coordination seams are ready).
- **Legacy `app.py` logging sweep** — convert remaining `print()`s.
- **CORS/CSRF audit** on Flask for the portal origin.
- **Deployment story** — Dockerfile audit, production WSGI unit, health
  check endpoint.
- **CI for the portal/legacy app**, mypy, ESLint-in-CI.
