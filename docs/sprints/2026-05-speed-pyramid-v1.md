# Sprint PRD — Speed Pyramid v1

**Status:** Draft (pending approval)
**Date:** 2026-05-11
**Owner:** Austin
**Tracker:** TBD — Ralph nano-stories will be added to `prd.json` after approval

## Problem

Earlier Table Wars demos showed AI-slop placeholder graphics and Minecraft-style voxel UI (`docs/adr/0001-quality-bar-and-stack.md`). Bars will not buy or renew a unit that looks like a weekend prototype. The existing `games/trivia-buzzer.html` and `server/templates/trivia_tv.html` use the exact slop aesthetic the owner has rejected (Segoe UI / Arial Black, `#4e54c8 → #8f94fb` and `#1a1a2e → #16213e` linear gradients).

We need one polished trivia game shipped end-to-end as proof the new quality bar is achievable, demoable to a bar owner, and reusable as the framework for every later trivia variant.

## Solution

Build **Speed Pyramid v1** — a single-puck, polished, end-to-end trivia game that uses the existing server-side `SpeedPyramidGame` engine and the existing 67-question database, but with:
- A new Vite + React + Tailwind + shadcn/ui + Framer Motion TV view at `server/static/games/speed-pyramid/`, served by Flask at `/tv/speed-pyramid/<session_code>`
- Locked brand tokens (HQ Trivia / Jackbox aesthetic) consumed via `tokens.json` + `tailwind.config.js`
- A 6-digit pair-code flow (new endpoints `/api/pair/*`) so the TV and puck bind to the same Match
- Puck firmware that does tilt-aim quadrant selection, tilt-dial pair-code entry, and rich LED + buzzer + motor feedback per event

Server-side scoring updates to a 4-tier model with a 0-point floor (no negative points). All audio assets sourced from Pixabay / Freesound CC0 — zero AI-generated content.

## User stories

### Player UX

- **As a player**, I see the bar's TV showing the Speed Pyramid title and a 6-digit pair code, so I know how to start.
- **As a player**, I pick up a puck, hold the button 1s to enter pair mode, then tilt-up / tilt-down to dial each digit and tap to advance, so I bind my puck to that TV's Match.
- **As a player**, after pairing, a 3-2-1 countdown plays with audio + LED ring sweep, so I know the match has started.
- **As a player**, each of 7 questions shows on the TV with 4 answers (A/B/C/D), and the LED ring around the puck depletes from 16 → 0 LEDs over 10s, so I can feel the time pressure.
- **As a player**, I tilt the puck toward one of 4 quadrants to highlight an answer in `--primary` blue, and tap to lock it in.
- **As a player**, on a correct answer the puck flashes `--correct` gold + buzzes a ding + motor pulses 200ms; on wrong, `--wrong` red + descending buzzer thud + motor pulse 500ms. The TV reveals the correct answer for 2s before moving on.
- **As a player**, after 7 questions, the TV reveals my final score with a staggered count-up animation + crescendo SFX.
- **As a player**, I can tap the puck for "Play Again" (resets to Q1, same puck) or hold 3s for "New Player" (returns to pair screen).

### Bar operator UX

- **As a bar operator**, I open `https://<railway-url>/tv/speed-pyramid` on any smart TV and the title screen + pair code appears with no on-site host box.
- **As a bar operator**, I can reset the TV (refresh) and the next player can pair fresh.

## Architecture

