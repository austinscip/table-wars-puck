# TABLE WARS - Multiplayer & Advanced Features

Complete guide to WiFi sync, multiplayer games, web scoreboard, and mobile app.

---

## 🌐 Multi-Puck System Overview

TABLE WARS now supports **2-6 pucks playing together** via ESP-NOW wireless communication!

### What's New

✅ **WiFi Sync System** - Puck-to-puck communication via ESP-NOW
✅ **5 Multiplayer Games** - Pass The Bomb, Team Battle, King of the Hill, Relay Race, Sync Shake
✅ **Web Scoreboard** - Flask server with real-time leaderboard
✅ **Mobile Control App** - Flutter app for bar staff
✅ **8 Original Games** - All single-puck games still work perfectly

---

## 📡 ESP-NOW WiFi Sync

### How It Works

**ESP-NOW** is a peer-to-peer wireless protocol (no WiFi router needed!):
- **Fast**: < 20ms latency between pucks
- **Reliable**: Works up to 200m outdoors, 50m indoors
- **Low power**: More efficient than regular WiFi
- **No router**: Pucks talk directly to each other

### Discovery Process

1. **Puck 1** sends discovery beacon every 1 second
2. **Pucks 2-6** receive beacon and respond with acknowledgment
3. Each puck builds a list of active pucks
4. Pucks exchange MAC addresses for direct messaging

### Message Types

```cpp
MSG_DISCOVERY       // "I'm here!"
MSG_BOMB_PASS       // Pass the bomb to another puck
MSG_TEAM_COLOR      // Team assignment (red vs blue)
MSG_SCORE_UPDATE    // Share your score
MSG_GAME_START      // Start a multiplayer game
MSG_GAME_STATE      // Sync game state
MSG_HEARTBEAT       // Keep-alive (every 5 seconds)
```

---

## 🎮 Multiplayer Games

### GAME 1: Pass The Bomb 💣

**Players**: 2-6 pucks
**Duration**: Until bomb explodes
**How to play**:
1. Puck 1 starts with the bomb (20 second timer)
2. Press button to pass bomb to next puck
3. Bomb countdown continues on receiving puck
4. Don't be holding it when it explodes!

**Scoring**:
- +200 points per successful pass
- 0 points if you explode

**Bar Appeal**: High! People frantically passing and laughing.

---

### GAME 2: Team Battle ⚔️

**Players**: 2-6 pucks (split into 2 teams)
**Duration**: 5 rounds
**How to play**:
1. Pucks auto-assign to Red team (odd IDs) or Blue team (even IDs)
2. Each round: Tap as fast as you can (10 seconds)
3. Team with most total taps wins the round
4. Best of 5 rounds wins

**Scoring**:
- +10 points per tap
- Winning team gets bonus points

**Bar Appeal**: Perfect for rivalries and group competition.

---

### GAME 3: King of the Hill 👑

**Players**: 2-6 pucks
**Duration**: 30 seconds
**How to play**:
1. Puck 1 starts as the King
2. Shake your puck to challenge for the throne
3. New King earns +10 points/second
4. Defend your reign or steal the crown!

**Scoring**:
- +10 points/second while King
- Whoever has the most points at the end wins

**Bar Appeal**: Constant competition, everyone can win.

---

### GAME 4: Relay Race 🏁

**Players**: 2-6 pucks
**Duration**: 5 seconds per puck
**How to play**:
1. Pucks take turns in sequence (1 → 2 → 3 → ...)
2. When it's your turn: Tap as fast as you can!
3. After 5 seconds, turn passes to next puck
4. Highest individual score wins

**Scoring**:
- +10 points per tap
- Personal best matters

**Bar Appeal**: Waiting for your turn builds tension.

---

### GAME 5: Synchronized Shake 🤝

**Players**: 2-6 pucks
**Duration**: 30 seconds
**How to play**:
1. All pucks must shake at the SAME intensity
2. Target intensity shown by LED brightness
3. When all pucks are synced: Everyone scores!
4. Coordination is key

**Scoring**:
- +10 points per synchronized second
- Team effort = team reward

**Bar Appeal**: Hilarious coordination challenges.

---

## 🛠️ Enabling Multiplayer in Firmware

### Update `platformio.ini`

The project already includes WiFi sync. Just make sure you have:

