# Table Wars Puck - Agent Instructions

## Project Overview

Table Wars is a wireless multiplayer gaming system consisting of:
- **ESP32 Pucks**: Handheld devices with motion sensors, LEDs, haptic feedback
- **Flask Server**: Python backend handling game state, WebSocket communication
- **Web Frontend**: Browser-based game displays and dashboards

## Architecture

```
[ESP32 Puck] --(WiFi/ESP-NOW)--> [Flask Server] --(WebSocket)--> [Browser Display]
     |                                |
     v                                v
Motion Sensors                  Game State
LED Ring (16)                   Leaderboards
Buzzer/Vibration                Player Management
Capacitive Touch                Real-time Events
```

## Build & Deploy Commands

```bash
# USB Upload (first time / debugging)
pio run -e puck1 -t upload

# OTA Upload (wireless, after initial setup)
pio run -e puck1_ota -t upload

# Deploy to all 6 pucks
./deploy_all_pucks.sh

# Start server
cd server && python app.py

# Monitor serial output
pio device monitor --baud 115200
```

## Feature Flags

In `platformio.ini`, these can be toggled:
- `ENABLE_OTA_UPDATES` - Wireless firmware updates (enabled)
- `ENABLE_DUAL_CORE` - FreeRTOS dual-core (disabled by default)
- `ENABLE_CAPACITIVE_TOUCH` - Touch controls (enabled)
- `ENABLE_ESP_NOW` - Puck-to-puck communication (enabled)
- `ENABLE_DEEP_SLEEP` - Battery saving mode (enabled)

## Hardware Pinout

| Component | GPIO Pin |
|-----------|----------|
| Buzzer | 15 |
| Button | 27 |
| LED Ring (WS2812B) | 23 |
| I2C SDA (MPU6050) | 21 |
| I2C SCL (MPU6050) | 22 |
| Touch Pins | 4, 0, 2, 15, 13, 12, 14, 27, 33, 32 |

## Testing Approach

1. **Serial Monitor**: Primary debugging interface
2. **Browser Verification**: All UI changes must be tested at http://localhost:5001
3. **Firmware Tests**: Run `TEST_ALL_FEATURES.ino` for hardware validation
4. **Multi-puck Tests**: Use ESP-NOW for puck-to-puck communication tests

## Key Gotchas

- **MPU6050 Calibration**: Always calibrate on flat surface before use
- **WiFi + ESP-NOW**: Cannot use WiFi and ESP-NOW simultaneously on all channels
- **FastLED + WiFi**: LED updates can cause WiFi instability - use show() sparingly
- **Memory Constraints**: ESP32 has 320KB RAM - avoid large buffers
- **OTA Password**: Default is `puck2024`, change in `platformio.ini`

## Important Directories

```
src/                    # ESP32 firmware
  main.cpp              # Entry point
  main_tablewars.h      # 51 original games
  main_complete.h       # All 56 games + features
  ota_update.h          # OTA functionality
  esp_now_multiplayer.h # Puck-to-puck
  capacitive_touch.h    # Touch controls

server/                 # Flask backend
  app.py                # Main server (port 5001)
  templates/            # Jinja2 HTML templates
  database.py           # SQLite/Postgres abstraction
  multiplayer_routes.py # Game API endpoints

tasks/                  # PRD files for Ralph
scripts/ralph/          # Ralph automation
```

## Game Development Pattern

New games follow this pattern:
1. **Firmware**: Add sensor input handling in `src/`
2. **Backend**: Add game routes in `server/` with WebSocket events
3. **Frontend**: Add UI in `server/templates/`
4. **Test**: Verify via serial monitor + browser

## Communication Protocols

- **Puck → Server**: HTTP POST or WebSocket
- **Server → Browser**: WebSocket (flask-socketio)
- **Puck → Puck**: ESP-NOW (250m range, 2-10ms latency)

## Ralph/Amp Nano-Story Workflow

### Story Structure
Each story in `prd.json` follows Level 4-5 granularity:
- **ID Format**: `US-XXXa-N` (Sprint, task group, sub-task)
- **Effort**: 5-20 minutes per story
- **Diff**: Exact code change to apply
- **Dependency**: Previous story that MUST pass first

