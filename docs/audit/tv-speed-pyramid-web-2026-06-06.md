# TV Audit — Speed Pyramid web TV (2026-06-06)

Area **B — TV app** from `AUDIT-PROGRAM.md`. Ran the standard playbook: 4
parallel adversarial review agents (crash resilience, realtime/socket races,
lifecycle/memory leaks, state-flow/data/perf+a11y), then re-graded every
finding against the real code.

## Scope — which "TV" is live

There are two TV surfaces in the repo:

1. **`server/static/games/speed-pyramid/`** — a React + react-router + Socket.IO
   Vite SPA that Flask serves at **`/tv/speed-pyramid`** (`server/app.py:788`).
   This is the **live bar TV** for the deployed Speed Pyramid product — the
   firmware audited in `firmware-2026-06-06.md` talks to the same server, and
   this app drives the screen. It had **zero tests**.
2. **`TableWarsTV/`** — a separate `react-native-tvos` native client (a
   parallel/next-gen multi-game surface, has some `src/lib` unit tests).

This audit covers **#1 (the live web TV)** — highest leverage (on the bar TV
now, zero tests, coupled to the endpoints just hardened). `TableWarsTV/`
(react-native) is a distinct surface, queued as the next TV pass.

LIVE files audited (everything under `src/` **except `src/dev/`**, which is
`VITE_DEV_TOOLS`-gated and tree-shaken out of prod): `App.tsx`, `main.tsx`, the
8 `screens/*`, `components/*`, `lib/{api,socket,audio}.ts`.

Key context for calibration: this TV runs **UNATTENDED on a bar television for
hours**. A white-screen or a wedged screen stays broken until a human notices —
so "any render throw kills the night" is a High/Critical concern even at low
probability.

---

## Findings by tier (re-graded)

### HIGH

**H1 — No React error boundary: any render throw white-screens the TV until a
human reloads.** `main.tsx` rendered `<App/>` bare inside `<StrictMode>` with no
boundary. React error boundaries are the only thing that turns a render-time
throw into a recoverable state; without one, a single bad access during render
(an unexpected `undefined` field, a malformed payload that reaches render, a bad
animation value) blanks the whole `<Routes>` tree for the rest of the night.
**Fix:** added `components/ErrorBoundary.tsx` wrapping `<App/>` — logs the crash
(console now, Sentry/PostHog hook later) and **auto-reloads after 8s**, so the
SPA boots fresh back to the title screen and the pucks re-pair without anyone
touching the TV. This is the single highest-value fix; it also caps the blast
radius of every other "malformed-data crashes render" finding below.

**H2 — A malformed `reveal` payload throws inside the socket handler and strands
the TV.** `QuestionScreen.onReveal` did `for (const r of p.results)` and
`p.results.every/some` (QuestionScreen.tsx:438,459-461). If a `reveal` event ever
arrives without `results`, the handler throws **before** `scheduleAdvanceToNext
Question()` (line 469) runs — and a throw in a socket event handler is **not**
caught by the ErrorBoundary (boundaries only catch render). The force-reveal
timer was already cleared at the top of the handler, so the TV sits on the
answering screen forever. **Fix:** `const results = Array.isArray(p.results) ?
p.results : []` and use it throughout; the reveal still renders and the advance
still schedules.

### MEDIUM

**M1 — `TimerBar` divide-by-zero blanks the bar.** `pct = (remainingMs /
(durationSec * 1000)) * 100` (TimerBar.tsx:39) yields `NaN%` when `durationSec`
is 0/missing (degenerate `time_limit`), painting an invisible bar, and `pct`
wasn't clamped. **Fix:** extracted `lib/num.ts` `pctRemaining()` (guards
`total <= 0 → 0`, clamps `[0,100]`); TimerBar uses it. Unit-tested.

