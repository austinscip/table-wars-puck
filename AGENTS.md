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
