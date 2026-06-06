# Audit Program — make EVERY area bulletproof

**Standing directive (user, 2026-06-06):** every aspect of Table Wars must be
as bulletproof as possible — or more — and must get the same ruthless
adversarial audit + fix treatment that Track A (schema) and Track G (runtime)
already received. "Architecturally sound, no gaps whatsoever across any
aspect." This is a permanent quality bar, not a one-off.

Do NOT declare an area "done/hardened" until it has actually been through the
playbook below.

## The playbook (run per area)

1. **Fan out adversarial review.** Launch parallel review agents, each on an
   independent dimension of the area, each grounded in real `file:line`
   (not memory). Tell them: be ruthless, cite lines, rate severity, give a
   concrete failure/exploit scenario + a specific fix, and also note what's
   genuinely solid. (See `track-a-g-deep-review-2026-06-06.md` for the prompt
   shape that worked.)
2. **Triage + re-grade.** Don't trust agent severities blindly — re-grade
   each finding for *actual* reachability and impact. Drop/​downgrade
   overstated ones; flag findings in our own prior work honestly.
3. **Write the audit doc** under `docs/audit/<area>-<date>.md`: findings by
   tier (Critical/High/Medium/Low), each with file:line + fix, plus a
   "verified solid" list and a "deliberately deferred (with rationale)" list.
4. **Fix in priority order**, each change landing with a **real-flow
   regression test**. Keep CI green (pytest + mypy + jest + tsc + eslint).
   Commit in logical chunks. Push at checkpoints; confirm CI green.
5. **Resolution summary** appended to the audit doc: what's fixed, what's
   deferred and why.

## Area inventory + audit status

| Area | Audited? | Notes |
|---|---|---|
| A — Schema / RLS / multi-tenancy | ✅ done (2026-06-06) | `track-a-g-deep-review-2026-06-06.md` |
| G — Multi-game runtime | ✅ done (2026-06-06) | same doc |
| B — TV app — live web TV (`server/static/games/speed-pyramid`, served at `/tv/speed-pyramid`) | ✅ done (2026-06-06) | `tv-speed-pyramid-web-2026-06-06.md`. ErrorBoundary auto-reload, malformed-reveal guard, TimerBar/ShotClockBar NaN guards. First tests for this app (vitest `lib/num`). Reconnect-resync + CI wiring deferred w/ rationale. |
| B2 — TV app — `TableWarsTV/` (react-native-tvos) | ✅ done (2026-06-06) | `tablewars-tv-2026-06-06.md`. ErrorBoundary (kiosk crash net), SmashView divide-by-zero, CueFlashOverlay tint-as-ref + rapid-cue (deferred from polish), leaderboard unmount guard. matchSource reconciliation verified solid. |
| F1–F4 games — logic (`server/games/*.py`) | 🟡 partial | runtime audit covered disconnect/scoring/serialize; do a dedicated per-game exploit/edge pass |
| F1–F4 games — TV views (`TableWarsTV/src/screens/games/*`) | ⬜ TODO | render robustness vs malformed snapshots, missing fields |
| C — Polish system (cues `runtime/cues.py`, `useCues`, audio, VO `server/voices`, LED) | ✅ done (2026-06-06) | `polish-2026-06-06.md`. Fixed: VO narration cache never invalidated (mis-drove live R027 question substitution) + stalled-narration wedge. Cue dispatch verified solid (agent "CRITICAL"s were unbuilt/non-live/self-retracted). Audio bus + firmware feedback covered in TV/firmware passes. |
| D — Firmware (ESP32 C++, live Speed Pyramid path) | ✅ done (2026-06-06) | `firmware-2026-06-06.md`. Heartbeat/ghost-sweep, WiFi reconnect, consolidated polling, secrets-in-repo, answer-loss, broken prod build env + more. First firmware host-test harness (`testing/firmware/`). Legacy monoliths / OTA / NVS provisioning / TLS deferred with rationale. |
| E — Customer self-serve (attract, onboarding) | ⬜ TODO | mostly unbuilt; audit what exists |
| Portal (Next.js, `portal/`) | ✅ done (2026-06-06) | `portal-2026-06-06.md`. DAL authz guards (layout-only authz → co-located check), security headers, metadata/noindex, .env.example. Anon-key-only + CSRF framework-handled verified solid. Open-signup + email-enum deferred to Supabase dashboard (owner). |
| Legacy Flask stack (`multiplayer_routes`, `trivia_routes`, `tv_game_routes`, `app.py`) | ✅ done (2026-06-06) | `legacy-flask-2026-06-06.md`. Fixed: DEBUG-default RCE, reflected XSS, socket CORS `*`, /api/score validation, SECRET_KEY fallback. No SQLi found (solid). Open game endpoints documented as by-design puck protocol (superseded by Speed Pyramid) — mitigate via network isolation, not per-route auth. First app.py route test. |
| Observability (Sentry/PostHog) | ✅ done (2026-06-06) | `observability-2026-06-06.md`. Fixed Sentry secret/PII leak (frame locals + request bodies + before_send scrub) + Bearer redaction. Log redactor verified solid. Client-side remote capture + PostHog deferred (feature, needs DSN/product decision). |
| Deploy / ops (Dockerfile, systemd, secrets) | ✅ done (2026-06-06) | `deploy-2026-06-06.md`. compose secrets fail-closed, postgres host port removed, no-new-privileges, healthcheck, systemd StartLimit fix, nginx Referrer-Policy. Dockerfile/systemd hardening verified solid. Worker-class unify + nginx rate-limit (NAT'd pucks) deferred w/ rationale. |

## Suggested order (highest risk / leverage first)

1. **Firmware (D)** — hardest to fix after deployment (pucks in the field);
   memory-safety + OTA security bugs are the scariest.
2. **TV app (B) + game TV views** — the customer-facing surface; crashes are
   visible and kill the experience.
3. **Portal (Next.js)** — internet-facing, auth-bearing.
4. **Legacy Flask stack** — still mounted, partially audited.
5. **Polish system (C)**, **self-serve (E)**, **observability** — as each is
   built/wired.

## Conventions that worked (keep them)

- Real-DB tests via `server/tests/pg_harness.py` for anything touching
  Postgres (the gold standard).
- Tests that drive the REAL flow, not re-implementations.
- Honest commit messages tying each fix to its audit finding id.
- One audit doc per area; this file is the index.
