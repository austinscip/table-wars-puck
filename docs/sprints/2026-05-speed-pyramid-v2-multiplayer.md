# Sprint PRD — Speed Pyramid v2 (Multiplayer)

**Status:** Draft (pending approval)
**Date:** 2026-05-12
**Owner:** Austin
**Builds on:** v1.1 (commit `HEAD` — hardware-verified end-to-end, polished)

## Problem

Speed Pyramid v1 is solo-play only. Bars are social — a one-player game on the TV is dead air. The whole point of pucks-on-the-table is multiple people at the same table competing live. v2 makes that real: 2-8 pucks join the same match, see the same questions, race against each other for the speed-tier high score.

## Solution

HQ Trivia-style multiplayer: all players see the same question simultaneously, each player has their own puck and their own answer, scores update per-player, single shared screen.

### Decision summary (locked via grilling session)

| Question | Decision |
|---|---|
| Multiplayer model | HQ Trivia: everyone answers the same question |
| Player count | Variable 2-8; engine scales |
| Lobby | One shared 6-digit code; all pucks dial it to join |
| Dial UI | Player 1 sees full live mirror (as today); subsequent pucks dial blind, trusting their puck LED, then pop into Joined-Players strip on confirm |
| Match start | Host puck (Player 1) **taps button** in lobby to start |
| Color identity | Pre-assigned by `PUCK_ID` build flag — 1=blue, 2=pink, 3=gold, 4=green, 5=purple, 6=orange, 7=cyan, 8=red |
| Round end | First of: all connected pucks answered OR 10-second timer expired |
| In-match layout | Vertical sidebar (right side) with per-player leaderboard rows |

## Architecture

### Server-side state model

A new module-level `_LOBBIES` dict in `pair_routes.py`:

```python
_LOBBIES: dict[str, dict] = {}
# Keyed by lobby_code (6-digit). Value:
# {
#   "host_puck_id": int,
#   "session_code": str | None,   # set after host starts
#   "started": bool,
#   "players": dict[int, dict],   # puck_id -> {"color": str, "joined_at": float}
#   "expires_at": float,
# }
```

Only ONE active lobby at a time (per server) — simplifies UX. Once host starts, lobby is "in match" and rejects new joins. After match completes, lobby is cleared.

### Pair-request flow change

```
First puck POST /api/pair/request {puck_id:1}
  -> server creates _LOBBIES[code] with host=1, players={1: {color:"blue",...}}
  -> emits "pair_started" {lobby_code: code, players: [{puck_id:1, color:"blue"}]}
  -> response: {pair_code: code, role: "host"}

Player 2 puck POST /api/pair/request {puck_id:2}
  -> server sees active lobby — returns same lobby code; does NOT add puck yet
  -> emits "pair_started_again" or just lets puck dial
  -> response: {pair_code: code, role: "joiner"}

Player 2 dials code on puck (no mirror on TV).

Player 2 POST /api/pair/confirm {puck_id:2, code:NNNNNN}
  -> server validates code matches lobby
  -> adds puck 2 to lobby.players with color="pink"
  -> emits "player_joined" {puck_id:2, color:"pink", players: [...]}

Host (Puck 1) taps button in lobby
  -> puck POST /api/pair/start {puck_id:1}
  -> server validates puck_id is host
  -> creates trivia session via create_trivia_session
  -> adds all lobby.players to session via add_player_to_session
  -> sets lobby.started=true, lobby.session_code=session_code
  -> emits "match_started" {session_code}
```

### In-match flow (per round)

Largely the same as v1 single-puck, but every event is now multi-player:

- Browser at /question/:session_code calls `/api/sp/load-question` — server picks question, emits `question_show` to all players in the lobby (the room is now keyed by session_code, with multiple sockets joined).
- Each puck independently polls `/api/sp/current-question/<session_code>` — detects the active question, transitions to IN_GAME_ANSWERING.
- Each puck's tilt-aim broadcasts `/api/trivia/answer-preview` with their `puck_id`. Server emits `answer_preview` to the room.
- TV sidebar updates the relevant player's row to show "aiming: B" (color-coded).
- Each puck's tap submits `/api/trivia/answer` with their `puck_id`. Server scores it, emits `answer_locked` then (after all-locked-or-timer) `reveal` with per-player results.
- Reveal: TV shows correct answer pill in gold, each player's locked answer dimmed if wrong with their color tint, sidebar shows per-player tier badges + score deltas.
- Loop for 7 questions, scoreboard at end with full standings.

### Color palette (firmware + frontend share)

```
Puck 1 = #3B82F6 blue       (--primary)
Puck 2 = #EC4899 pink       (--accent)
Puck 3 = #FBBF24 gold       (--correct)
Puck 4 = #10B981 green
Puck 5 = #A855F7 purple
Puck 6 = #F97316 orange
Puck 7 = #06B6D4 cyan
Puck 8 = #EF4444 red        (--wrong)
```

Add as new tokens in `src/index.css` `@theme` block: `--color-puck-1` through `--color-puck-8`.

## User stories

### Operator UX
- As the bar operator I open `http://localhost:5001/tv/speed-pyramid` on the TV. Title screen. Same as v1.