**M2 — `ShotClockBar` modulo-by-zero + unclamped green zone.** `(elapsed %
cycleMs)/cycleMs` (MinigameScreen.tsx:382) → `NaN` if `cycle_ms` is `0` (the
`?? 3000` default only catches null/undefined), freezing the sweep pointer; and
`greenFrac` was used unclamped so a bad value renders the green zone off the
track (players tap where it's drawn). **Fix:** `safeCycleMs = cycleMs > 0 ?
cycleMs : 3000` and `safeGreenFrac = clamp(greenFrac, 0, 1)` (left + width).

### LOW

**L1 — `question.answers[reveal.correct_answer]`** (QuestionScreen.tsx:711) would
render `undefined` if the server ever sent an invalid letter — cosmetic (`"C ·
undefined"`), not a crash. Covered by H1 if it ever did throw. Left as-is.

**L2 — Deep-link reload mid-countdown** restarts the countdown visually
(CountdownScreen). Self-corrects on the next server event; acceptable for a
kiosk. Noted.

**L3 — A11y/legibility nits** (relying on color for correct/wrong; pair-code
font size). Low priority for a passive display; noted for a polish pass.

---

## Re-graded DOWN / rejected (agent claims that did not survive triage)

- **"CRITICAL: `GlobalLobbyResetListener` re-subscribes every navigate → N
  stacked `lobby_cancelled` listeners → N navigations"** — false. In
  react-router **v7** `useNavigate()` returns a **stable** reference, so the
  `[navigate]` effect runs once. Even if it re-ran, each effect run registers
  and cleans up **its own** `onLobbyCancelled` (matching `on`/`off`), so no
  listener ever leaks. App-level component barely re-renders anyway.
- **"CRITICAL: audio listener leak / 700 orphaned `<audio>` elements /
  50–100 MB over a night"** — false. `audio.ts` caches each sample element once
  (`if (!el)`, line 33) so its 2 listeners are added once per ~15 names; the
  `AudioContext` is a singleton; procedural oscillators self-stop
  (`osc.stop(...)`, line 150) and are GC'd. Narration `new Audio()` objects are
  never attached to the DOM, so nulling the ref makes them GC-eligible —
  `.remove()` would be a no-op. No unbounded growth.
- **"Reveal vs force-reveal race / narration bleed / cross-session events"**
  (claimed risks) — already correctly handled in-code: `onReveal` clears the
  force-reveal timer (415-418); `applyQuestionShown` is idempotent per
  `question.id` (176-179) and guards re-narration via `narratedQidRef`;
  every handler filters on `session_code`; advance is belt-and-suspenders via
  `.finally` (222-227). NB: the agents attributed these to a `regression_log.md`
  — that file does not exist; the `R0xx` notes live inline in the code.
- **"`StrictMode` double-invoke / setInterval stacking in Minigame/Category
  pick"** — false alarm; React guarantees effect cleanup runs before re-run, and
  every interval/rAF here is paired with its clear/cancel.

## Verified solid (keep)

- `App.tsx` `SfxRouteGuard` (stop SFX on every route change) and
  `GlobalLobbyResetListener` (single global reset path, dev-route guarded).
- `QuestionScreen` listener cleanup (named refs + matching `off()`),
  force-reveal/advance belt-and-suspenders, narration timer tracking +
  unmount/reveal cleanup, idempotent question apply, session-code filtering on
  every handler.
- `TimerBar` / `CountUpScore` rAF loops paired with `cancelAnimationFrame`.
- `audio.ts` singleton context, bounded sample cache, `stopAll` on route change.
- `ScoreboardScreen` trusts the server's deterministic `rank`/`is_winner`
  tie-break; 0-player and >4-player layouts handled.
- Phase routing: every `loadQuestion` consumer branches on
  `phase: 'category_pick' | 'minigame'` before touching `question`.

## Deliberately deferred (with rationale)

- **Reconnect state-resync in `QuestionScreen`** — on reconnect the screen
  re-joins the socket room (`onConnect`, line 121) but doesn't re-fetch state, so
  a `reveal`/`question_show` emitted *during* a WiFi outage is missed. In
  practice the screen self-heals via the force-reveal → advance timer chain. A
  naive `loadQuestion` resync is **risky**: `applyQuestionShown` calls
  `setReveal(null)` (line 182) for the same `question.id`, which would wipe an
  active reveal mid-display. A correct resync must diff phase/question-id and
  needs integration testing (React Testing Library, not yet set up). Deferred
  rather than land a risky change in the 830-line hot path.
- **Wiring the new vitest suite into CI** — this web app is not in CI today
  (dist is gitignored/built at deploy; the server is Python) and has
  **pre-existing eslint errors** (`api.ts:13`, `LobbyScreen.tsx:90`,
  `PairScreen.tsx:130`, `dev/usePuckState.ts:587`) plus no committed lockfile.
  Adding a CI job needs a committed lockfile and a lint cleanup first — a
  separate chore. The suite runs locally today (`npm test`).
- **CountUpScore negative clamp, scoreboard multi-winner crown, category emoji
  fallback** — defensive/cosmetic; server never emits these. Noted.
- **`TableWarsTV/` (react-native-tvos)** — a distinct surface; next TV pass.

---

## Resolution summary

**Fixed (verified: `tsc -b` ✓, `eslint` on changed files ✓, `vite build` ✓,
`vitest run` 6/6 ✓):**

- **H1** — `components/ErrorBoundary.tsx` added and wraps `<App/>` in
  `main.tsx`; auto-reloads 8s after any render crash.
- **H2** — `QuestionScreen.onReveal` defaults `results` to `[]` so a malformed
  `reveal` can't throw in the handler and strand the TV.
- **M1** — `lib/num.ts` (`clamp`, `pctRemaining`) extracted + unit-tested;
  `TimerBar` uses `pctRemaining` (no more `NaN%`).
- **M2** — `ShotClockBar` guards `cycleMs <= 0` and clamps `greenFrac` to
  `[0,1]`.
- First **test harness** for this app: vitest + `src/lib/__tests__/num.test.ts`
  (6 tests), `npm test` script.

**Deferred** — reconnect resync, CI wiring, cosmetic guards, `TableWarsTV/`
(rationale above).
</content>
