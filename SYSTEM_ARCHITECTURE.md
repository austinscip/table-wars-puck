# Table Wars - Complete System Architecture

## System Overview

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Phone (User)  │◄───────►│  Flask Server    │◄───────►│  TV Display     │
│                 │  WiFi   │  + SocketIO      │  WiFi   │  (Bar Screen)   │
└─────────────────┘         └──────────────────┘         └─────────────────┘
         ▲                           ▲
         │                           │
         │ WiFi                      │ WiFi
         ▼                           ▼
┌─────────────────┐         ┌──────────────────┐
│  ESP32 Puck     │         │  ESP32 Puck      │
│  (Hardware)     │◄───────►│  (Hardware)      │
└─────────────────┘ ESP-NOW └──────────────────┘
```

## Game Types Architecture

### Type 1: Single-Player TV Games (Games 52-61)
**Pattern**: One puck controls one TV display

**Endpoints**:
```
POST   /tv-games/start/<game_id>         # Body: {"puck_id": 1}
GET    /tv-games/state/<puck_id>
POST   /tv-games/end/<puck_id>
GET    /tv/<game-route>/<puck_id>        # TV display

WebSocket Events:
- puck_input         # { puck_id, tilt_x, tilt_y, shake, button }
- join_game_room     # { puck_id }
- game_state_update  # Server → Client (broadcast to room game_{puck_id})
```

**Storage**: `active_games[puck_id] = GameInstance()`

**Examples**: Puck Racer, Obstacle Dodger, Puck Golf, Space Invaders

---

### Type 2: Multiplayer Games (Games 70-73)
**Pattern**: Multiple pucks share one session/TV display

**Endpoints**:
```
POST   /multiplayer/start/<game_id>      # Body: {"player_ids": [1,2,3,4], "team_assignments": {...}}
GET    /multiplayer/state/<session_id>
POST   /multiplayer/end/<session_id>
GET    /tv/<game-route>?session=<id>    # TV display

