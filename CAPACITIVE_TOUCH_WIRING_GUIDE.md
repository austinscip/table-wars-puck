# Capacitive Touch Wiring Guide

## 🎯 Overview

Add touch controls to your puck using ESP32's **built-in** capacitive touch sensors. No external chips needed!

**Cost**: $0.50 (just copper tape)
**Time**: 30 minutes
**Difficulty**: Easy

---

## 📦 Materials Needed

### Required:
- **Copper tape** (2cm wide) - $2 for entire roll on Amazon
  - Search: "copper foil tape adhesive"
  - Need about 20cm total per puck
- **22 AWG wire** - You already have this
- **Solder** - You already have this

### Optional:
- **100pF capacitors** (4x) - Makes sensors more stable ($0.50)
- **Electrical tape** - For insulation

---

## 🔌 ESP32 Touch Pins

The ESP32 has **10 built-in capacitive touch sensors**:

| Touch Pin | GPIO Pin | Physical Pin | Recommended Use |
|-----------|----------|--------------|-----------------|
| **T0** | GPIO 4 | Pin 26 | Top (Main button) |
| **T2** | GPIO 2 | Pin 24 | Left (Swipe left) |
| **T4** | GPIO 13 | Pin 16 | Bottom (Long press) |
| **T6** | GPIO 14 | Pin 13 | Right (Swipe right) |

We'll use 4 touch pads for best results.

---

## 📐 Touch Pad Layout

```
╔═══════════════════════╗
║                       ║
║      [TOP - T0]       ║  ← Tap to select
║                       ║
║  [LEFT]     [RIGHT]   ║  ← Swipe left/right
║   T2           T6     ║
║                       ║
║    [BOTTOM - T4]      ║  ← Long press for menu
║                       ║
╚═══════════════════════╝
```

### Touch Zone Sizes:
- **Top**: 5cm × 3cm (main tap area)
- **Left/Right**: 3cm × 3cm (swipe zones)
- **Bottom**: 4cm × 2cm (long press)

---

## 🛠️ Step-by-Step Instructions

### Step 1: Cut Copper Tape

Cut 4 pieces of copper tape:

1. **Top pad**: 5cm × 3cm
2. **Left pad**: 3cm × 3cm
3. **Right pad**: 3cm × 3cm
4. **Bottom pad**: 4cm × 2cm

**Tip**: Use scissors, but wipe blades after (copper dulls them).

---

### Step 2: Stick Copper Tape