```
[Puck (ESP32)]                          [Flask + SocketIO]                    [TV (smart TV browser)]
     |                                          |                                       |
     |  POST /api/pair/request (puck_id) ------>|                                       |
     |<------ 200 {pair_code, expires_at} ------|                                       |
     |                                          |                                       |
     |                                          |<--- GET /tv/speed-pyramid -----------|
     |                                          |---- 200 (Vite-built React app) ------>|
     |                                          |                                       |
     |                                          |<--- WS connect, subscribe pair_code -|
     |                                          |                                       |
     |  POST /api/pair/confirm (code) --------->|                                       |
     |<------ 200 {session_code} ---------------|                                       |
     |                                          |--- WS emit 'paired' -----------------> |
     |                                          |                                       |
     |  POST /api/trivia/start ---------------->|                                       |
     |                                          |--- WS emit 'match_started' ----------> |
     |  GET /api/trivia/question/<session> ---->|                                       |
     |                                          |--- WS emit 'question_show' ----------> |
     |  POST /api/trivia/answer (A/B/C/D, t_ms)>|                                       |
     |                                          |--- WS emit 'answer_locked' ----------> |
     |<--- 200 {is_correct, points, tier} ------|--- WS emit 'reveal' -----------------> |
     |                                          |                                       |
     |  POST /api/trivia/next-round ----------->|                                       |
     |                                          | ... loops 7 times ...                 |
     |                                          |--- WS emit 'match_ended' ------------> |
```

- **State authority:** Flask. `trivia_sessions` table + in-memory `SpeedPyramidGame` instance keyed by `session_code`.
- **Realtime:** Flask-SocketIO. Trivia gets new events: `question_show`, `answer_locked`, `reveal`, `match_started`, `match_ended`, `pair_dial_progress`.
- **Puck transport:** HTTP POST for inputs (already used by existing `/api/trivia/answer`). WS subscribe optional but not required for v1.
- **TV transport:** WS subscribe to `pair_code` channel for all events.

## Locked design

### Brand tokens
See `CONTEXT.md` § "Locked brand tokens (web)". Palette: `#0A0E1A` bg, `#3B82F6` primary, `#EC4899` accent, `#FBBF24` correct, `#EF4444` wrong, `#F8FAFC` text. Fonts: Anton (display) / Inter (body) / JetBrains Mono (scores). Motion: overshoot ease at 400ms reveals, 150ms snaps.

### Mechanics
- 7 questions, difficulty curve: Q1-Q2 easy, Q3-Q5 medium, Q6-Q7 hard
- Time limit: 10 seconds per question
- **Scoring (server update required):**
  - 0–3s correct = 1000pts (LEGENDARY)
  - 3–6s correct = 500pts (EXPERT)
  - 6–10s correct = 200pts (AVERAGE)
  - Wrong or timeout = 0pts
- Server reveals correct answer for 2 seconds before next question
- Match end: scoreboard reveal with staggered count-up + crescendo

### Puck input
- **In-game:** tilt-up = A, tilt-right = B, tilt-down = C, tilt-left = D. Tap = lock current quadrant. Re-tilt before tap to change selection.
- **Pair-code entry:** hold button 1s → enter pair mode. LED ring shows current digit 0–9 as a number-dial. Tilt-up = +1, tilt-down = −1 (loops 0→9). Tap = lock current digit, advance. After 6th digit auto-submits.

### Puck feedback
| Event | LED | Motor | Buzzer |
|---|---|---|---|
| Tilt-aim | Light the 4 LEDs in the current quadrant in `PALETTE_PRIMARY` | — | — |
| Timer tick | Ring depletes 16 → 0 over 10s in `PALETTE_ACCENT` | — | Soft 800Hz tick last 3s, last-second ascending |
| Lock-in | Full ring flash `PALETTE_PRIMARY` 150ms | 80ms pulse | 1.2kHz beep 80ms |
| Correct | Full ring pulse `PALETTE_CORRECT` 600ms | 200ms pulse | Ding-up 700→1400Hz over 250ms |
| Wrong | Full ring flash `PALETTE_WRONG` 400ms | 500ms pulse | Thud 200→100Hz over 300ms |
| Match end | Rainbow sweep `PALETTE_VICTORY` 2s | 100ms × 3 with 80ms gaps | Crescendo C4→C6 |
| Pair mode | Single LED rotating slowly in `PALETTE_HOST` | — | — |
| Pair confirmed | Full ring `PALETTE_CORRECT` 1s | 200ms pulse | Ding |

