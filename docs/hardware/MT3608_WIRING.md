# MT3608 Boost Converter - Wiring Guide

## ⚡ Power Flow Diagram

```
┌─────────────┐
│  3.7V LiPo  │
│  Battery    │
└──────┬──────┘
       │ PH2.0
       ▼
┌─────────────┐
│   TP4057    │ ◄─── USB-C charging
│  Charger    │
└──────┬──────┘
       │ OUT+ / OUT- (3.7-4.2V)
       │
       ├──────────────────┬─────────────────┐
       │                  │                 │
       ▼                  ▼                 ▼
   ┌─────────┐      ┌──────────┐    ┌─────────────┐
   │ MT3608  │      │  ESP32   │    │   Motor     │
   │ Boost   │      │  5V pin  │    │  (3.7-4.2V  │
   │ Module  │      │          │    │   is fine)  │
   └────┬────┘      └──────────┘    └─────────────┘
        │ OUT+ (regulated 5V)
        │
        ▼
   ┌──────────┐
   │ WS2812B  │
   │ LED Ring │
   │   5V     │
   └──────────┘
```

---

## 📋 Wiring Table

### MT3608 Connections

| MT3608 Pin | Connect To | Notes |
|------------|-----------|-------|
| IN+ | TP4057 OUT+ | Battery voltage (3.7-4.2V) |
| IN- | Common GND | Ground from TP4057 OUT- |
| OUT+ | LED ring 5V pad | Regulated 5V output |
| OUT- | Common GND | Tie to same GND rail |

### Complete Power Distribution

| Component | Power Source | Voltage | Notes |
|-----------|-------------|---------|-------|
| **ESP32** | TP4057 OUT+ | 3.7-4.2V | Has onboard regulator, works fine |
| **LED ring** | MT3608 OUT+ | 5V regulated | ✅ Proper voltage now! |
| **Motor** | TP4057 OUT+ | 3.7-4.2V | Works fine at battery voltage |
| **MPU6050** | ESP32 3.3V pin | 3.3V | No change |
| **Buzzer** | GPIO 15 | 3.3V | No change |

---

## 🔧 Initial Setup - IMPORTANT!

### Before Connecting LEDs: Adjust MT3608 to 5V

The MT3608 comes factory-set to a random voltage (usually 5-12V). You MUST adjust it to exactly 5V before connecting your LED ring!

#### You'll Need:
- Multimeter
- Small Phillips screwdriver (for the blue potentiometer)

#### Steps:

1. **Connect power to MT3608 ONLY** (no load yet):
   - TP4057 OUT+ → MT3608 IN+
   - TP4057 OUT- → MT3608 IN-
   - Leave MT3608 OUT+/OUT- disconnected

2. **Power on** (connect battery or USB to TP4057)

3. **Measure output voltage:**
   - Multimeter red probe → MT3608 OUT+
   - Multimeter black probe → MT3608 OUT-

4. **Adjust the blue potentiometer:**
   - Turn **clockwise** to increase voltage
   - Turn **counter-clockwise** to decrease voltage
   - Adjust until you read exactly **5.0V** (±0.1V is fine)

5. **Power off**, disconnect everything

6. **Now connect your LED ring** to MT3608 OUT+/OUT-

---

## ⚙️ Physical Assembly Tips

### Breadboard Layout

```
Power Rails:
┌─────────────────────────────────────────────────┐
│ RED (+)   TP4057 OUT+ (3.7-4.2V)                │ ← Battery voltage
│ BLK (-)   Common GND                            │
└─────────────────────────────────────────────────┘

MT3608 Module:
  - Sits in main breadboard area
  - IN+ to battery voltage rail (red)
  - IN- to GND rail (black)
  - OUT+ goes to LED ring 5V
  - OUT- to GND rail (black)

ESP32:
  - 5V pin to battery voltage rail (red)
  - GND pins to GND rail (black)
```

### Wire Gauge Recommendations

| Connection | Wire Gauge | Notes |
|------------|-----------|-------|
| Battery → TP4057 | 22 AWG | Handles charging + discharge current |
| TP4057 → MT3608 IN | 22 AWG | LED current flows here |
| MT3608 OUT → LED ring | 22 AWG | Up to 1A possible |
| TP4057 → ESP32 | 22 AWG | ESP32 draw + passthrough |
| All GND connections | 22 AWG | Return path for all current |
| Signal wires (GPIO) | 30 AWG | Low current, flexible |

---