### Sprint 0 Structure (Foundation)
```
Sprint 0A: MPU6050 sensor reading (US-001a-1 to US-001d-2)
Sprint 0B: ESP-NOW message extension (US-002a-1 to US-002d-2)
Sprint 0C: Gateway + Server parsing (US-003a-1 to US-003b-2)
Sprint 0D: Browser display + E2E test (US-003c-1 to US-004a-1)
```

### Running Ralph
```bash
cd /Users/austinscipione/table-wars-puck
./scripts/ralph/ralph.sh 50  # Run up to 50 iterations
```

### Key Files for Ralph
- `prd.json` - User stories (update passes: true when complete)
- `progress.txt` - Append learnings after each story
- `scripts/ralph/prompt.md` - Agent instructions
- `scripts/ralph/ralph.sh` - Execution loop (Amp CLI)

---

## Discipline & Guardrails (project-wide rules)

This project is a commercial bar/restaurant product. The TV is the surface that sells the unit. Sloppy visuals kill perceived value. The rules below override convenience.

### Visual / asset quality
- **No AI-generated graphics, music, or SFX.** No SDXL/DALL-E sprites, no text-to-3D models, no AI-generated audio. If a polished asset is not available, source one — do not ship slop.
- **No voxel / Minecraft / cube-block aesthetic.** Forbidden for this product.
- **No generic CSS gradient slop.** No Segoe UI / Verdana, no generic purple linear-gradients, no rgba opacity tricks as polish. Use the locked brand kit.
- **Approved 3D assets (CC0 / royalty-free):** Kenney.nl, Quaternius, Kay Lousberg, Synty POLYGON, Poly Pizza, Sketchfab CC0
- **Approved 2D / UI:** Kenney UI packs, shadcn/ui, Heroicons, Phosphor Icons, LottieFiles
- **Approved audio:** Pixabay SFX, Freesound CC0, Kenney Audio packs
- **TV/web tech stack:** Three.js + React Three Fiber + Drei (3D), PixiJS or Phaser 3 (2D arcade), React + Tailwind + shadcn/ui + Framer Motion (game-show UI)
- **Puck-side LEDs:** named palettes only (e.g. `PALETTE_TRIVIA_CORRECT`, `PALETTE_VICTORY`), eased transitions. No raw RGB literals in game code.
- **Polish gate:** every TV game gets a side-by-side comparison vs. a Jackbox / HQ Trivia reference frame before it ships. If it looks worse, it doesn't ship.

### Workflow discipline (Matt Pocock skills — github.com/mattpocock/skills)
- Before any feature larger than one file, invoke `/grill-with-docs`.
- Visual exploration goes through `/prototype` UI branch only. Prototype assets do not cross into production. Record the decision in an ADR, then delete the prototype.
- For web app work, follow `/tdd` vertical-slice protocol. Never write more than one failing test before making it pass.
- For bugs or perf regressions, invoke `/diagnose`. Build a deterministic feedback loop before hypothesising. Tag debug logs `[DEBUG-xxxx]` for one-grep cleanup.
- Before editing any file >300 lines or any module untouched this session, invoke `/zoom-out`.
- At session end, or before context approaches 70%, run `/handoff`. Reference existing artifacts, do not duplicate.
- Every PRD has an `Out of Scope` section. Every issue is labeled HITL (human-in-the-loop) or AFK (Claude can merge unattended).

### Project knowledge
- **Domain vocabulary:** `CONTEXT.md` at repo root. One sentence per term, `_Avoid_:` aliases for words to never use as synonyms.
- **Architectural decisions:** `docs/adr/NNNN-slug.md`. Only when the decision is (a) hard to reverse, (b) surprising without context, (c) a real trade-off.

### Safety
- Git guardrails hook is active (`.claude/hooks/block-dangerous-git.sh`). It blocks `git push`, `reset --hard`, `clean -f`, `branch -D`, `checkout .`, `restore .`, `--no-verify`, interactive rebase, `filter-branch`. Do not attempt to bypass — fix the underlying issue instead.
- Never `--no-verify` to skip pre-commit hooks. Fix the lint/test, do not skip it.
- New commits only. Do not amend or force-push without explicit user instruction.
