# Project Vocabulary

Domain glossary for Table Wars. One sentence per term. The `_Avoid_:` lines list aliases that must not be used as synonyms — pick one canonical name and stick to it across firmware, server, web, and docs.

## Hardware

- **Puck** — A single ESP32 handheld unit (button, 16-LED ring, IMU, buzzer, vibration motor, battery, ESP-NOW radio). _Avoid_: device, controller, remote, dongle.
- **Host Puck** — The one puck per table that bridges sibling pucks' ESP-NOW traffic to the cloud over WiFi. Exactly one per active table. _Avoid_: master, primary, gateway puck.
- **Sibling Puck** — Any non-host puck at the same table; reaches the cloud only via the Host Puck. _Avoid_: slave, client, peer.
- **Rev A / Rev B** — Hardware revisions. Rev A uses pins BUZZER=15, BUTTON=27, LED=23. Rev B uses BUZZER=32, BUTTON=33, LED=5, MOTOR=4. Code must compile against one revision at a time via PlatformIO build flags.

## Software layers

- **HAL** — Hardware Abstraction Layer in firmware (`src/hal/*.h`). Wraps button, LED, IMU, buzzer, motor, NVS storage, ESP-NOW comms. Game code never calls FastLED / Adafruit_MPU6050 / ledc directly. _Avoid_: driver, BSP.
- **Game** — A single playable mode (e.g. Speed Pyramid, Duck Hunt). Lives in `src/games/g_<name>.h`, inherits from `Game` base class. _Avoid_: mode, activity, scene.
- **Game Loop** — The per-game `Game::loop()` routine. Called from the menu launcher after the player picks the game. _Avoid_: game loop in the engine sense — that's the global firmware super-loop.
- **Menu Launcher** — The boot-time `main.cpp` UI that lets a player cycle games and launch one. Replaces the old diagnostic test as `main.cpp`. _Avoid_: home screen, main menu.

## Gameplay nouns

- **Session** — A connection lifetime between a Puck and the cloud realtime backend. Begins at pair, ends at disconnect. _Avoid_: connection (too generic at this layer).
- **Lobby** — The pre-game state where players join a table and pick a game. _Avoid_: waiting room, queue.
- **Match** — One full play-through of a Game, from start to final scoreboard. _Avoid_: session (overloaded), session (used at network layer), play.
- **Round** — A subdivision inside a Match (e.g. one trivia question, one battle-royale wave). _Avoid_: turn, level.
- **Score** — A non-negative integer earned during a Match. Persisted per-puck in NVS and uploaded to the leaderboard. _Avoid_: points (use in player-facing copy only), rank.

## Identity

- **Player** — The human holding a Puck. Identified by Puck ID for now. _Avoid_: user.
- **Puck ID** — Stable 1-byte ID assigned per puck at provisioning time. _Avoid_: device ID.
- **Table** — The physical bar/restaurant table that a set of pucks belongs to. Identified by 6-digit pair code at runtime. _Avoid_: room, group.
- **Bar Account** — The Supabase row representing the venue. _Avoid_: tenant, customer, org.

## TV / web

- **TV View** — The cloud-hosted web page the smart TV browser navigates to. URL: `https://<host>/bar/<6-digit-code>`. _Avoid_: dashboard, display, screen.
- **Pair Code** — The 6-digit code displayed by the TV View and entered on the Host Puck via tilt-select to bind the table to the TV. _Avoid_: session code, room code.
- **Polish Gate** — The pre-ship review where a TV game is screenshotted next to a Jackbox / HQ Trivia / Bar Rescue reference and judged. _Avoid_: QA.

## Visual / asset vocabulary

- **Visual Token** — A semantic name for a color, font size, motion duration, or LED palette. Lives in `tokens.json` (web) and `hal/led.h` palettes (firmware). _Avoid_: theme variable, design var.
- **LED Palette** — A named set of CRGB values + transition curve consumed by `hal/led.h` (e.g. `PALETTE_TRIVIA_CORRECT`, `PALETTE_VICTORY`). _Avoid_: color scheme, color set.
- **North Star Frame** — A reference screenshot from a real product (Jackbox, HQ Trivia, Bar Rescue) committed to `docs/north-star/`. Every TV game must hold up beside its assigned North Star Frame. _Avoid_: mockup, reference image.