## 🔍 Testing Procedure

### Test 1: Voltage Adjustment (No Load)

- [ ] Connect battery to TP4057
- [ ] Connect TP4057 OUT to MT3608 IN
- [ ] Measure MT3608 OUT voltage with multimeter
- [ ] Adjust to exactly 5.0V
- [ ] **Expected:** Stable 5.0V reading

### Test 2: LED Ring Connected (Light Load)

- [ ] Power off, connect LED ring to MT3608 OUT
- [ ] Upload `TEST_MODE_LEDS` to ESP32
- [ ] Power on
- [ ] Measure voltage at LED ring 5V pad
- [ ] **Expected:** 5.0V with LEDs running
- [ ] **Expected:** Bright, vivid colors (better than before!)

### Test 3: Full Load Test

- [ ] Upload `NORMAL_MODE` firmware
- [ ] Trigger button press (green flash)
- [ ] Trigger shake (rainbow burst)
- [ ] Monitor voltage during animations
- [ ] **Expected:** 5.0V stays stable (±0.2V acceptable)

### Test 4: Efficiency Check (Optional)

- [ ] Fully charge battery (4.2V)
- [ ] Run puck for 1 hour in idle mode (breathing LEDs)
- [ ] Measure battery voltage
- [ ] **Expected:** Battery drops ~0.2-0.3V
- [ ] **Calculate runtime:** ~6-8 hours on 2000mAh battery

---

## 📊 Current Draw Estimates (Updated)

With MT3608 boost converter @ ~93% efficiency:

| Condition | LED Current @ 5V | Input Current @ 3.7V | Total System |
|-----------|-----------------|---------------------|--------------|
| Idle (breathing cyan) | 50-80 mA | ~110-170 mA | ~200-280 mA |
| Button flash (green) | ~150 mA | ~200 mA | ~280 mA |
| Rainbow burst | ~150-200 mA | ~215-270 mA | ~300-350 mA |
| All LEDs white (max) | ~960 mA | ~1.3 A | ~1.4 A |

**Battery life @ 2000mAh:**
- Idle: ~8-10 hours
- Active play: ~6-8 hours
- Max brightness: ~1.5 hours

---

## ⚠️ Safety Notes

### DO:
✅ Adjust voltage BEFORE connecting LEDs
✅ Use multimeter to verify 5.0V output
✅ Connect all GND points together
✅ Use 22 AWG wire for power connections

### DON'T:
❌ Connect LEDs before adjusting voltage (could fry them at >5.5V!)
❌ Turn potentiometer while measuring with cheap meter (can arc)
❌ Exceed 2A output current (MT3608 limit)
❌ Short OUT+ to OUT- (will damage boost converter)

---

## 🔧 Troubleshooting

### MT3608 gets hot
- **Normal:** Warm to the touch during operation
- **Too hot to touch:** Output current too high, reduce LED brightness
- **Solution:** Lower `LED_BRIGHTNESS` to 60-80 in firmware

### Voltage sags during animations
- **Cause:** Insufficient input capacitance
- **Solution:** Add 100-220µF capacitor across MT3608 IN+/IN-
- **Already have:** 1000µF cap on LED ring output (that helps too!)

### LEDs flicker
- **Cause:** Loose connections or low battery
- **Check:** Battery voltage (should be >3.5V)
- **Check:** All power connections are solid

### Can't adjust voltage
- **Issue:** Potentiometer at min/max
- **Solution:** Module may be defective, try another from your pack of 10

---

## 📐 Module Dimensions

**MT3608 Module (typical):**
- Length: ~36mm
- Width: ~17mm
- Height: ~14mm (with potentiometer)
- Mounting holes: 2× M3 (optional)

**Fits easily on breadboard or can be soldered directly.**

---

## 🎯 Benefits of Adding MT3608

| Before (Battery Voltage) | After (MT3608 5V) |
|-------------------------|-------------------|
| LEDs dimmer at 3.7V | ✅ Full brightness at 5V |
| Colors shift (less blue) | ✅ Accurate RGB colors |
| Brightness varies with battery | ✅ Consistent until battery low |
| Voltage 3.7-4.2V (±14%) | ✅ Regulated 5.0V (±2%) |

---

## 🚀 You're All Set!

**Total cost:** ~$2 per puck for MT3608
**Benefit:** Professional-quality LED performance! 🌈

Adjust voltage, wire it up, and enjoy bright, accurate colors on your Table Wars pucks!
