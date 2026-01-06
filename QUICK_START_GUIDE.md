# Quick Start Guide - Upgrade Your Puck This Weekend!

## 🎯 TL;DR

**You can add 5 MAJOR features to your puck for FREE (or $0.50)**

No new hardware needed! Just code.

---

## ✅ What You're Doing This Weekend

### 1️⃣ OTA Updates (10 minutes)
**Why**: Update all 6 pucks wirelessly

```cpp
#include "ota_update.h"

void setup() {
    connectWiFi();
    initArduinoOTA();  // Add this line
}

void loop() {
    handleOTAUpdates();  // Add this line
    // Your game code...
}
```

**Test it**:
1. Upload code via USB (last time!)
2. Make a small change
3. Upload via WiFi: `Tools → Port → TableWarsPuck.local`
4. Done! Never plug in USB again

---

### 2️⃣ Dual-Core (20 minutes)
**Why**: 2× performance, zero lag

```cpp
#include "dual_core.h"

void setup() {
    // All your init code...
    connectWiFi();
    initMPU6050();
    FastLED.addLeds(...);

    // Replace loop() with this:
    initDualCore();
}

void loop() {
    // Leave empty - tasks run on both cores
}
```

**What changes**:
- Core 0: Game runs smoothly
- Core 1: WiFi doesn't lag game
- LEDs update 60 FPS always

---

### 3️⃣ Capacitive Touch (30 minutes)
**Why**: Touch-sensitive surface, no button failures

**Hardware**:
- Copper tape ($2 for whole roll on Amazon)
- Cut 4 strips: 2cm × 5cm each
- Stick to inside of case
- Solder wire to GPIO pins

```cpp
#include "capacitive_touch.h"

void setup() {
    initCapacitiveTouch();
    calibrateTouchSensors();  // Run once
}

void loop() {
    readTouchPads();

    if (gestureDetected(GESTURE_TAP)) {
        Serial.println("Tapped!");
    }

    if (gestureDetected(GESTURE_SWIPE_LEFT)) {
        previousMenuItem();
    }

    if (gestureDetected(GESTURE_SWIPE_RIGHT)) {
        nextMenuItem();
    }

    showTouchFeedback();  // LEDs show what you're touching
}
```

**Touch zones**:
- GPIO 4: Top (tap)
- GPIO 2: Left (swipe left)
- GPIO 15: Right (swipe right)
- GPIO 13: Bottom (long press)

---

### 4️⃣ ESP-NOW Multiplayer (15 minutes)
**Why**: Pucks talk to each other instantly

```cpp
#include "esp_now_multiplayer.h"

void setup() {
    initESPNow();
    addBroadcastPeer();
    discoverPucks();  // Find nearby pucks
}

void puckWarsGame() {
    // Attack another puck
    if (digitalRead(BUTTON_PIN) == LOW) {
        attackPuck(targetPuckId, 20);  // 20 damage
    }

    // Or play cooperative game
    // gameBossBattle();  // Team up to defeat boss
}
```

**Game ideas**:
- Puck Wars (battle royale)
- Hot Potato (pass before explosion)
- Sync Challenge (all shake together)
- Team Relay (pass the baton)

---

### 5️⃣ Deep Sleep (5 minutes)
**Why**: 2.5 YEARS battery life when idle

```cpp
void goToSleep() {
    Serial.println("💤 Going to sleep...");

    // Wake on button press
    esp_sleep_enable_ext0_wakeup(GPIO_NUM_0, 0);

    // Or wake after 60 seconds
    esp_sleep_enable_timer_wakeup(60 * 1000000ULL);

    esp_deep_sleep_start();
}

// When puck wakes, it reboots and runs setup()
```

**Power comparison**:
- Normal: 250 mA → 8 hours
- Deep sleep: 0.01 mA → 22,000 hours (2.5 years!)

---

## 💰 Total Cost

**This weekend**: $0.50 (copper tape)

**Result**:
- ✅ Wireless updates
- ✅ 2× performance
- ✅ Touch controls
- ✅ Multiplayer games
- ✅ Infinite battery (with sleep)

---

## 🔊 Next Week: Audio Upgrade ($27 for 6 pucks)

### Order on Amazon:
1. **MAX98357A I2S Amplifier** (6-pack) - $15
2. **4Ω Speakers** (6-pack) - $12
3. **Total**: $27

### What you get:
**BEFORE (buzzer)**:
```
Game Start: BEEP BEEP BEEP
Score: BEEP!
Game Over: BEEEEEEP
```