## Locked brand tokens (web)

Authoritative source-of-truth for color, type, and motion across all TV games. Lives in `tokens.json` + `tailwind.config.js`. Aesthetic direction: HQ Trivia / Jackbox.

**Palette:**
- `--bg`: `#0A0E1A` (near-black, slight blue undertone) — game canvas background
- `--primary`: `#3B82F6` (electric blue) — primary action color, selected-answer highlight
- `--accent`: `#EC4899` (hot pink) — secondary accent, attention beats
- `--correct`: `#FBBF24` (sunny gold) — correct answer, victory states
- `--wrong`: `#EF4444` (red) — wrong answer, elimination states
- `--text`: `#F8FAFC` (off-white) — primary text on `--bg`

**Type:**
- Display: **Anton** (Google Fonts, free) — question text, big numerals, game titles
- Body: **Inter** (Google Fonts, free) — UI copy, instructions
- Score numerals: **JetBrains Mono** (Google Fonts, free) — points / timers / counters

**Motion:**
- Default ease (reveal, overshoot energy): `cubic-bezier(0.34, 1.56, 0.64, 1)`
- Reveal duration: **400ms**
- Snap / hover duration: **150ms**
- Score count-up: **800ms** with stagger

## Sprint vocabulary

- **Speed Pyramid** — A YDKJ-style trivia game with speed-tiered scoring: gold 0-3s = 1000pts, silver 3-6s = 500pts, bronze 6-10s = 200pts. Player tilts puck for A/B/C/D, taps to lock in. First sprint target. _Avoid_: Trivia Pyramid (the show), Trivia Speed Round.
- **State Authority** — The single process that owns the canonical state machine for a Match. For Table Wars: always the Flask server. Pucks and TV Views are dumb clients. _Avoid_: source of truth (used informally elsewhere), master.

## Sandbox / dev tooling

These exist only in the sandbox worktree and are never bundled into a production build.

- **Virtual Puck** — A browser-rendered control panel that POSTs the same `/api/pair/*` and `/api/sp/*` endpoints a Puck's firmware does, used in the sandbox for mouse-only end-to-end testing. Never bundled into prod. _Avoid_: demo mode, dev player, fake puck.
- **Hub** — The single sandbox page at `/dev/hub` that renders up to 8 Virtual Pucks in a grid. The Hub is not itself a Puck; it's the harness that hosts them. Each Virtual Puck reuses real `PUCK_COLORS[1..8]` server-side, so colors match a real-hardware test. _Avoid_: console, dashboard.
- **Pragmatic input model** — The convention for Virtual Puck controls: faithful at every endpoint surface (TAP / HOLD_1S / HOLD_3S, tilt N/E/S/W, A/B/C/D in answering mode) except the 6-digit pair-code dial, which is short-circuited to a single "Confirm Code" click that auto-POSTs all 6 `/api/pair/dial` calls + `/api/pair/confirm`. Dial cycling on a mouse carries zero information beyond the auto-call; tilt input still needs to be testable end-to-end because answer-preview bugs are real.
- **Faithful polling** — The Virtual Puck synchronizes with server state by polling the same endpoints at the same cadence as firmware (`/api/sp/current-question` 500ms, `/api/sp/match-state` 500ms, `/api/pair/lobby-state` 1s). It does NOT subscribe to socket.io events. The Hub itself MAY subscribe to sockets for its read-only meta display (pair code, round number) since the Hub is dev tooling, not a Puck.
- **VITE_DEV_TOOLS** — Build-time Vite env flag (`import.meta.env.VITE_DEV_TOOLS`). When truthy, the Hub route mounts under `/dev/hub`. When falsy (default for prod builds), the Hub code is tree-shaken out of the bundle. Sandbox builds use `VITE_DEV_TOOLS=1 vite build` (wired as `npm run build:sandbox`); prod builds use plain `vite build`.
