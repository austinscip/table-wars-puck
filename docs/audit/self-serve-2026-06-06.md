# E — Customer Self-Serve audit (2026-06-06)

Area **E — Customer self-serve (attract, onboarding)** from `AUDIT-PROGRAM.md`
("mostly unbuilt; audit what exists"). A review of the existing self-serve
surface rather than a deep fix pass — there is little built to harden, and what
exists was largely covered in the TV audits.

## What "self-serve" is today

There is **no guided onboarding / tutorial / how-to-play flow**. "Self-serve" is
currently just the **passive attract loop + scan-to-join**:

- **Attract loop** (`TableWarsTV/src/screens/AttractScreen.tsx`): shows a
  rotating top-5 leaderboard (day/week/all-time) when idle, and wakes back to
  the Title screen the instant a lobby/match appears — via a 1s `lobby-state`
  poll AND a Supabase Realtime `matches` channel (belt-and-suspenders).
- **Scan-to-join onboarding** (`components/JoinQrBadge.tsx` + the pairing flow):
  a QR badge to join a live match; the firmware pair-code flow is the primary
  path.
- **Title / leaderboard** surfaces (web TV + TableWarsTV).

## Findings

**No new issues to fix.** The existing surface was already reviewed/hardened in
the TV passes:

- `AttractScreen` — verified solid this pass: the Realtime channel is removed on
  unmount (`supabase.removeChannel`), the breathing-prompt `Animated.loop` and
  the leaderboard rotation are cleaned up, and the dual wake paths
  (poll + realtime) are robust.
- The **leaderboard rotation unmount race** and the **kiosk ErrorBoundary** that
  protect this surface were fixed in `tablewars-tv-2026-06-06.md` (B2).
- `JoinQrBadge` QR generation uses the abort pattern (no setState after unmount)
  — verified in the B2 pass.

## Deferred (genuinely unbuilt — not a bug)

- A real first-time **onboarding / tutorial** ("how to hold the puck, tilt to
  aim, tap to lock"), an attract-mode **call-to-action** beyond the leaderboard,
  and any **customer self-registration** are product features that don't exist
  yet. There is nothing to audit until they're built; flagged here so a future
  build picks up the same hardening bar (kiosk error boundary, timer/animation
  cleanup, Realtime channel teardown) the rest of the TV surface already meets.

## Resolution

No code changes. Area marked audited: the built surface (attract + scan-to-join)
is robust and already covered by the B/B2 fixes; the rest of self-serve is
unbuilt and documented as such.
</content>