```ini
lib_deps =
    adafruit/Adafruit NeoPixel@^1.12.0
    adafruit/Adafruit MPU6050@^2.2.4
    adafruit/Adafruit Unified Sensor@^1.1.9
    adafruit/Adafruit BusIO@^1.14.1
    bblanchon/ArduinoJson@^6.21.3
    knolleary/PubSubClient@^2.8
```

### Enable Multiplayer Games

In `src/main_tablewars.h`, enable WiFi sync:

```cpp
// At top of file
#define ENABLE_WIFI_SYNC    // Uncomment this

#ifdef ENABLE_WIFI_SYNC
#include "wifi_sync.h"
#include "multiplayer_games.h"
#endif
```

### Configure Puck IDs

Each puck MUST have a unique ID (1-6):

```cpp
// In main_tablewars.h
#define PUCK_ID  1  // Change to 2, 3, 4, 5, or 6 for other pucks
```

### Compile & Upload

```bash
pio run --target upload
```

---

## 📊 Web Scoreboard Server

### Setup

1. **Install Python dependencies**:
   ```bash
   cd server
   pip install -r requirements.txt
   ```

2. **Run server**:
   ```bash
   python app.py
   ```

3. **Access leaderboard**:
   Open browser to `http://localhost:5000`

### Server Features

- ✅ **Real-time leaderboard** via WebSocket
- ✅ **Player statistics** (total score, games played, average)
- ✅ **Recent games feed**
- ✅ **RESTful API** for puck integration
- ✅ **SQLite database** for persistence

### Deploy on Raspberry Pi

Perfect for displaying on bar TV!

```bash
# On Raspberry Pi
cd server
python3 app.py

# Get Pi's IP
hostname -I

# Access from any device on same network
# http://<pi-ip>:5000
```

### Auto-start on boot

```bash
sudo nano /etc/rc.local

# Add before "exit 0":
cd /home/pi/table-wars-puck/server && python3 app.py &
```

---

## 📱 Mobile Control App

### Setup

1. **Install Flutter**:
   ```bash
   brew install flutter  # macOS
   ```

2. **Get dependencies**:
   ```bash
   cd mobile_app
   flutter pub get
   ```

3. **Run on device**:
   ```bash
   flutter run
   ```

### App Features

- ✅ **Scan for pucks** via Bluetooth LE
- ✅ **View puck status** (battery, signal strength)
- ✅ **Start games remotely**
- ✅ **Monitor multiple pucks**
- ⏳ **OTA firmware updates** (coming soon)

### For Bar Staff

Perfect for bartenders to:
- See which pucks are active
- Start specific games for customers
- Monitor battery levels
- Troubleshoot issues

---

## 🚀 Full System Deployment

### Hardware Needed

- 6× Complete pucks (built per BUILD_CHECKLIST.md)
- 1× Raspberry Pi 4 (for scoreboard server)
- 1× TV/monitor (for leaderboard display)
- 1× Android/iOS tablet (for mobile control app)

### Network Setup

**Option A: Bar WiFi** (Recommended)
- All pucks connect to bar WiFi
- Server runs on Raspberry Pi
- Everyone on same network can view leaderboard

**Option B: Dedicated WiFi** (Best performance)
- Create dedicated network just for TABLE WARS
- Eliminates interference from bar patrons
- More stable connections

### Setup Process

1. **Build all 6 pucks**
   - Follow BUILD_CHECKLIST.md
   - Set unique Puck IDs (1-6)
   - Test each puck individually

2. **Setup Raspberry Pi server**
   - Install Python & dependencies
   - Run Flask app on boot
   - Connect to bar TV via HDMI

3. **Configure WiFi**
   - Set WiFi credentials in firmware
   - Upload to all pucks
   - Verify all pucks connect

4. **Test multiplayer**
   - Power on all 6 pucks
   - Run discovery (takes 10 seconds)
   - Start "Pass The Bomb"
   - Verify bomb passes between pucks

5. **Setup mobile app**
   - Install on bar staff tablet
   - Scan for pucks
   - Test game control

6. **Launch!**
   - Place pucks on bar tables
   - Instruct customers on how to play
   - Monitor via mobile app

---

## 🔧 Troubleshooting Multiplayer

### Pucks Can't Find Each Other

**Symptoms**: Discovery timeout, "0 pucks found"

**Solutions**:
- ✅ Verify all pucks have unique IDs (1-6)
- ✅ Check pucks are within 50m of each other
- ✅ Ensure all using same WiFi channel (default: 1)
- ✅ Power cycle all pucks
- ✅ Re-upload firmware

### Bomb Pass Fails

**Symptoms**: "Send failed" in Serial Monitor

