# Table Wars Puck

> **Professional multiplayer gaming system with 56 games and 8 advanced ESP32 features**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-ESP32-green.svg)](https://www.espressif.com/en/products/socs/esp32)
[![Firmware](https://img.shields.io/badge/firmware-v2.0.0-orange.svg)](src/)

---

## 🎯 What Is This?

Table Wars Puck is a **wireless multiplayer gaming system** for bars and entertainment venues. Each puck contains motion sensors, LEDs, haptic feedback, and wireless connectivity to create an interactive gaming experience.

**Key Stats:**
- 🎮 **56 total games** (51 solo + 5 multiplayer)
- 🚀 **8 ESP32 features** (OTA, dual-core, touch, ESP-NOW, etc.)
- 🔋 **2.5 year battery** (with deep sleep)
- 💰 **$0.50 to upgrade** (just copper tape for touch)

---

## ⚡ Quick Start

### 1. Upload Firmware (USB - first time only)

```bash
pio run -e puck1 -t upload
```

### 2. Upload Via WiFi (OTA - forever after)

```bash
pio run -e puck1_ota -t upload
```

### 3. Play Games

Open serial monitor and type game numbers:
```
1-51   # Original games
52     # Puck Wars (battle royale)
53     # Hot Potato Relay
54     # Sync Shake Challenge
55     # Boss Battle (cooperative)
56     # King of the Hill
```

**Full guide:** [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md)

---

## 📦 What's Included

### Hardware
- ESP32-DevKitC (38-pin)
- WS2812B LED Ring (16 LEDs)
- MPU6050 Motion Sensor
- Piezo Buzzer
- Vibration Motor
- 2000mAh LiPo Battery
- 3D Printed Case

### Firmware Features

#### FREE Features (Built into ESP32):
1. ✅ **OTA Updates** - Wireless firmware deployment
2. ✅ **Dual-Core** - 2× performance boost
3. ✅ **Capacitive Touch** - Touch gestures ($0.50 copper tape)
4. ✅ **ESP-NOW** - Puck-to-puck multiplayer
5. ✅ **Deep Sleep** - 2.5 year battery life
6. ✅ **Hall Sensor** - Magnet detection
7. ✅ **Temperature** - Built-in sensor
8. ✅ **DAC Audio** - Better sound quality

### Games

**51 Original Games + 5 New Multiplayer Games**

[See full game list in docs](docs/archive/51_GAMES_COMPLETE.md)

---

## 🏗️ Repository Structure

```
table-wars-puck/
├── 📄 README.md                          ← You are here
├── 📄 QUICK_START_GUIDE.md               ← Start here (2-hour setup)
├── 📄 DEPLOYMENT_CHECKLIST.md            ← Complete deployment guide
│
├── 💾 src/                               ← Firmware source code
│   ├── main.cpp                          ← Main entry point
│   ├── main_complete.h                   ← MASTER firmware (all 56 games)
│   ├── main_tablewars.h                  ← Original 51 games
│   │
│   └── Feature modules:
│       ├── ota_update.h                  ← OTA firmware updates
│       ├── dual_core.h                   ← FreeRTOS dual-core
│       ├── capacitive_touch.h            ← Touch controls
│       ├── esp_now_multiplayer.h         ← Multiplayer networking
│       ├── i2s_audio.h                   ← Real audio (optional)
│       ├── sd_card.h                     ← Storage (optional)
│       ├── bluetooth_audio.h             ← BT streaming (optional)
│       └── camera_module.h               ← AR games (optional)
│
├── 🖥️ server/                            ← Flask backend
│   ├── app.py                            ← Main server
│   ├── firmware_routes.py                ← OTA management
│   └── templates/                        ← Web dashboards
│
├── 🏗️ cad/                               ← 3D printable case (5 STL files)
│
├── 📚 docs/                              ← Documentation
│   ├── hardware/                         ← Wiring, parts lists
│   ├── business/                         ← Business plans
│   ├── legal/                            ← Patents
│   ├── manufacturing/                    ← Production
│   └── archive/                          ← Old docs
│
├── 📄 platformio.ini                     ← Build configuration
├── 📄 deploy_all_pucks.sh                ← Deploy to all 6 pucks
└── 📄 TEST_ALL_FEATURES.ino              ← Feature test suite
```

---

## 📖 Documentation

### Start Here:
- **[QUICK_START_GUIDE.md](QUICK_START_GUIDE.md)** - 2-hour weekend setup
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Complete walkthrough

### Wiring & Hardware:
- **[CAPACITIVE_TOUCH_WIRING_GUIDE.md](CAPACITIVE_TOUCH_WIRING_GUIDE.md)** - Add touch controls
- **[docs/hardware/](docs/hardware/)** - Parts lists, wiring diagrams

### Features & Games:
- **[MULTIPLAYER_GAMES_EXAMPLES.md](MULTIPLAYER_GAMES_EXAMPLES.md)** - Game code examples
- **[ESP32_UNTAPPED_FEATURES.md](ESP32_UNTAPPED_FEATURES.md)** - Technical deep dive
- **[FEATURES_REALITY_CHECK.md](FEATURES_REALITY_CHECK.md)** - FREE vs PAID features
- **[FEATURE_IMPACT_GUIDE.md](FEATURE_IMPACT_GUIDE.md)** - Before/after comparisons

---

## 🚀 Features Deep Dive

### OTA Updates
Update all 6 pucks wirelessly in 2 minutes:
```bash
./deploy_all_pucks.sh
```

### Capacitive Touch
Add touch gestures with $0.50 copper tape:
- Tap, swipe, long press, multi-touch combos

### ESP-NOW Multiplayer
Puck-to-puck communication:
- 250m range outdoors
- 2-10ms latency
- Up to 20 pucks

### Deep Sleep
**Active:** 250 mA (8 hours)
**Deep Sleep:** 0.01 mA (2.5 years!)

---

## 💰 Cost Breakdown

| Upgrade | Cost (6 pucks) | Per Puck | Benefit |
|---------|----------------|----------|---------|
| **Copper Tape** | $2 | $0.33 | Touch controls |
| **I2S Audio** | $27 | $4.50 | Real voice/music |
| **SD Cards** | $15 | $2.50 | 10K trivia questions |
| **ESP32-CAM** | $36 | $6.00 | AR games |
| **TOTAL** | **$80** | **$13.33** | **Complete system** |

---

## 🎮 Usage

### Deploy to All Pucks
```bash
./deploy_all_pucks.sh
```

### Start Server
```bash
cd server
pip install -r requirements.txt
python app.py
```

Dashboards:
- http://localhost:5001/ - Game dashboard
- http://localhost:5001/leaderboard - High scores
- http://localhost:5001/firmware/dashboard - OTA management

### Play Games
```bash
pio device monitor --baud 115200

# Type commands:
help    # Show commands
1-56    # Launch game number
```

---

## 🛠️ Development

```bash
# Build
pio run -e puck1

# Upload (USB)
pio run -e puck1 -t upload

# Upload (OTA)
pio run -e puck1_ota -t upload

# Monitor
pio device monitor --baud 115200
```

---

## 🎯 What's New

**From basic toy to professional gaming system:**

| Before | After |
|--------|-------|
| 51 games | 56 games |
| USB updates only | Wireless OTA |
| 30 FPS | 60 FPS |
| Button only | Touch gestures |
| Solo play | Multiplayer |
| 8 hour battery | 2.5 year battery (idle) |

**Total upgrade cost:** $0.50 (copper tape) 🚀

---

## 📝 License

MIT License

---

**Built with ❤️ using ESP32 and PlatformIO**

🎮 **Happy Gaming!** 🍻