### TV audio
- Bed loop (tense low pad, CC0 from Pixabay) during questions
- Tick-tick countdown SFX in last 3s
- Lock-in SFX (Jackbox-style ding-up sweep)
- Correct SFX (ascending bell)
- Wrong SFX (descending thud)
- Reveal stinger
- Scoreboard bed (different from question bed) during match end

### Match flow
1. **Title screen:** "SPEED PYRAMID" in Anton display, motion-typed in. Pair code shown. "Hold puck button to pair."
2. **Pair-dial:** TV mirrors digit-by-digit dial as puck reports `pair_dial_progress`. On 6th digit submit, both confirm.
3. **Ready countdown:** "GET READY" → 3 → 2 → 1 → "GO!" with LED ring sweep + countdown SFX.
4. **Question rounds (×7):** Question card with Q text in Anton, 4 answer pills with letter prefixes (A/B/C/D), LED-style timer bar. Lock-in revealed answer pill highlight. 2s reveal of correct answer with `--correct` halo. Score updates in JetBrains Mono numerals with count-up.
5. **Scoreboard reveal:** "MATCH COMPLETE" → final score staggered count-up + tier label (LEGENDARY / EXPERT / AVERAGE based on average). "Play Again" / "New Player" prompts.

### North Star reference
- HQ Trivia question screen. Reference image to be committed at `docs/north-star/speed-pyramid-q-screen.png` before the polish gate. Locked in `AGENTS.md` Discipline gate.

## Server changes

1. **`server/trivia_game_engines.py:299-327`** — update `SpeedPyramidGame.calculate_points` to 4-tier 0-floor:
   - 0–3000ms: 1000 (LEGENDARY)
   - 3000–6000ms: 500 (EXPERT)
   - 6000–10000ms: 200 (AVERAGE)
   - Else: 0 (TIMEOUT)
2. **New `server/pair_routes.py`** — endpoints:
   - `POST /api/pair/request` — body `{puck_id}` → response `{pair_code: 6-digit, expires_at}`
   - `POST /api/pair/dial` — body `{puck_id, digit_index, digit}` → response `{accepted: bool}` + emits `pair_dial_progress` to the matching session
   - `POST /api/pair/confirm` — body `{puck_id, code}` → response `{session_code}` + emits `paired` to TV
3. **`server/app.py`** — emit new socketio events: `question_show`, `answer_locked`, `reveal`, `match_started`, `match_ended`, `pair_dial_progress`, `paired`
4. **`server/templates/`** — no changes to existing trivia_tv.html; add a thin Jinja shell that mounts the Vite bundle (Flask route `/tv/speed-pyramid/<session_code>`)

## Frontend changes (new)

`server/static/games/speed-pyramid/`:
- Vite + React + TypeScript + Tailwind + shadcn/ui + Framer Motion + socket.io-client
- Routes (single-page): `/pair` → `/countdown` → `/question` → `/reveal` → `/scoreboard`
- Component library: `<QuestionCard>`, `<AnswerPill>`, `<TimerBar>`, `<PairCodeDisplay>`, `<DigitDial>`, `<Scoreboard>`, `<TierBadge>`
- Tokens consumed via `tokens.json` → Tailwind theme
- Sounds preloaded from `static/games/speed-pyramid/audio/`

## Firmware changes (new)

`src/` (Rev A pins per current firmware: BUZZER=15, BUTTON=27, LED=23):
- New `src/hal/` headers (`led.h`, `imu.h`, `buzzer.h`, `motor.h`, `button.h`, `comms.h`, `storage.h`, `calibration.h`) — extract from `main_tablewars.h` lazily, only as needed for Speed Pyramid
- New `src/games/g_speed_pyramid.h` with `SpeedPyramidGame::setup() / loop() / handleEvent()`
- Update `src/main.cpp` to a thin menu launcher that boots into Speed Pyramid by default for sprint v1
- Wire HTTP POST inputs to existing Flask routes
- LED palettes locked in `hal/led.h`: `PALETTE_PRIMARY`, `PALETTE_ACCENT`, `PALETTE_CORRECT`, `PALETTE_WRONG`, `PALETTE_VICTORY`, `PALETTE_HOST`

