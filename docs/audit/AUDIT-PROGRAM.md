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
| B2 — TV app — `TableWarsTV/` (react-native-tvos) | ⬜ TODO | distinct native surface (the live TV is the web app above). state mgmt, reconnection, error handling, memory leaks, perf, a11y. `src/lib` partly unit-tested. |
| F1–F4 games — logic (`server/games/*.py`) | 🟡 partial | runtime audit covered disconnect/scoring/serialize; do a dedicated per-game exploit/edge pass |
| F1–F4 games — TV views (`TableWarsTV/src/screens/games/*`) | ⬜ TODO | render robustness vs malformed snapshots, missing fields |
| C — Polish system (cues `runtime/cues.py`, `useCues`, audio, VO `server/voices`, LED) | ⬜ TODO | cue ordering/dispatch, audio pipeline, asset handling |
| D — Firmware (ESP32 C++, live Speed Pyramid path) | ✅ done (2026-06-06) | `firmware-2026-06-06.md`. Heartbeat/ghost-sweep, WiFi reconnect, consolidated polling, secrets-in-repo, answer-loss, broken prod build env + more. First firmware host-test harness (`testing/firmware/`). Legacy monoliths / OTA / NVS provisioning / TLS deferred with rationale. |
| E — Customer self-serve (attract, onboarding) | ⬜ TODO | mostly unbuilt; audit what exists |
| Portal (Next.js, `portal/`) | ⬜ TODO | auth, RLS reliance, XSS, server actions, secrets |
| Legacy Flask stack (`multiplayer_routes`, `trivia_routes`, `tv_game_routes`, `app.py`) | ⬜ TODO | older code still mounted; admin auth gate added but not fully audited |
| Observability (Sentry/PostHog) | ⬜ TODO | barely wired; audit + complete |
| Deploy / ops (Dockerfile, systemd, secrets) | 🟡 partial | hardened during runtime work; do a dedicated pass |

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
