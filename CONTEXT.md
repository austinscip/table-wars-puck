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
