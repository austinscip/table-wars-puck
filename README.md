# Table Wars - Puck Firmware v0.1

**Interactive bar game device with LEDs, haptics, sound, and motion detection.**

---

## ⚡ Power Upgrade: MT3608 Boost Converter

**This project is configured to use the MT3608 DC-DC boost converter** for proper 5V LED power.

**Why MT3608?**
- ✅ Brighter, more vivid LEDs (full 5V vs dim 3.7V battery voltage)
- ✅ Accurate RGB colors (especially blues!)
- ✅ Consistent brightness (doesn't fade as battery drains)
- ✅ Professional results for ~$1.50/puck

**What you need:** MT3608 DC-DC boost converter (10-pack for $10-15 on Amazon)

**See `MT3608_WIRING.md` and `WIRING_GUIDE.md` for complete setup instructions.**

---

## 📦 What's In This Project

- **Firmware** for ESP32-DevKitC-32 (38-pin)
- **Hardware test modes** for each component
- **Interactive "puck feels alive" mode** (NORMAL_MODE)
- **🎮 FULL GAME SYSTEM** with 8 complete mini-games (TABLE_WARS_MODE) 🎮
- **🌐 MULTIPLAYER MODE** - 2-6 pucks playing together via ESP-NOW WiFi sync 🌐
- **📊 Web Scoreboard** - Flask server with real-time leaderboard
- **📱 Mobile Control App** - Flutter app for bar staff
- **MT3608-integrated wiring guide** for professional LED brightness
- **Complete documentation** in `WIRING_GUIDE.md`, `BUILD_CHECKLIST.md`, `SCHEMATIC.txt`, `GAMES.md`, and `MULTIPLAYER.md`

---

## 🚀 Business Strategy & Go-To-Market

**You have a working product. Now what?**

### 📊 Complete Business Playbook Available

**`BUSINESS_PLAYBOOK.md`** - Your roadmap from prototype → profitable business:

**Phase 1: Customer Discovery** (Days 1-30)
- Contact 50 bars, validate demand
- Build demo materials (pitch deck, video, landing page)
- Book 10+ in-person demos

**Phase 2: Paid Pilots** (Days 31-90)
- Close 5 paid pilot bars ($99/month)
- Collect ROI data (track sales lift)
- Prove product-market fit

**Phase 3: Go/No-Go Decision** (Day 90)
- Success = 4+ bars renew, 30%+ sales increase
- If validated → Raise capital, scale to 100 bars
- If not → Iterate or pivot

**Phase 4: Scale** (Months 4-15)
- Manufacture 600 pucks (injection molding)
- Hire sales reps
- Deploy to 100 bars → $120k ARR

### 🎯 Start Here: Week 1 Action Plan

**`WEEK1_ACTION_PLAN.md`** - Day-by-day execution checklist

**This week** (30-40 hours):
- Monday: Research competitors, build target list
- Tuesday: Create pitch deck + demo video
- Wednesday: Build landing page, visit 5 bars
- Thursday: Cold call 20 bars, visit 5 more
- Friday: Instagram outreach, order components
- Weekend: Assemble 2 pilot sets

**Goal**: 50 bars contacted, 10 demos booked, 5 paid pilots closed (in 30 days)

### 💰 Financial Reality Check

```
Unit Economics (per bar):
├─ COGS: $300 (6 pucks + server)
├─ Price: $99/month × 24 months = $2,376
├─ Gross Profit: $2,076 per bar
└─ Gross Margin: 87%

Break-Even: 24 bars (achievable in Month 6)

100 Bars = $120k ARR (Month 12 goal)
```

### ⚠️ Critical Questions Answered

The playbook addresses:
- How do I validate demand BEFORE scaling?
- What pricing model works best? (Lease vs sale vs revenue share)
- How do I compete with Buzztime/NTN trivia?
- How do I manufacture 1,000 pucks affordably?
- What if nobody wants this? (Pivot scenarios)
- How do I sell to 100 bars without a sales team?

**Read `BUSINESS_PLAYBOOK.md` before you build your 10th puck.**

---

## 🎯 Quick Start

⚠️ **IMPORTANT**: If this is your first build, see **`BREADBOARD_FIRST_GUIDE.md`** before soldering anything!
- Build a breadboard prototype first (1-2 hours, no soldering)
- Test that everything works before permanent assembly
- Saves you 2-4 hours of debugging
- Only costs $20 for breadboard + jumper wires

### 1. Install PlatformIO

**Option A: VS Code Extension (Recommended)**
1. Install [VS Code](https://code.visualstudio.com/)
2. Install the **PlatformIO IDE** extension
3. Restart VS Code

**Option B: CLI**
```bash
pip install platformio
```

### 2. Open This Project

**VS Code:**
- File → Open Folder → Select `table-wars-puck/`
- PlatformIO will auto-detect `platformio.ini`

**CLI:**
```bash
cd table-wars-puck
```

### 3. Build the Firmware

**VS Code:**
- Click the checkmark (✓) icon in the bottom toolbar
- Or: PlatformIO → Build

**CLI:**
```bash
pio run
```

### 4. Upload to ESP32

1. **Connect ESP32 via USB-C**
2. **Upload:**

**VS Code:**
- Click the arrow (→) icon in bottom toolbar
- Or: PlatformIO → Upload

**CLI:**
```bash
pio run --target upload
```

### 5. Open Serial Monitor

**VS Code:**
- Click the plug icon in bottom toolbar
- Or: PlatformIO → Serial Monitor

**CLI:**
```bash
pio device monitor
```

You should see:
```
========================================
  TABLE WARS - Puck Firmware v0.1
========================================

✅ LED ring initialized
✅ Button initialized (GPIO 27)
✅ Buzzer initialized (GPIO 15)
✅ Motor driver initialized (GPIO 12)
✅ MPU6050 initialized
```

---

## 🧪 Testing Modes

Edit `src/main.cpp` and **uncomment ONE mode:**

```cpp
// ============================================================================
// MODE SELECTION - UNCOMMENT ONE MODE
// ============================================================================
// #define TEST_MODE_LEDS      // Test LED ring
// #define TEST_MODE_BUTTON    // Test button
// #define TEST_MODE_BUZZER    // Test buzzer
// #define TEST_MODE_MOTOR     // Test vibration motor
// #define TEST_MODE_MPU       // Test motion sensor
// #define NORMAL_MODE         // Full interactive mode
#define TABLE_WARS_MODE        // 🎮 FULL GAME SYSTEM!
```

### Mode Descriptions

| Mode               | What It Does                                      |
|--------------------|--------------------------------------------------|
| `TEST_MODE_LEDS`   | Cycles through colors and animations             |
| `TEST_MODE_BUTTON` | Lights green + beeps when button pressed         |
| `TEST_MODE_BUZZER` | Plays beep patterns in a loop                    |
| `TEST_MODE_MOTOR`  | Pulses vibration motor on/off                    |
| `TEST_MODE_MPU`    | Prints acceleration + detects shakes             |
| `NORMAL_MODE`      | Full interactive firmware                        |
| **`TABLE_WARS_MODE`** | **🎮 ALL 8 MINI-GAMES** (see `GAMES.md`)    |

**After changing mode:**
1. Save `main.cpp`
2. Re-upload (click → or `pio run -t upload`)

---

## 🎮 Normal Mode Behavior

When running `NORMAL_MODE`, your puck will:

### On Boot
- Run a spinner animation (cyan)
- Flash white
- Beep once
- Enter idle mode

### Idle State
- LEDs slowly pulse cyan (breathing effect)
- Waiting for input...

### Button Press
- Flash green
- Vibrate briefly
- Beep
- Return to idle

### Shake Detection
- Rainbow burst animation
- Vibrate for duration of animation
- Double beep
- Return to idle

**Serial output will confirm all actions.**

---

## 🎮 TABLE WARS Game Mode

When running `TABLE_WARS_MODE`, your puck becomes a **complete mini-game system** with 8 different games!

### How It Works

The puck runs in **demo mode** by default:
- Automatically cycles through all 8 games
- Each game runs 10-30 seconds
- Press button anytime to skip to next game
- Tracks total session score across all games
- Full Serial Monitor output for debugging

### Game System Features

✅ **8 Complete Mini-Games** (see `GAMES.md` for full details):
1. **Speed Tap Battle** - Button mashing competition
2. **Shake Duel** - Violent shaking intensity meter
3. **Red Light Green Light** - Freeze game with motion detection
4. **LED Chase Race** - Timing/reflex challenge
5. **Color Wars** - Territory defense game
6. **Rainbow Roulette** - Stop on the target color
7. **Visual Bomb Countdown** - Hot potato style game
8. **Simon Says LED** - Memory pattern game

✅ **Smart Game Logic**:
- Each game has unique scoring system
- Visual feedback via LED animations
- Haptic feedback (vibration)
- Audio cues (buzzer patterns)
- Progressive difficulty
- Clear win/lose conditions

✅ **Bar-Ready Features**:
- Demo mode for showing off all games
- Manual skip for quick testing
- Score tracking
- WiFi framework ready (for multi-puck sync)

### Using TABLE_WARS_MODE

1. **Enable the mode** in `src/main.cpp`:
   ```cpp
   #define TABLE_WARS_MODE      // 🎮 FULL GAME SYSTEM!
   ```

2. **Upload to ESP32**:
   ```bash
   pio run --target upload
   ```

3. **Open Serial Monitor** to see game output:
   ```bash
   pio device monitor
   ```

4. **Watch the games cycle!**
   - Each game announces itself
   - Follow on-screen instructions
   - Press button to skip to next game
   - Session total shown after each game

### Example Serial Output

```
╔═══════════════════════════════════════════╗
║      TABLE WARS - GAME SYSTEM v1.0       ║
╚═══════════════════════════════════════════╝

🎮 Puck ID: 1
🎲 Table: 1

🎮 DEMO MODE - Cycling through all games
Press button anytime to skip to next game

🎮 GAME: SPEED TAP BATTLE
Mash the button as fast as you can!
✅ TAPS: 47
💯 SCORE: 470

════════════════════════════════════════
SESSION TOTAL: 470 points
════════════════════════════════════════

Next game in 5 seconds...
(Press button to skip)
```

### Customization

Edit `src/main_tablewars.h` to customize:

```cpp
// Change puck ID (1-6 for multi-puck setup)
#define PUCK_ID            1

// Change table assignment
#define TABLE_NUMBER       1

// WiFi credentials (for future multi-puck sync)
const char* WIFI_SSID = "TABLE_WARS_GAME";
const char* WIFI_PASSWORD = "tablewars2024";
```

### Full Game Documentation

See **`GAMES.md`** for:
- Detailed rules for each game
- Scoring systems
- Strategy tips
- Customization options
- Bar deployment guide

---

## 🌐 Multiplayer Mode (2-6 Pucks)

TABLE WARS now supports **wireless multi-puck gameplay** via ESP-NOW!

### What's Included

✅ **ESP-NOW WiFi Sync** - Puck-to-puck communication (no router needed!)
✅ **5 Multiplayer Games**:
  1. **Pass The Bomb** 💣 - Hot potato with 20-second timer
  2. **Team Battle** ⚔️ - Red vs Blue team competition
  3. **King of the Hill** 👑 - Fight for the throne
  4. **Relay Race** 🏁 - Sequential turn-based tapping
  5. **Synchronized Shake** 🤝 - Coordinate shake intensity

✅ **Web Scoreboard Server** - Flask app with real-time leaderboard
✅ **Mobile Control App** - Flutter app for bar staff (BLE control)
✅ **Discovery Protocol** - Automatic puck detection (2-10 seconds)

### Quick Setup

1. **Enable WiFi sync** in `src/main_tablewars.h`:
   ```cpp
   #define ENABLE_WIFI_SYNC    // Uncomment this line
   ```

2. **Set unique puck IDs** (1-6) for each puck:
   ```cpp
   #define PUCK_ID  1  // Change to 2, 3, 4, 5, or 6
   ```

3. **Upload to all pucks**:
   ```bash
   pio run --target upload
   ```

4. **Power on all pucks** - they'll automatically discover each other!

5. **Start a multiplayer game** - Choose "Pass The Bomb" or "Team Battle"

### Web Scoreboard

Real-time leaderboard with live score updates:

```bash
cd server
pip install -r requirements.txt
python app.py
```

Open browser to `http://localhost:5000` - perfect for displaying on bar TV!

### Mobile Control App

Flutter app for bar staff to control pucks remotely:

```bash
cd mobile_app
flutter pub get
flutter run
```

Features:
- Scan for nearby pucks via Bluetooth LE
- View battery levels and signal strength
- Start games remotely
- Monitor multiple pucks

### Complete Multiplayer Guide

See **`MULTIPLAYER.md`** for:
- ESP-NOW technical details
- Complete game rules for all 5 multiplayer games
- Server deployment guide (including Raspberry Pi)
- Mobile app setup instructions
- Troubleshooting multi-puck connections
- API reference for WiFiSync class
- How to add your own multiplayer games

---

## 🏗️ 3D Printed Enclosure (Forerunner Design)

A complete **Halo 3 Forerunner-inspired** enclosure specification is ready for production!

### Design Highlights

**Aesthetic**:
- Forerunner Energy Core styling
- Smooth ancient technology curves
- Concentric energy rings aligned with LEDs
- Decorative glyphs and hexagonal details
- Translucent top shell for LED diffusion

**Durability** 🛡️:
- 95mm diameter, 40mm total height
- 3.0-3.5mm wall thickness (drop-resistant)
- TPU bumper ring around equator (crumple zone)
- IP54 splash resistance (O-ring seal)
- Survives 1-meter drops onto concrete

**Engineering**:
- Precision mounts for all components
- Brass heat-set inserts (M3 screws)
- Integrated wire routing channels
- Thermal ventilation for ESP32
- Velcro battery retention
- Direct tactile button (not flex membrane)
- USB-C access for charging

### Print Specifications

```
Materials:
- Top shell: Translucent PETG (7-9 hours)
- Bottom shell: Standard PETG (6-8 hours)
- TPU parts: Bumper ring, motor sock (1-2 hours)

Total print time: 14-19 hours per puck
Material cost: $5.62 basic / $8.92 with all options
```

### Documentation

📄 **`ENCLOSURE_SPEC.md`** - Complete technical specification:
- Detailed CAD requirements (95mm diameter, all dimensions)
- Component mounting specifications
- Print settings for PETG and TPU
- Assembly instructions with tool list
- Durability testing protocol
- Troubleshooting guide

📋 **`CAD_CHECKLIST.md`** - Quick reference for CAD designers:
- Feature-by-feature checklist
- Critical dimensions summary
- Aesthetic guidelines (Forerunner style)
- Mini test print recommendations
- Deliverables list

### Design Status

✅ Specification complete (v2.0)
✅ All critical issues addressed (button, durability, thermal, sealing)
🔄 Ready for CAD modeling
🔄 Awaiting test prints

### Enclosure Features Summary

| Feature | Specification |
|---------|--------------|
| Drop resistance | 1m onto concrete |
| Water resistance | IP54 (splash resistant) |
| Button type | Direct tactile (12mm) |
| Fasteners | 6× M3 with brass inserts |
| Thermal vents | 4× Forerunner glyphs |
| Weight | ~120g empty (est.) |
| Assembly time | 45-60 minutes |
| Serviceability | Full disassembly possible |

**Next**: Commission CAD modeling based on `ENCLOSURE_SPEC.md` or model yourself in Fusion 360/OnShape.

---

## ⚙️ Configuration

All settings are at the top of `src/main.cpp`:

### Pin Configuration
```cpp
#define PIN_LED_RING       13    // WS2812B data
#define PIN_MPU_SDA        21    // MPU6050 I2C data
#define PIN_MPU_SCL        22    // MPU6050 I2C clock
#define PIN_BUTTON         27    // Button
#define PIN_BUZZER         15    // Buzzer +
#define PIN_MOTOR          12    // Motor (via transistor)
```

### LED Settings
```cpp
#define NUM_LEDS           16    // LEDs in ring
#define LED_BRIGHTNESS     80    // 0-255 (keep ≤100 for battery life)
```

**Brightness tips:**
- 80 = Good balance (default)
- 50 = Longer battery life
- 150 = Brighter (drains battery faster)
- 255 = Max (may exceed battery/TP4057 limits!)

### Motion Detection
```cpp
#define SHAKE_THRESHOLD    15.0  // Acceleration for "shake" (m/s²)
#define SHAKE_COOLDOWN_MS  1000  // Min time between shakes
```

**Sensitivity:**
- Lower threshold = more sensitive
- Higher threshold = harder shakes needed
- Default (15.0) = medium shake

### Timing
```cpp
#define PULSE_PERIOD_MS    2000  // Idle LED pulse speed
#define DEBOUNCE_MS        50    // Button debounce
```

---

## 🔧 Wiring Your Puck

**See `WIRING_GUIDE.md` for complete wiring instructions!**

**Quick reference (with MT3608):**

| Component      | Connection | Notes                          |
|---------------|-----------|--------------------------------|
| **MT3608 IN+** | TP4057 OUT+ (battery 3.7-4.2V) | **Adjust to 5.0V before connecting LEDs!** |
| **MT3608 OUT+** | LED ring 5V | Regulated 5V for LEDs |
| LED ring DIN  | GPIO 13   | Through 330Ω resistor          |
| LED ring 5V   | **MT3608 OUT+** | + 1000µF capacitor to GND      |
| MPU6050 SDA   | GPIO 21   | I2C data                       |
| MPU6050 SCL   | GPIO 22   | I2C clock                      |
| MPU6050 VCC   | 3.3V      | **NOT 5V!**                    |
| Button        | GPIO 27   | Other leg to GND               |
| Buzzer +      | GPIO 15   | Buzzer - to GND                |
| Motor driver  | GPIO 12   | Via 2.2kΩ → transistor base    |
| Motor +       | TP4057 OUT+ | Battery voltage (3.7-4.2V OK for motor) |

**Critical:** MT3608 must be adjusted to exactly 5.0V with multimeter BEFORE connecting LED ring!

---

## 🐛 Troubleshooting

### Build Errors

**"Platform 'espressif32' not found"**
```bash
pio platform install espressif32
```

**Library errors**
```bash
pio lib install
```

### Upload Errors

**"Serial port not found"**
- Check USB cable (must be data cable, not charge-only)
- Install CP210x driver: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
- Try different USB port
- Check Device Manager (Windows) or `ls /dev/tty.*` (Mac)

**"Permission denied"**
```bash
# Mac/Linux
sudo chmod 666 /dev/ttyUSB0
```

### Hardware Issues

**MT3608 / Power Issues**
- MT3608 gets hot → Lower LED brightness in firmware
- LEDs flicker → Check battery voltage (should be >3.5V)
- Can't adjust MT3608 → Potentiometer may be at limit, try another module
- Voltage sags during animations → Add 100µF capacitor across MT3608 input

**LEDs don't light**
- **Check MT3608 adjusted to 5.0V** with multimeter!
- Check 330Ω resistor on data line
- Check 1000µF capacitor polarity (- to GND)
- Verify MT3608 OUT+ connected to LED ring 5V
- Check GPIO 13 connection

**Motor doesn't work**
- Verify transistor pinout (E-B-C)
- Check diode polarity (stripe to Motor +)
- Ensure 2.2kΩ resistor on base
- Motor + should go to **battery voltage** (TP4057 OUT+), not GPIO!

**MPU6050 "not found"**
- Check it's connected to 3.3V (not 5V!)
- Swap SDA/SCL if still not working
- Check I2C address (should be 0x68)

**Buzzer won't beep**
- Verify it's an **active** buzzer (has built-in oscillator)
- Check + goes to GPIO 15, - to GND
- Try different buzzer (may be defective)

**Serial Monitor shows nothing**
- Check baud rate is 115200
- Press EN button on ESP32 to reset

---

## 📊 Battery Life Estimates

With `LED_BRIGHTNESS = 80` and 2000mAh battery:

| Usage Pattern              | Estimated Runtime |
|---------------------------|-------------------|
| Idle (breathing LEDs)     | ~8-10 hours       |
| Moderate play (button/shake every 30s) | ~6-8 hours |
| Continuous animations     | ~2-3 hours        |

**Tips for longer battery:**
- Lower `LED_BRIGHTNESS` to 50
- Use fewer LEDs in animations
- Add sleep mode when idle >5 minutes

---

## 🚀 Next Steps

### ✅ Phase 1: Hardware & Basic Firmware (COMPLETE)
- Single-puck firmware with all components working
- 8 single-player games
- Interactive demo modes

### ✅ Phase 2: Game Logic (COMPLETE)
- 8 complete mini-games with scoring
- Player identification (unique puck IDs)
- Demo mode for showcasing

### ✅ Phase 3: Multi-Puck System (COMPLETE)
- ESP-NOW puck-to-puck communication
- 5 multiplayer games
- Web scoreboard with real-time updates
- Mobile control app for bar staff

### Phase 4: Enclosure & Deployment (IN PROGRESS)
- ✅ Complete enclosure specification (Forerunner design)
- ✅ CAD requirements documented
- 🔄 3D modeling and test prints
- 🔄 Drop resistance testing
- 🔄 Splash resistance validation
- 🔄 Bar pilot testing

### Phase 5: Future Enhancements
- Tournament brackets
- Bar vs Bar competitions (multiple locations)
- Offline score tracking (SD card storage)
- Spectator mode (watch games on phone)
- Custom game creator (mobile app)

---

## 📁 Project Structure

```
table-wars-puck/
├── platformio.ini                # PlatformIO configuration
├── src/
│   ├── main.cpp                 # Main firmware (tests + normal mode)
│   ├── main_tablewars.h         # TABLE WARS game system (8 single-player games)
│   ├── GameFramework.h          # Game framework classes
│   ├── GameFramework.cpp        # Game framework implementation
│   ├── wifi_sync.h              # ESP-NOW WiFi sync header
│   ├── wifi_sync.cpp            # ESP-NOW implementation
│   ├── multiplayer_games.h      # Multiplayer game classes
│   └── multiplayer_games_impl.h # Multiplayer game implementations
├── server/
│   ├── app.py                   # Flask scoreboard server
│   ├── requirements.txt         # Python dependencies
│   ├── templates/
│   │   └── leaderboard.html    # Web UI
│   └── README.md                # Server setup guide
├── mobile_app/
│   ├── lib/
│   │   ├── main.dart           # Flutter app entry
│   │   ├── puck_controller.dart # BLE controller
│   │   └── screens/
│   │       └── home_screen.dart # Main UI
│   ├── pubspec.yaml            # Flutter dependencies
│   └── README.md               # Mobile app guide
├── WIRING_GUIDE.md             # Detailed wiring instructions
├── MT3608_WIRING.md            # MT3608 boost converter setup
├── BUILD_CHECKLIST.md          # Step-by-step assembly guide
├── PARTS_LIST.md               # Complete shopping list
├── SCHEMATIC.txt               # Visual wiring diagram
├── ENCLOSURE_SPEC.md           # Complete 3D enclosure specification (Forerunner design)
├── CAD_CHECKLIST.md            # Quick reference for CAD designers
├── BUSINESS_PLAYBOOK.md        # 90-day validation → 12-month scale strategy
├── WEEK1_ACTION_PLAN.md        # Week 1 execution checklist (start here!)
├── GAMES.md                    # Single-player game documentation (8 games)
├── MULTIPLAYER.md              # Multiplayer features guide (ESP-NOW, 5 games, server, app)
└── README.md                   # This file
```

---

## 🛠️ Development Tips

### Adding Custom Animations

Edit the LED helper functions in `main.cpp`:

```cpp
void myCustomAnimation() {
  for (int i = 0; i < NUM_LEDS; i++) {
    strip.setPixelColor(i, COLOR_PURPLE);
    strip.show();
    delay(50);
  }
}
```

Call it from your mode:
```cpp
if (buttonPressed) {
  myCustomAnimation();
}
```

### Changing Pin Assignments

Edit the pin definitions:
```cpp
#define PIN_LED_RING  13  // Change to your preferred GPIO
```

**Safe GPIOs:** 4, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33

**Avoid:** 0, 2, 5, 6-11 (boot/flash pins)

### Serial Debugging

Add debug prints:
```cpp
Serial.println("Debug message");
Serial.printf("Value: %d\n", myValue);
```

---

## 📜 License

This is a personal project. Feel free to modify for your own bar game!

---

## 🙏 Acknowledgments

- **Adafruit** for excellent libraries
- **PlatformIO** for clean embedded development
- **ESP32** community for documentation

---

**Happy building! 🍻**