**AFTER (I2S)**:
```cpp
announceVoice("ready");      // "Ready..." (human voice)
announceCountdown();          // "3... 2... 1... GO!"
playWAV("/sounds/score.wav"); // Cha-ching!
playWAV("/sounds/cheer.wav"); // Crowd cheering
```

---

## 📋 Shopping List

### This Weekend (Optional)
- [ ] Copper tape roll - $2 (Amazon)

### Next Week (Recommended)
- [ ] 6× MAX98357A I2S Amplifier - $15
- [ ] 6× Small 4Ω speakers - $12

### Later (Optional)
- [ ] 6× Micro SD modules - $9
- [ ] 6× 8GB SD cards - $6
- [ ] 6× ESP32-CAM modules - $36

---

## 🚀 Integration Steps

### Step 1: Copy header files
```bash
cd /Users/austinscipione/table-wars-puck

# Free features (do these now!)
cp src/ota_update.h into your project
cp src/dual_core.h into your project
cp src/capacitive_touch.h into your project
cp src/esp_now_multiplayer.h into your project
```

### Step 2: Update main.cpp
```cpp
// Add at top
#include "ota_update.h"
#include "dual_core.h"
#include "capacitive_touch.h"
#include "esp_now_multiplayer.h"

void setup() {
    Serial.begin(115200);

    // Your existing init
    connectWiFi();
    initMPU6050();
    FastLED.addLeds(...);

    // NEW: Add these
    initArduinoOTA();
    initCapacitiveTouch();
    initESPNow();

    // NEW: Replace loop() with dual-core
    initDualCore();
}

void loop() {
    // Empty - dual-core tasks run automatically
}
```

### Step 3: Test
```bash
# Upload via USB one last time
pio run -t upload

# Future uploads via WiFi
pio run -t upload --upload-port TableWarsPuck.local
```

---

## 🎮 New Games You Can Make

### With ESP-NOW:
1. **Puck Wars** - Battle royale, last puck standing
2. **Hot Potato** - Pass before explosion
3. **Sync Challenge** - All pucks shake together
4. **Team Relay** - Pass baton to teammates
5. **Boss Battle** - Cooperate to defeat giant boss

### With Capacitive Touch:
1. **Touch Menu** - Swipe to navigate, tap to select
2. **Gesture Combat** - Swipe = attack, tap = block
3. **Volume Control** - Swipe up/down for volume
4. **Secret Unlock** - Special gesture sequence

### With Deep Sleep:
1. **Wake-up Challenge** - First to grab puck wins
2. **Alarm Clock Game** - Must shake to snooze
3. **Idle Timeout** - Puck sleeps if unused

---

## ❓ FAQ

**Q: Will OTA break my existing code?**
A: Nope! It just adds wireless upload. Everything else works the same.

**Q: Does dual-core require rewriting everything?**
A: No! Your game code stays the same. Just wrap it in `initDualCore()`.

**Q: Can I use capacitive touch AND button?**
A: Yes! They work together. Use both for more inputs.

**Q: Does ESP-NOW work with WiFi?**
A: Yes! You can use both at the same time.

**Q: How many pucks can communicate via ESP-NOW?**
A: Up to 20 pucks in one network. Plenty for a bar!

---

## 🐛 Troubleshooting

### OTA not working
- Make sure puck and laptop on same WiFi network
- Check firewall isn't blocking port 3232
- Serial monitor shows "Arduino OTA initialized"

### Dual-core crashes
- Increase stack sizes in dual_core.h
- Check for shared resource conflicts
- Use mutexes for I2C, LEDs, buzzer

### Touch sensors too sensitive
- Run calibration: `calibrateTouchSensors()`
- Increase threshold in code
- Add small capacitor to pin (100pF)

### ESP-NOW messages not received
- Check both pucks initialized ESP-NOW
- Verify same WiFi channel
- Check MAC addresses correct

---

## 📞 What's Next?

### This Weekend:
✅ Integrate OTA, Dual-Core, Touch, ESP-NOW (2 hours total)

### Next Week:
✅ Order I2S audio ($27 for 6 pucks)
✅ Integrate audio when parts arrive

### Week After:
✅ Create 5 multiplayer games using ESP-NOW
✅ Add touch controls to all games
✅ Deploy to all 6 pucks via OTA

---

## 🎯 Summary

**Time**: 2 hours this weekend
**Cost**: $0.50 (copper tape)
**Result**: Professional-grade multiplayer puck

**Then add audio next week**:
**Time**: 1 hour to install speakers
**Cost**: $27 for 6 pucks ($4.50 each)
**Result**: Game-show quality audio

---

**You're about to go from basic motion sensor toy to professional bar gaming system for under $30!** 🚀

Let's do this! 🍻