## Audio asset list

To source from Pixabay / Freesound CC0 and commit to `server/static/games/speed-pyramid/audio/`:
- `bed_question.mp3` — tense low pad loop, ~30s
- `bed_scoreboard.mp3` — celebratory bed, ~20s
- `sfx_tick.mp3` — soft 800Hz tick
- `sfx_tick_final.mp3` — ascending last-second tick
- `sfx_lock.mp3` — Jackbox-style ding-up sweep
- `sfx_correct.mp3` — ascending bell
- `sfx_wrong.mp3` — descending thud
- `sfx_reveal.mp3` — stinger
- `sfx_match_end.mp3` — crescendo

Each gets a license entry in `docs/assets/LICENSES.md`.

## Out of scope (explicit)

- **Multiplayer.** Multi-puck Speed Pyramid is next sprint. v1 is single-puck.
- **Leaderboard UI.** Score writes go to existing leaderboard DB, but no leaderboard rendering this sprint.
- **Replay / archived matches.** Each match is independent.
- **Custom question authoring.** Use the existing 67 questions.
- **Phone companion app.** No mobile app changes.
- **Vercel / Next.js refactor.** Stays on Flask + Vite-built static.
- **Rev B firmware port.** Sprint runs on Rev A pins. Rev B port is a separate sprint (mostly a HAL change + pin map remap).
- **Calibration mode.** Defaults from plan are baked in for v1; tuning UI is a separate sprint.

## Acceptance criteria

A bar owner can:
1. Open `https://<railway-url>/tv/speed-pyramid` on a real smart TV. Title screen + pair code appear without any setup.
2. Pick up an idle puck. Hold button 1s. Dial the 6-digit code via tilt + tap. Puck and TV both confirm pairing.
3. Play 7 questions. Each shows on the TV with brand-correct styling. Puck LED ring depletes as the timer runs. Tilt-aim works for A/B/C/D. Tap locks the answer. Speed tier appears correctly.
4. See a final scoreboard with motion-typed count-up.
5. Tap "Play Again" or hold 3s for "New Player".
6. The whole thing looks professionally designed when screenshotted next to an HQ Trivia frame (see `docs/north-star/`).

A second pass with the polish gate:
- No Segoe UI / Verdana / Tahoma / Arial Black anywhere
- No generic CSS linear-gradients outside of the locked palette
- No AI-generated images or sounds
- All audio assets have license entries in `docs/assets/LICENSES.md`
- Motion uses Framer Motion eases, not raw CSS transitions for game-feel beats
- LED code uses named palettes from `hal/led.h`, no raw `CRGB(...)` literals in `g_speed_pyramid.h`

## Verification plan

- **Local dev:** `cd server && python app.py`, separately `cd server/static/games/speed-pyramid && npm run dev` (Vite). Open `http://localhost:5001/tv/speed-pyramid` on desktop, simulate puck via existing `test_puck_simulator.html` or a real puck on WiFi.
- **Bar smoke test:** Deploy via existing Railway flow. Open Railway URL on actual smart TV. Play full match with real puck on a phone-hotspot WiFi.
- **Polish gate:** Side-by-side screenshot vs. HQ Trivia question screen frame in `docs/north-star/`.

## Open follow-ups (not blocking v1)

- ADR-0003 (smart-TV-direct-browse on Vercel) — defer
- ADR-0004 (Rev A / Rev B firmware coexistence) — write before Rev B port sprint
- Speed Pyramid v2 (multi-puck) — next sprint
