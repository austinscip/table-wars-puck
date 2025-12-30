# 📱 BLE Remote Control - Setup Guide

## What Was Added

**Bluetooth Low Energy (BLE) support** has been added to the ESP32 firmware, enabling remote control from the mobile app.

### New Features:
- ✅ Mobile app can start/stop games remotely
- ✅ Monitor battery levels in real-time
- ✅ See which pucks are online/offline
- ✅ Dual-mode: BLE for control + WiFi for score submission
- ✅ Standard Bluetooth SIG services (compatible with any BLE scanner)

---

## Files Added

1. **`src/ble_control.h`** - BLE service implementation
   - Battery monitoring service
   - Game control service
   - Device info service
   - Connection management

2. **`src/main_ble_wifi_test.h`** - Dual-mode test firmware
   - Combines BLE + WiFi
   - Remote game control via mobile app
   - Auto score submission to server
   - LED feedback for connection status

---

## How to Use

### Step 1: Upload Firmware to ESP32

The firmware is **already set to BLE+WiFi mode** in `src/main.cpp` (line 32).

**Upload to ESP32:**
```bash
cd /Users/austinscipione/table-wars-puck
pio run --target upload
```

Or in PlatformIO IDE: Click "Upload" button

### Step 2: Watch Serial Monitor

```bash
pio device monitor
```

You should see:
```
╔═══════════════════════════════════════════╗
║   TABLE WARS - BLE + WiFi Dual Mode      ║
╚═══════════════════════════════════════════╝

✅ Hardware initialized
📡 Connecting to WiFi...
   SSID: Verizon_7GKY9V
✅ WiFi connected!
   IP: 192.168.1.XX

🔵 Initializing BLE...
   Device Name: TableWars_1
✅ BLE initialized and advertising

╔═══════════════════════════════════════════╗
║          DUAL MODE ACTIVE                 ║
╚═══════════════════════════════════════════╝

📱 BLE:  Ready for mobile app connection
📡 WiFi: Connected to server

🎮 Use mobile app to start games remotely!
```

### Step 3: Connect Mobile App

#### Option A: Use Flutter App (Recommended)

**Setup:**
```bash
cd mobile_app
flutter pub get
flutter run
```

**In the app:**
1. Tap "Scan Pucks"
2. You'll see "TableWars_1" appear
3. Tap the menu icon (⋮)
4. Select "Connect"
5. Wait for connection confirmation

#### Option B: Use Generic BLE Scanner (Testing)

Download any BLE scanner app:
- **iOS:** LightBlue
- **Android:** nRF Connect

**Scan for device:**
- Device name: `TableWars_1`
- Services visible:
  - `180F` - Battery Service
  - `1800` - Game Control Service
  - `180A` - Device Information

---

## Controlling Games via Mobile App

### Start a Game

**Via Flutter App:**
1. Tap menu (⋮) on connected puck
2. Select "Start Game"
3. Choose from list:
   - Speed Tap Battle (0x01)
   - Shake Duel (0x02)
   - Red Light Green Light (0x03)
   - LED Chase Race (0x04)
   - Color Wars (0x05)
   - Hot Potato (0x09)
   - Drunk Duel (0x0A)

**Via BLE Scanner (Advanced):**
1. Connect to `TableWars_1`
2. Navigate to service `1800`
3. Find characteristic `2A00` (Game Command)
4. Write hex value: `01` (Speed Tap), `02` (Shake Duel), etc.
5. Puck LEDs will change color and game starts!

### What Happens:

1. **ESP32 receives BLE command**
   - Serial: `📱 BLE COMMAND: Game ID = 0x01`
   - LEDs flash the game's color
   - Game starts running

2. **Game runs automatically**
   - LEDs animate based on game type
   - Scores generated every 10 seconds
   - Auto-submitted to server via WiFi

3. **View on dashboard**
   - Open http://localhost:5001
   - See scores appearing in real-time!

### Stop Game

**Send command:** `0x00`

Puck returns to idle breathing animation.

---