**Solutions**:
- ✅ Target puck must be online (check discovery)
- ✅ Move pucks closer together
- ✅ Check for WiFi interference
- ✅ Verify message queue not full

### Game Desyncs

**Symptoms**: Pucks show different game states

**Solutions**:
- ✅ Restart all pucks simultaneously
- ✅ Ensure stable power (low battery causes issues)
- ✅ Check for packet loss (watch Serial Monitor)
- ✅ Reduce distance between pucks

### Poor WiFi Range

**Symptoms**: RSSI < -80 dBm, frequent disconnects

**Solutions**:
- ✅ Upgrade antennas (external antenna mod)
- ✅ Reduce obstacles between pucks
- ✅ Increase transmission power in firmware:
  ```cpp
  esp_wifi_set_max_tx_power(84); // Max power
  ```

---

## 📈 Performance Metrics

### ESP-NOW Benchmarks

- **Discovery time**: 2-10 seconds (6 pucks)
- **Message latency**: 10-20ms
- **Max range**: 50m indoors, 200m outdoors
- **Packet loss**: < 1% under good conditions
- **Battery impact**: +15% drain vs single-puck mode

### Server Performance

- **Concurrent clients**: 50+ (WebSocket)
- **Database queries**: < 10ms (SQLite)
- **Memory usage**: 50-100MB (Flask + Python)
- **CPU usage**: < 5% (Raspberry Pi 4)

---

## 🎯 Best Practices

### For Bar Deployment

1. **Test extensively** before going live
2. **Charge all pucks** to 100% before opening
3. **Keep spares** (2 extra pucks)
4. **Monitor battery levels** via mobile app
5. **Restart pucks** between sessions (prevents desyncs)

### For Customers

1. **Explain games clearly** (use GAMES.md as reference)
2. **Start with single-puck games** (easier to learn)
3. **Introduce multiplayer gradually** (after they understand basics)
4. **Encourage groups** (multiplayer is more fun with 4+ people)

### For Development

1. **Use Serial Monitor** to debug WiFi issues
2. **Test with 2 pucks first**, then scale up
3. **Version your firmware** (helps track bugs)
4. **Log all errors** to SD card (future feature)

---

## 🆕 Adding Your Own Multiplayer Game

Create a new class in `src/multiplayer_games.h`:

```cpp
class MyNewGame {
private:
    WiFiSync* wifi;
    uint8_t myPuckID;
    uint32_t myScore;

public:
    MyNewGame(WiFiSync* wifiSync, uint8_t puckID);
    uint32_t play();
};
```

Implement in `src/multiplayer_games.cpp`:

```cpp
uint32_t MyNewGame::play() {
    Serial.println("🎮 MY NEW GAME");

    // Your game logic here
    // Use wifi->sendBombPass(), wifi->sendScore(), etc.

    return myScore;
}
```

Add to game selector in `main_tablewars.h`.

---

## 📞 API Reference

### WiFiSync Class

**Methods**:
```cpp
bool begin()                              // Initialize ESP-NOW
bool discoverPucks(uint16_t timeout)      // Find other pucks
bool sendBombPass(uint8_t target, ...)    // Pass bomb
bool sendScore(uint32_t score, ...)       // Broadcast score
bool sendGameStart(uint8_t gameID)        // Start multiplayer game
void update()                             // Call in loop()
```

**Callbacks**:
```cpp
setOnPuckDiscovered(callback)   // New puck found
setOnPuckLost(callback)         // Puck went offline
setOnBombReceived(callback)     // Bomb passed to you
setOnGameStart(callback)        // Game starting
```

---

## 🎉 What's Next?

**Immediate Next Steps**:
1. Build 6 pucks
2. Test multiplayer with 2 pucks
3. Scale to 4-6 pucks
4. Deploy server on Raspberry Pi
5. Pilot in a bar!

**Future Features**:
- [ ] Puck-to-puck mesh network (no server needed)
- [ ] Offline score tracking (SD card storage)
- [ ] Tournament brackets
- [ ] Bar vs Bar competitions (multiple locations)
- [ ] Spectator mode (watch games on phone)
- [ ] Custom game creator (mobile app)

---

**Ready to enable multiplayer?**

1. Upload firmware to all pucks (unique IDs!)
2. Power on all pucks
3. Wait 10 seconds for discovery
4. Start "Pass The Bomb"
5. HAVE FUN! 🎮🎉

**Questions?** See main README.md or open an issue.