### Player UX
- As Player 1 I hold my puck's button. TV auto-advances to the pair screen with a 6-digit code AND a "Players: 1 joined" indicator below.
- As Player 1 I dial the 6 digits with the live "Your Input" mirror (same as v1). My puck LED shows my color (blue). After my 6th tap, my puck plays the gold flash + happy beep. TV updates: "Players: 1 joined" → "Players: 1 joined ✓ HOST · Puck 1 [blue]". TV shows a "Hold your puck button to start" prompt for me, the host.
- As Player 2 I hold my puck button. My puck flashes briefly to indicate join attempt. The TV does NOT switch screens (it's still showing the lobby) but adds a small indicator "Player 2 dialing…". My puck LED shows my color (pink) and goes into the dial-digit display. I dial blind — watching my puck's LED — to the 6-digit code still visible on the TV.
- As Player 2 after my 6th tap, my puck plays the join-confirm feedback. TV adds "Puck 2 [pink]" to the joined players strip.
- As the host (Player 1), once I see all my friends are paired, I **tap** my puck button. TV transitions to the 3-2-1 countdown.
- As any player during a question, I tilt my puck to aim. The on-screen sidebar row for my color updates in real time to show "aiming: A/B/C/D". I tap to lock. My sidebar row shows my locked answer.
- As a player on reveal, I see the correct answer pill highlighted gold. My sidebar row shows my tier badge (LEGENDARY/EXPERT/AVERAGE/TIMEOUT) + my score delta + my new total.
- As any player after 7 questions, I see the final scoreboard sorted by total score. Winner gets a brief crown animation. Tap = Play Again (same lobby), Hold 3s = New Players (back to title).

## Sliced delivery

5 vertical slices, same shape as v1's 1A-1E.

### Slice 2A — Server lobby model + multi-puck pair endpoints
- New `_LOBBIES` state in `pair_routes.py`
- `/api/pair/request` returns lobby code + role
- `/api/pair/confirm` joins puck to lobby (creates lobby if first; adds player if existing)
- New `/api/pair/start` host-only endpoint
- Emit events: `pair_started`, `player_joined`, `match_started`
- Curl-test the full pair-multiple-pucks-then-start flow

### Slice 2B — Frontend Lobby screen + multi-player pair UI
- Add `LobbyScreen` at `/lobby/:lobby_code`
- Player-1-first detection in `PairScreen` (don't auto-navigate to countdown; wait for `match_started`)
- Joined-players strip component (color circles + Puck N labels)
- "Hold your puck button to start" host hint
- Subscribe to `player_joined` + `match_started` socket events

### Slice 2C — Firmware multiplayer pair-mode
- `sp_pins.h` or firmware header: define `_puck_color()` returning a CRGB based on `PUCK_ID`
- Pair-mode LED ring shows puck's color (not generic blue) during dial
- New `_post_start()` for host puck: POST `/api/pair/start`
- Add LOBBY_WAITING state: after pair-confirm, puck holds in lobby until `match_started`. Host puck listens for TAP to fire start; non-hosts ignore TAP. Color-coded "I'm in" glow on LED.

### Slice 2D — In-match multi-player support
- Server: `/api/trivia/answer` accepts puck_id, scores per-player, returns per-player results
- Server: emit `reveal` with full per-player results dict
- Server: round-end logic — emit `reveal` when all pucks have locked OR timer expires
- Frontend: vertical sidebar on `QuestionScreen` with one row per player, color-coded, live updates (aiming/locked/timed-out/correct/wrong)
- Frontend: scoreboard adapted to N players sorted by total

### Slice 2E — Polish & verify
- Puck-color tokens in `src/index.css`
- Per-color audio cue if desired (slightly different lock-in tone per puck)
- Side-by-side audit vs HQ Trivia / Jackbox multiplayer references
- Full-flow run with 2 pucks (then 3+ if hardware available)
- Update `docs/audit/polish-gate-v1.1.md` -> `v2.md`

## Open follow-ups (out of scope for v2)

- **Late-join during match**: V2 disallows. Match starts with whoever's paired; new pucks wait for match to end.
- **Reconnect after puck drops mid-match**: V2 best-effort — if puck loses WiFi, it stops contributing to current round, can re-pair into next lobby after match ends. No mid-match resume.
- **Sabotage mechanics** (screw-your-neighbor, multipliers): planned for v3.
- **Team mode**: planned for v3.
- **Per-puck individual leaderboards across matches**: probably needs DB schema work; not in v2.

## Acceptance

- Two pucks can join the same lobby on the same TV. Both can dial the shared code. Host can start. Both see the same questions. Each can independently tilt + tap. Reveals show both answers + scores. After 7 questions, scoreboard shows ranked standings. Play-again resets the same lobby.
- Color identity is consistent — Puck 1 always blue across matches, Puck 2 always pink, etc.
- One-puck "match" still works (single-player play through, host-puck-only case is the unified default).

## Estimate

5 slices × ~2-3 hours each = roughly 12-15 hours of build time. Recommend completing 2A-2C in one session (~5h) to get the lobby + join flow working, then 2D-2E in a second session.