## LED Feedback

| Event | LED Behavior |
|-------|-------------|
| Idle (no game) | Slow breathing cyan/blue |
| Mobile app connects | Flash green |
| Mobile app disconnects | Flash red |
| Game running | Spinning color (based on game ID) |
| Score submitted | Quick pulse |

---

## BLE Services Reference

### Battery Service (Standard)
- **Service UUID:** `0000180f-0000-1000-8000-00805f9b34fb`
- **Characteristic:** `00002a19...` (Battery Level)
- **Type:** Read + Notify
- **Value:** 0-100 (percentage)

### Game Control Service (Custom)
- **Service UUID:** `00001800-0000-1000-8000-00805f9b34fb`

**Game Command Characteristic:**
- **UUID:** `00002a00...`
- **Type:** Write
- **Format:** 1 byte
- **Values:**
  - `0x00` - Stop game
  - `0x01` - Speed Tap Battle
  - `0x02` - Shake Duel
  - `0x03` - Red Light Green Light
  - `0x04` - LED Chase Race
  - `0x05` - Color Wars
  - `0x06` - Rainbow Roulette
  - `0x07` - Visual Bomb Countdown
  - `0x08` - Simon Says LED
  - `0x09` - Hot Potato
  - `0x0A` - Drunk Duel

**Game State Characteristic:**
- **UUID:** `00002a01...`
- **Type:** Read + Notify
- **Format:** 2 bytes `[gameID, isRunning]`

### Device Info Service (Standard)
- **Service UUID:** `0000180a-0000-1000-8000-00805f9b34fb`

**Firmware Version:**
- **UUID:** `00002a26...`
- **Value:** "v1.0.0"

**Puck ID:**
- **UUID:** `00002a24...`
- **Value:** 1 byte (puck number)

---

## Troubleshooting

### BLE not advertising
- Check serial output for "BLE initialized"
- Restart ESP32
- Make sure no other BLE mode is running

### Mobile app can't find puck
- Ensure Bluetooth is ON
- Grant location permissions (required for BLE scanning)
- Move closer to ESP32 (< 5 meters)
- Try a generic BLE scanner to verify advertising

### Games won't start
- Check serial monitor for BLE command messages
- Verify correct characteristic UUID
- Ensure value is 1 byte (0x01, not "01")

### WiFi not connecting
- Check credentials in `main_ble_wifi_test.h`
- Update SSID/password if needed
- BLE will still work without WiFi

### Scores not appearing on dashboard
- Verify server is running on port 5001
- Check WiFi connection status
- Look for "Score submitted successfully" in serial

---

## Next Steps

### Add More Games
Edit `main_ble_wifi_test.h`:
```cpp
const char* gameNamesForBLE[] = {
    "Stopped",
    "Your New Game",  // Add here
    // ...
};
```

### Change Puck ID
Edit line in `main_ble_wifi_test.h`:
```cpp
#define PUCK_ID  2  // Change to 2, 3, 4, etc.
```

Each puck gets unique BLE name: `TableWars_2`, `TableWars_3`...

### Customize LED Colors
Edit the color calculation in `onGameCommandReceived()`:
```cpp
uint32_t color = strip.Color(255, 0, 0);  // Red
uint32_t color = strip.Color(0, 255, 0);  // Green
uint32_t color = strip.Color(0, 0, 255);  // Blue
```

---

## Demo Video Script

**What to show:**
1. ESP32 plugged into laptop
2. Serial monitor showing "BLE initialized"
3. Open mobile app, scan for pucks
4. "TableWars_1" appears in list
5. Tap connect - ESP32 LEDs flash green
6. Tap "Start Game" → Choose "Hot Potato"
7. ESP32 LEDs change color, serial shows game started
8. After 10 seconds, score auto-submits
9. Open http://localhost:5001 - score appears!
10. Tap "Stop Game" - puck returns to breathing

**Boom - remote controlled drinking game puck!** 🎮

---

**Questions?** Check `mobile_app/README.md` for mobile app details.