WebSocket Events:
- multiplayer_input            # { session_id, puck_id, tilt_x, ... }
- join_multiplayer_session     # { session_id }
- multiplayer_state_update     # Server → Client (broadcast to room session_{session_id})
- multiplayer_game_over        # Server → Client
```

**Storage**: `active_sessions[session_id] = GameInstance()`

**Examples**: Keep Away Chaos, Tug of War, Bomb Lobber, Simon Says

---

### Type 3: Trivia Games (Games 1-51)
**Pattern**: Phone UI with optional TV display

**Endpoints**:
```
POST   /trivia/start                     # Body: {"puck_id": 1, "game_type_id": 3}
GET    /trivia/state/<puck_id>
POST   /trivia/answer/<puck_id>          # Body: {"answer": "A"}
GET    /bar/<slug>/table/<num>           # Phone UI
GET    /bar/<slug>/tv                    # TV display
```

---

## Shot Roulette Royale - Correct Architecture

**Game ID**: 62
**Type**: **MULTIPLAYER** (not single-player!)
**Pattern**: Games 70-73 (session-based)

### Required Implementation:

1. **Game Engine** (`multiplayer_engines.py`, not `tv_game_engines.py`)
   - Session-based, not puck-based
   - Manages multiple players
   - Turn order and state machine

2. **Routes** (`multiplayer_routes.py`, not just `tv_game_routes.py`)
   ```python
   POST /multiplayer/start/62
   Body: {
     "player_ids": [1, 2, 3, 4],
     "player_names": ["Alice", "Bob", "Charlie", "Dana"],
     "rounds": 5
   }
   Response: {
     "session_id": 1736453128,
     "state": {...}
   }
   ```

3. **WebSocket Events**
   ```javascript
   // Puck sends spin
   socket.emit('multiplayer_input', {
     session_id: 1736453128,
     puck_id: 1,
     gyro_z: 250.5,  // deg/s
     button_held: false
   });

   // Server broadcasts update
   socket.on('multiplayer_state_update', (state) => {
     // state.current_player_id
     // state.wheel_rotation
     // state.spinning
     // state.players[]
   });
   ```

4. **TV Display** (`/tv/shot-roulette-royale?session=<id>`)
   - Connects to session room, not puck room
   - Shows all players
   - Highlights current spinner

5. **Phone UI** (TODO: Needs creation)
   - Lobby to join/create session
   - Show player names and turn order
   - "Your turn!" notification
   - Show outcomes for each player

---

## Complete API Surface Map

### TV Games (Single-Player)
- [x] POST /tv-games/start/<game_id>
- [x] GET /tv-games/state/<puck_id>
- [x] POST /tv-games/end/<puck_id>
- [x] GET /tv-games/active
- [x] WS puck_input
- [x] WS join_game_room
- [x] WS game_state_update

### Multiplayer Games
- [x] POST /multiplayer/start/<game_id>
- [x] GET /multiplayer/state/<session_id>
- [x] POST /multiplayer/end/<session_id>
- [x] WS multiplayer_input
- [x] WS join_multiplayer_session
- [x] WS multiplayer_state_update
- [x] WS multiplayer_game_over
- [ ] **TODO**: GET /multiplayer/active (list sessions)
- [ ] **TODO**: POST /multiplayer/join/<session_id> (late join)
- [ ] **TODO**: POST /multiplayer/kick/<session_id>/<player_id>

### Trivia Games
- [x] POST /trivia/start
- [x] POST /trivia/answer/<puck_id>
- [x] GET /trivia/state/<puck_id>
- [x] GET /bar/<slug>/table/<num>

### General
- [x] POST /api/register (register puck)
- [x] POST /api/score (save score)
- [x] GET /api/leaderboard
- [x] GET /api/puck/<puck_id>

---

## Firmware Data Transmission

### Current Sensor Data (from dual_core.h):
```cpp
struct SensorData {
    float accel_x, accel_y, accel_z;
    float gyro_x, gyro_y, gyro_z;       // ✓ gyro_z available!
    float tilt_angle_x, tilt_angle_y;
    bool shake_detected;
    float shake_intensity;
    bool button_pressed;
    unsigned long timestamp;
};
```

### Puck → Server Transmission Format (NEEDS VERIFICATION):
```javascript
// Expected format (based on tv_game_engines.py):
{
  "puck_id": 1,
  "tilt_x": -15.3,
  "tilt_y": 8.2,
  "shake_intensity": 12.5,
  "shake_detected": true,
  "button_held": false,
  "timestamp": 1234567890,
  "gyro_z": ???  // ⚠️ NOT CONFIRMED if firmware sends this!
}
```

**ACTION REQUIRED**:
1. Check firmware code to see if `gyro_z` is transmitted
2. If not, update firmware to include `gyro_z` in WebSocket payload
3. Conversion: `gyro_z_deg_per_sec = gyro.z * 57.2958` (rad/s → deg/s)

---

## Testing Infrastructure Needed

### 1. Puck Simulator Endpoint
```python
# Create: /api/test/simulate-puck
POST /api/test/simulate-puck
Body: {
  "session_id": 123,
  "puck_id": 1,
  "gyro_z": 250.0,  // Simulate hard spin
  "tilt_x": 0,
  "button_held": false
}
```

### 2. Session Test UI
```html
<!-- Create: /test/multiplayer-simulator -->
- Create session button
- Add fake players (1-8)
- Simulate spins with slider
- Show real-time state updates
```

---

## Shot Roulette Royale - Complete User Journey

### Scenario: 4 friends at a bar

1. **Setup** (Phone or Bar Tablet)
   ```
   User → Navigate to /multiplayer/lobby
   User → Select "SHOT ROULETTE ROYALE"
   User → Enter player names: ["Alice", "Bob", "Charlie", "Dana"]
   User → Assign pucks: [1, 2, 3, 4]
   User → Click "Start Game"
   POST /multiplayer/start/62 { player_ids: [1,2,3,4], player_names: [...] }
   Server → Returns session_id: 1736453128
   ```

2. **TV Display Launches**
   ```
   Browser → Navigate to /tv/shot-roulette-royale?session=1736453128
   TV → Connects to WebSocket
   TV → emit('join_multiplayer_session', { session_id })
   TV → Displays: "ALICE - YOUR TURN! SPIN YOUR PUCK!"
   ```

3. **Round 1 - Alice's Turn**
   ```
   Alice → Picks up Puck 1
   Alice → Physically spins puck (hard spin - 280 deg/s)

   Puck 1 → Detects gyro_z = 280 deg/s
   Puck 1 → emit('multiplayer_input', { session_id, puck_id: 1, gyro_z: 280 })

   Server → Calculates: Hard spin = 6-8 zones travel
   Server → Wheel spins: 2.5 full rotations + 6.2 zones
   Server → emit('multiplayer_state_update', {
              spinning: true,
              wheel_rotation: 912.4°,
              current_player: "Alice"
            })

   TV → Animates wheel spinning (8 seconds)
   TV → Wheel decelerates, lands on "CHUG"
   TV → Shows: "ALICE LANDED ON CHUG! 💀 DRINK UP!"

   Puck 1 → LED ring turns red, vibrates 3 times (haptic feedback)
   ```

4. **Round 1 - Bob's Turn**
   ```
   TV → Displays: "BOB - YOUR TURN!"

   Bob → Light spin (85 deg/s)
   Server → Calculates: 1.8 zones travel
   TV → Wheel spins gently, lands on "DRINK ONE"
   TV → Shows: "BOB LANDED ON DRINK ONE! 🍺"
   ```

5. **Round 1 - Special Zones**
   ```
   Charlie → Lands on "SPIN AGAIN"
   TV → "SPIN AGAIN! Go again Charlie!"
   Server → state.extra_spin = true, doesn't advance player

   Dana → Lands on "CHAMPION"
   TV → "DANA IS THE CHAMPION! 👑 Pick someone to drink!"
   TV → Shows player avatars to select
   ```

6. **Game End** (After Round 5)
   ```
   Server → game_over = true
   Server → emit('multiplayer_game_over', {
              winners: ["Dana"],
              stats: {
                Alice: { drinks: 4, immunities: 0 },
                Bob: { drinks: 2, immunities: 1 },
                ...
              }
            })

   TV → Shows final scoreboard
   TV → "DANA WINS! Play again?"
   ```

---

## Critical Gaps Identified

### MUST HAVE:
1. ✅ Multiplayer engine for Shot Roulette (session-based)
2. ✅ Player management (join, register, turn order)
3. ❌ Phone UI for lobby/player join
4. ❌ Firmware verification (gyro_z transmission)
5. ❌ Test/simulator endpoint
6. ❌ Zone outcome handling (CHAMPION picks player, SPIN AGAIN logic, etc.)
7. ❌ Player state tracking (drinks taken, immunities held, challenges)

### NICE TO HAVE:
- Player avatars/colors
- Sound effects on TV
- Leaderboard integration
- Tournament mode (multiple games)

---

## Implementation Priority

1. **Verify firmware gyro_z** - Can't test without this
2. **Create test simulator** - Need to test without hardware
3. **Move game to multiplayer pattern** - Refactor existing code
4. **Implement turn management** - Core game loop
5. **Add zone outcome logic** - Game mechanics
6. **Create phone lobby UI** - User can start games
7. **Test end-to-end** - Complete user journey
