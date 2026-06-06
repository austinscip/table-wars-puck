# TableWarsTV (B2) Audit (2026-06-06)

Area **B2 — `TableWarsTV`** from `AUDIT-PROGRAM.md` — the react-native-tvos
(Android TV / tvOS) native client. NOTE: this is the **next-gen / parallel** TV
surface, NOT the live bar TV (that's the speed-pyramid web app, audited
separately). It runs unattended on a TV, so the kiosk-crash calibration from the
web-TV audit applies. Also lands the cue-client items deferred from the polish
audit.

Ran one focused adversarial agent (screens + game-view render/lifecycle) plus a
direct read of the data layer (`matchSource`, `useMatchState`, `leaderboard`,
`CueFlashOverlay`), then re-graded.

## Findings by tier (re-graded)

### HIGH

**H1 — No error boundary: any render throw blanks the TV until power-cycle.**
`App.tsx` rendered the navigator bare. The slug dispatcher (`games/index.tsx`)
guards a malformed TOP-LEVEL snapshot (Fallback), but the per-game views cast
the snapshot and read nested fields that throw on a partial frame — e.g.
`SpeedPyramidView.tsx:18` `Object.entries(snapshot.scores)` (throws if `scores`
is absent), `SmashView.tsx:14` destructuring `snapshot.arena.x` (throws if
`arena` absent), `*.fighters.map` / `*.players.map`. A mid-match reconnect
delivering a partial frame → white screen for the rest of the night. **Fixed:**
added `components/ErrorBoundary.tsx` wrapping the navigator — logs the crash and
**auto-recovers after 6s** by re-rendering (by then the next snapshot has
usually replaced the bad frame; a persistent bad frame just re-shows the card on
the same cadence, no tight loop).

### MEDIUM

**M1 — `SmashView` divide-by-zero → off-screen fighters.** `xSpan =
arenaXMax - arenaXMin` / `ySpan = …` (SmashView.tsx:16-17) are denominators for
each fighter's `left`/`bottom` percentage. A degenerate arena (`min === max`)
makes them `0` → `Infinity%`, throwing fighters off-screen. This renders
silently (no throw → the ErrorBoundary won't catch it). **Fixed:** `|| 1` guard
on both spans.

**M2 — `CueFlashOverlay` flashed with the wrong colour.** `tint` was a `useRef`
mutated in the cue handler, but a ref mutation doesn't re-render — so the
overlay painted with the *previous* cue's colour until some unrelated render
happened (CueFlashOverlay.tsx:31,37,62). **Fixed:** `tint` is now `useState`
(setting it re-renders with the correct colour), and `opacity.stopAnimation()`
before each flash so rapid back-to-back cues each get a clean full flash rather
than stacking partially-faded animations. (This is the cue-overlay item deferred
from `polish-2026-06-06.md`.)

### LOW

**L1 — `useLeaderboardRotation` could setState after unmount.** The auto-fetch
effect (`leaderboard.ts:94-96`) awaited a Supabase query then `setRows`/
`setLoading` with no mounted guard, so a fetch resolving after the attract
screen unmounts/rotates warns + leaks. **Fixed:** the effect now inlines the
fetch with an `active` flag and bails on the stale resolve.

---

## Re-graded DOWN / rejected

- **"Double-fetch every 12s on the leaderboard rotation"** (claimed MEDIUM,
  HIGH likelihood) — false. The `setInterval` only bumps `periodIndex`; the
  `period` change recreates `refetch` and the effect runs it ONCE. One fetch per
  rotation, not two. (The real issue was the unmount race, L1.)
- **"Unsafe type casting is itself the bug"** — the casting is fine; the actual
  risk is the unguarded nested-field access on a partial frame, which the
  ErrorBoundary (H1) now contains. Per-view shape validation in the dispatcher
  is reasonable defense-in-depth but lower priority once the boundary exists;
  deferred.

## Verified solid (keep)

- **`matchSource` reconciliation reducer** — pure, exhaustively unit-tested
  (`matchSource.test.ts`): local-first authority, monotonic `snapshot_seq`
  failover guard (never paints an older frame), keeps the last snapshot on a
  status-only frame so a live view never blanks. Genuinely robust.
- **`GameViewDispatcher`** guards a non-object / unknown-slug snapshot
  (Fallback).
- **`CueDispatcher`** (cues.ts) — monotonic-seq dedup, channel fan-out, reset on
  match change; tested (`cues.test.ts`).
- **`BreathingDots` / `AttractScreen` animations, `JoinQrBadge` abort pattern,
  navigation cleanup** — timers/animations cleaned up on unmount (agent
  confirmed).

## Deliberately deferred (with rationale)

- **Per-game-view shape validation in the dispatcher** — defense-in-depth now
  that the ErrorBoundary contains the white-screen; nice-to-have, low priority.
- **RN component-test infra (RTL-native)** — TableWarsTV's jest only covers
  `src/lib` (pure logic) today; component tests for the boundary/overlay are a
  separate harness task. These fixes are verified by `tsc`/`eslint` + the
  existing lib tests staying green.
- The remaining speculative cue-client nits from the polish audit
  (`channels=[]` semantics, payload JSON guard) — not reachable by any current
  game; revisit if a game emits them.

---

## Resolution summary

**Fixed (verified: `tsc --noEmit` clean, `eslint .` clean, `jest src/lib`
19/19):**

- **H1** — `components/ErrorBoundary.tsx` wraps the navigator in `App.tsx`
  (auto-recovers 6s after a render crash).
- **M1** — `SmashView` arena-span `|| 1` divide-by-zero guard.
- **M2** — `CueFlashOverlay` `tint` ref → state (correct flash colour) +
  `stopAnimation` for clean rapid re-flashes.
- **L1** — `useLeaderboardRotation` unmount guard.

**Deferred** — dispatcher shape guards, RN component-test infra, unreachable
cue-client nits (rationale above).
</content>