**Inside the puck case** (so it's invisible):

1. Clean surface with rubbing alcohol
2. Peel backing from copper tape
3. Stick firmly, smooth out bubbles
4. Press edges down hard

**Important**:
- Don't overlap pads (leave 1cm gap between them)
- Make sure tape doesn't touch metal components inside
- Position where you naturally touch the puck

---

### Step 3: Solder Wires

For each copper pad:

1. Strip 5mm of wire
2. Tin the wire with solder
3. Touch soldering iron to corner of copper tape
4. Add small amount of solder to tape
5. Press tinned wire into solder
6. Hold for 2 seconds until cool

**Wire colors** (if you have colored wire):
- Red = Top (GPIO 4)
- Yellow = Left (GPIO 2)
- Green = Right (GPIO 14)
- Blue = Bottom (GPIO 13)

---

### Step 4: Connect to ESP32

Route wires to ESP32 pins:

| Copper Pad | Wire → | ESP32 Pin |
|------------|--------|-----------|
| Top | Red wire | GPIO 4 (Pin 26) |
| Left | Yellow wire | GPIO 2 (Pin 24) |
| Right | Green wire | GPIO 14 (Pin 13) |
| Bottom | Blue wire | GPIO 13 (Pin 16) |

**Pinout reference**:
```
ESP32-DevKitC (38-pin)

   3V3  [ ][ ] GND
   EN   [ ][ ] GPIO 23
GPIO 36  [ ][ ] GPIO 22
GPIO 39  [ ][ ] TX
GPIO 34  [ ][ ] RX
GPIO 35  [ ][ ] GPIO 21
GPIO 32  [ ][ ] GND
GPIO 33  [ ][ ] GPIO 19
GPIO 25  [ ][ ] GPIO 18
GPIO 26  [ ][ ] GPIO 5
GPIO 27  [ ][ ] GPIO 17
GPIO 14  [ ][ ] GPIO 16  ← Bottom (T6)
GPIO 12  [ ][ ] GPIO 4   ← Top (T0)
   GND  [ ][ ] GPIO 0
GPIO 13  [ ][ ] GPIO 2   ← Left (T2)
GPIO 15  [ ][ ] GPIO 15
GPIO 2   [ ][ ] GPIO 8
   GND  [ ][ ] GPIO 7
```

---

### Step 5: Add Capacitors (Optional but Recommended)

For each touch pin, add a **100pF capacitor** between the GPIO pin and GND:

```
GPIO 4 ──┬── 100pF ── GND
         │
         └── Copper Pad
```

**Why?** Reduces false triggers from electrical noise.

**Where to buy**: Search Amazon for "100pF ceramic capacitor"
**Cost**: $0.50 for 100 capacitors

---

### Step 6: Insulate (Important!)

Cover copper tape with electrical tape or kapton tape:

**Why?**
- Prevents shorts if case is metal
- Protects from skin oils/sweat
- Makes touch more consistent

**Don't skip this step!**

---

## 💻 Software Setup

### Upload Test Code

1. Copy `capacitive_touch.h` to your project
2. Upload `TEST_ALL_FEATURES.ino`
3. Open serial monitor (115200 baud)
4. Type `touch` to run touch test

### Calibration

The code auto-calibrates, but you can manually adjust:

```cpp
// In capacitive_touch.h, line 15:
#define TOUCH_THRESHOLD 40  // Lower = more sensitive
                            // Higher = less sensitive

// Recommended values:
// 30 = Very sensitive (may get false triggers)
// 40 = Default (good for most cases)
// 50 = Less sensitive (good if getting false triggers)
```

### Test It

Serial monitor output:
```
═══════════════════════════════════
TEST 2: CAPACITIVE TOUCH
═══════════════════════════════════
Touch the puck surface for 10 seconds...

✓ Tap 1 detected!
✓ Tap 2 detected!
◀️ Swipe Left!
▶️ Swipe Right!

✅ Capacitive Touch Test Complete (4 taps detected)
```

---

## 🎮 Usage in Games

### Example 1: Menu Navigation

```cpp
void navigateMenu() {
    readTouchPads();

    if (gestureDetected(GESTURE_TAP)) {
        selectMenuItem();  // Tap = select
    }

    if (gestureDetected(GESTURE_SWIPE_LEFT)) {
        previousMenuItem();  // Swipe left = back
    }

    if (gestureDetected(GESTURE_SWIPE_RIGHT)) {
        nextMenuItem();  // Swipe right = next
    }

    if (gestureDetected(GESTURE_LONG_PRESS)) {
        exitMenu();  // Hold = exit
    }

    showTouchFeedback();  // LEDs show what you're touching
}
```

### Example 2: Volume Control

```cpp
void adjustVolume() {
    readTouchPads();

    if (touchPadActive(TOUCH_PAD_TOP)) {
        volumeUp();
        Serial.println("Volume +");
    }

    if (touchPadActive(TOUCH_PAD_BOTTOM)) {
        volumeDown();
        Serial.println("Volume -");
    }

    showTouchFeedback();
}
```

### Example 3: Secret Gesture Unlock

```cpp
// Unlock special mode with: Left → Right → Top → Top
if (gestureSequence("LEFT RIGHT TAP TAP")) {
    unlockSecretMode();
    Serial.println("🔓 Secret mode unlocked!");
}
```

---

## 🐛 Troubleshooting

### Touch Not Detected

**Problem**: Serial monitor shows no touches

**Solutions**:
1. Check wiring (use multimeter to verify connections)
2. Run calibration: `calibrateTouchSensors()`
3. Lower threshold: `TOUCH_THRESHOLD = 30`
4. Check copper tape is making good contact with wire

### Too Sensitive (False Triggers)

**Problem**: Touch detected when not touching

**Solutions**:
1. Increase threshold: `TOUCH_THRESHOLD = 50`
2. Add 100pF capacitor between GPIO and GND
3. Check copper pads aren't touching metal components
4. Verify pads have 1cm gap between them
5. Cover pads with electrical tape

### Intermittent Detection

**Problem**: Sometimes works, sometimes doesn't

**Solutions**:
1. Check solder joints (re-solder if needed)
2. Add capacitors (reduces noise)
3. Keep wires away from high-current components
4. Use shielded wire (wrap in aluminum foil + ground)

### Wrong Gesture Detected

**Problem**: Swipe detected as tap, etc.

**Solutions**:
1. Adjust timing in code:
   ```cpp
   #define TAP_TIME_MIN 50      // Minimum tap time (ms)
   #define TAP_TIME_MAX 300     // Maximum tap time (ms)
   #define LONG_PRESS_TIME 1000 // Long press threshold (ms)
   ```
2. Practice consistent gestures
3. Watch serial monitor to see raw values

---

## 📊 Touch Pad Values (for debugging)

Open serial monitor and type `touch`:

```
Touch Pad Values:
T0 (GPIO 4):  12  ← Touching (low value)
T2 (GPIO 2):  45  ← Not touching
T4 (GPIO 13): 42  ← Not touching
T6 (GPIO 14): 11  ← Touching (low value)

Threshold: 40
```

**Reading values**:
- **< 20**: Definitely touching
- **20-40**: Maybe touching (adjust threshold)
- **> 40**: Not touching

---

## 💡 Advanced Tips

### Tip 1: Use Larger Pads

Bigger copper pads = more reliable detection:
- **Good**: 5cm × 3cm
- **Better**: 7cm × 4cm
- **Best**: Cover entire side of puck

### Tip 2: Multi-Touch Combos

Detect two-finger gestures:

```cpp
if (touchPadActive(TOUCH_PAD_TOP) && touchPadActive(TOUCH_PAD_BOTTOM)) {
    Serial.println("Two-finger press!");
    triggerSpecialMove();
}
```

### Tip 3: Proximity Detection

Touch sensors work through plastic! Detect hand nearby:

```cpp
if (touchValue(TOUCH_PAD_TOP) < 35) {  // Not quite touching
    Serial.println("Hand nearby...");
    dimLEDs();  // Prepare for touch
}
```

### Tip 4: Touch Wheel

Arrange pads in circle for rotary control:

```
     [TOP]
   /       \
[LEFT]   [RIGHT]
   \       /
    [BOTTOM]
```

Detect clockwise/counter-clockwise rotation!

---

## 📸 Photo Guide

### Good Copper Tape Placement:
```
✅ Smooth, flat application
✅ Good solder connection
✅ Wires secured with hot glue
✅ 1cm gap between pads
✅ Covered with electrical tape
```

### Bad Copper Tape Placement:
```
❌ Wrinkled tape (air bubbles)
❌ Touching metal components
❌ Overlapping pads
❌ Loose wire connection
❌ No insulation
```

---

## 🎯 What You Get

**Before** (button only):
- 1 input (press button)
- Mechanical wear
- Accidental presses

**After** (capacitive touch):
- 6+ inputs (tap, swipe, hold, combos)
- No mechanical wear
- More intuitive
- Touch = instant feedback (LEDs light up)

---

## ⏱️ Time Breakdown

1. **Cut copper tape** - 5 min
2. **Stick pads inside case** - 5 min
3. **Solder wires** - 10 min
4. **Connect to ESP32** - 5 min
5. **Test & calibrate** - 5 min

**Total**: 30 minutes per puck

**For 6 pucks**: ~3 hours (do while watching TV!)

---

## 🛒 Shopping List

| Item | Quantity | Cost | Where |
|------|----------|------|-------|
| Copper tape (2cm × 5m) | 1 roll | $2.00 | Amazon |
| 100pF capacitors | 24 (4 per puck) | $0.50 | Amazon/DigiKey |
| Electrical tape | 1 roll | $1.00 | Hardware store |
| **TOTAL** | - | **$3.50** | **All 6 pucks!** |

**Per puck**: $0.58

---

## ✅ Final Checklist

Before closing case:

- [ ] All 4 copper pads stuck firmly
- [ ] Wires soldered to pads
- [ ] Wires connected to correct GPIO pins
- [ ] Capacitors added (optional)
- [ ] Pads covered with electrical tape
- [ ] Test code uploaded
- [ ] All touches detected in serial monitor
- [ ] No false triggers
- [ ] LEDs respond to touch

---

## 🎮 Ready to Use!

Your puck now has:
- ✅ Tap to select
- ✅ Swipe left/right to navigate
- ✅ Long press for menu
- ✅ Multi-touch combos
- ✅ LED touch feedback

**Next**: Add to all your games! See `main_tablewars_v2_UPGRADED.h` for examples.

---

**Questions?** Check the troubleshooting section or serial monitor debug output!
