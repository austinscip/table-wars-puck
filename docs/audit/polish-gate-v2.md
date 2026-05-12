# Polish gate audit — Speed Pyramid v2 (multiplayer)

**Date:** 2026-05-12
**Build:** post Slice 2D (commit `68bcd1b`)
**Auditor:** code-side review against the Jackbox / HQ Trivia north-star, multiplayer surfaces

## Compared against

- **HQ Trivia** lobby + question screen — single bold question, vivid color-coded answer pills, lobby avatars stacked on a dark bg.
- **Jackbox** (Trivia Murder Party, Quiplash, Fibbage) — vertical right-rail player list with color-coded squares + names, theatrical answer reveals, tier-colored point deltas.
- **Kahoot multiplayer** — colored player chips that flip to a check / X on reveal; live total beside each row.
- **Bar Rescue / sports-bar leaderboards** — bold display type, neon highlights against dark bg, crown / glow on the leader.

## ✅ What ships at or above bar — keep as-is

| Surface | Notes |
|---|---|
| **Per-puck identity palette** | 8-color palette mirrored across server (`PUCK_COLORS` in `pair_routes.py`) and CSS (`--color-puck-1..8` in `index.css`). Single source-of-truth; if anything is off in production it's a server/CSS sync bug, not a per-screen drift. |
| **Pair flow → Lobby → Match flow** | Pair code dial (host only, joiner just sees code) → Lobby with live avatar pop-in → host TAP to start. No throw-away screens. |
| **LobbyScreen joins** | New player avatars animate in on `player_joined` socket event. Color and number both shown — robust to colorblind viewing. |
| **QuestionScreen right-rail** | Vertical sidebar with one row per puck, colored circle + Puck N + state label ("…", "LOCKED", "LEGENDARY") + cumulative score. Clamped width 14rem–22vw–22rem so it doesn't squeeze the question on narrow TVs. |
| **Reveal state per lane** | At reveal time, the correct pill is gold, any pill someone picked wrongly is red, others dim — same affordance HQ Trivia uses. Lane label shows the tier badge color (LEGENDARY=gold, EXPERT=blue, AVERAGE=pink, TIMEOUT=dim, WRONG=red). |
| **Force-reveal on timeout** | Frontend schedules `/api/sp/force-reveal` at `time_limit + 800ms`. Server backfills TIMEOUT for any silent puck so the round always closes — no waiting-on-a-disconnected-puck stall. |
| **Scoreboard winner highlight** | Top row gets crown glyph + gold border + 60px gold-shadow glow. Crown only shown if total > 0 (no crown on a 0–0 tie). Per-row colored disc keeps identity visible at the final tally. |

## ⚠️ Open items — for V3 or fast follow

| Item | Notes |
|---|---|
| **Pre-roll countdown for the lobby start** | Host taps to start, but there's no "3-2-1" between LobbyScreen and the first question. Adding a 2-3s countdown card gives latecomers a chance to see the question is about to load and lets the TV transition feel deliberate. |
| **Inter-question score deltas** | Right-rail shows cumulative total but not the points-earned-this-round delta. Jackbox flashes "+500" floating up from the row on reveal. Cheap motion win. |
| **Lobby avatars > 4 pucks** | Currently the avatars just stack horizontally — wraps fine for ≤4, ≥5 starts running off. Vertical stack at >4 or grid at >6 would scale better. |
| **Sidebar at 7-8 pucks** | 8 rows fit at clamp(22vw) on a 1080p TV but get cramped. Could shrink each row's score type at >6 players. Not blocking at 2-4 (the realistic-table case). |
| **Late-joiner UX** | Right now, if a puck pairs after the host has tapped Start, the server returns `409 already started`. The puck just bounces. A "joining as spectator next round" path is a future feature — defer until we see it in the wild. |
| **Loser graceful-out** | Eliminated/0-point pucks still appear in the sidebar through the whole match. That's correct for trivia (everyone plays every round), but if we add a "last puck standing" mode later we'll need a `state: out` for the lane. |
| **Color-blind verification** | The blue/pink/cyan trio could be tight for deuteranopia. The puck_id digit inside the circle is the safety net — verify on real hardware with a colorblind sim filter before any commercial install. |
| **Audio cues per-puck** | All players hear the same reveal stinger. Differentiating per-puck (e.g. their own "you got it" chime) is a Sprint 3+ idea once we have CC0 SFX sourced. |

## 🎯 Multiplayer-specific north-star checks

Each line is a side-by-side question against a reference; ✅ = holds up, ⚠ = behind, ✘ = ship-blocker.

| Check | vs HQ Trivia | vs Jackbox |
|---|---|---|
| Lobby establishes player identity before the round starts | ✅ | ✅ |
| Players can see who they're playing against during the round | ✅ (sidebar) | ✅ (sidebar) |
| Reveal call-out names each player's outcome distinctly | ✅ (per-lane tier badge) | ✅ |
| Score deltas legible at reveal | ⚠ (only cumulative shown) | ⚠ (only cumulative shown) |
| Leader visually distinct in final tally | ✅ (crown + glow) | ✅ |
| Lobby code displayed boldly + persistently | ✅ (host) | n/a (Jackbox uses phone, not pairing code) |
| Color identity holds from lobby → match → scoreboard | ✅ (server-driven, no drift) | ✅ |

## 🎧 Audio shopping list — still open from v1.1

Carried over from `polish-gate-v1.1.md` § Audio shopping list. The sample-first / procedural-fallback architecture in `audio.ts` means dropping MP3s into `dist/assets/audio/` lights them up with no code change. Add a row to `docs/assets/LICENSES.md` per file adopted.

## Verdict

**Speed Pyramid v2 multiplayer = bar-shippable for 2–4 pucks.** The lobby → match → reveal → scoreboard chain holds up next to HQ Trivia and Jackbox reference frames. Color identity is consistent end-to-end thanks to the server-owned palette.

**Open items are quality-of-life, not quality-of-bar.** Per-round +N score deltas and a pre-roll countdown are the two follow-ups that would most improve perceived polish. Both are < 1 day of work each.

**One unknown remains: full-flow 2-puck verification on real hardware.** Code-side review only covers the rendering; we won't know reveal-on-last-answer race conditions or sidebar layout on a TV until we play it. Reserve a slot in Sprint 2E for the hardware shakedown.

## Engineering polish that landed in v2

- Server lobby model with per-session SP state and `expected_pucks` lock-in at match-start (no late joiners corrupt the round).
- `/api/sp/answer` records per-puck per-round answers + auto-emits reveal on full set, or backfills TIMEOUT on `/api/sp/force-reveal`.
- Per-puck cumulative scores tracked in server state and broadcast in the `reveal` payload.
- Frontend sidebar (`PlayerLane`) state-machine handles preview/locked/reveal transitions per puck independently — no cross-talk.
- `--color-puck-1..8` tokens added to `@theme`, mirroring server `PUCK_COLORS`.
- ScoreboardScreen gains colored puck discs + winner crown/glow.
- Firmware `_post_answer` switched to `/api/sp/answer` (lobby-aware path) — same body shape, no Rev B reflash logistics change.
