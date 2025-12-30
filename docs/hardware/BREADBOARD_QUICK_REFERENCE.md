# TABLE WARS PUCK - Quick Reference Card
## Print this and keep it next to your breadboard!

---

## ⚠️ BEFORE YOU START: LED Ring Prep

**WS2812B LED rings have SOLDER PADS, not wires!**

**Prep Step (10 minutes):**
1. Solder 3 wires to LED ring pads FIRST:
   - RED wire (6") → 5V pad
   - BLACK wire (6") → GND pad
   - GREEN wire (6") → DIN pad
2. Use 22 AWG solid core wire (inserts into breadboard)
3. Test: Tug wires gently - should not pull out

**See LED_RING_PREP_GUIDE.md for detailed soldering instructions!**

---

## 🔌 Pin Connections At-a-Glance

### ESP32 to Breadboard Position (Rows 15-34)

| ESP32 Pin | Row | Column | Connects To | Wire Color |
|-----------|-----|--------|-------------|------------|
| **3.3V** | 15 | D | Left Red Rail (+) | Red |
| **GND** | 15 | F | Left Blue Rail (-) | Black |
| **GND** | 21 | F | Left Blue Rail (-) | Black |
| **GPIO 13** | 29 | E | 330Ω resistor → LED DIN | - |
| **GPIO 15** | 29 | F | Buzzer + | Red |
| **GPIO 21** | 20 | F | MPU6050 SDA | Green |
| **GPIO 22** | 17 | F | MPU6050 SCL | Yellow |
| **GPIO 27** | 25 | D | Button (Row 50) | Blue |
| **GPIO 12** | 27 | E | 2.2kΩ → Transistor Base | Orange |

---

## 🔋 Power System Connections

### TP4057 Charger (Rows 5-8, Right Side)

| Pin | Row | Column | Connects To | Wire Color |
|-----|-----|--------|-------------|------------|
| **BAT+** | 5 | H | Battery Red | Red |
| **BAT-** | 6 | I | Battery Black | Black |
| **OUT+** | 7 | H | MT3608 IN+ & Motor+ | Red |
| **OUT-** | 8 | I | Right Blue Rail (-) | Black |

### MT3608 Boost Converter (Rows 40-43, Right Side)

| Pin | Row | Column | Connects To | Wire Color |
|-----|-----|--------|-------------|------------|
| **IN+** | 40 | H | TP4057 OUT+ (Row 7) | Red |
| **IN-** | 41 | I | Right Blue Rail (-) | Black |
| **OUT+** | 42 | H | LED Ring 5V (Adjust to 5.0V!) | Red |
| **OUT-** | 43 | I | Right Blue Rail (-) | Black |

---

## 🌈 LED Ring Connections

| LED Wire | Breadboard Position | Notes |
|----------|---------------------|-------|
| **5V** (Red) | Row 42, Col H (MT3608 OUT+) | 5V regulated |
| **GND** (Black) | Right Blue Rail (-) | Ground |
| **DIN** (Green/White) | Row 29, Col C (via 330Ω resistor) | Data input |

**Add 1000µF Capacitor:**
- Positive (+): Row 42, Col I
- Negative (-): Row 43, Col J (stripe marking)

---

## 📐 MPU6050 Sensor Connections

| MPU Pin | Breadboard Position | Wire Color |
|---------|---------------------|------------|
| **VCC** | Left Red Rail (+) = 3.3V | Red |
| **GND** | Left Blue Rail (-) | Black |
| **SCL** | Row 17, Col H (GPIO 22) | Yellow |
| **SDA** | Row 20, Col H (GPIO 21) | Green |

⚠️ **Use 3.3V NOT 5V!**

---

## 🔘 Button Connections (Rows 50-52)

| Button Leg | Breadboard Position | Connects To |
|-----------|---------------------|-------------|
| **Leg 1** | Row 50, Col D | GPIO 27 (Row 25, Col D) via jumper |
| **Leg 2** | Row 52, Col D | Left Blue Rail (-) GND |

---

## 🔊 Buzzer Connections

| Buzzer Wire | Breadboard Position | Notes |
|------------|---------------------|-------|
| **+ (Red/Long)** | Row 29, Col H (GPIO 15) | Positive |
| **- (Black/Short)** | Left Blue Rail (-) | Ground |

---

## 📳 Motor + Transistor Circuit (Row 55)

### Transistor Pinout (S8050/2N2222, flat side LEFT):

| Pin | Row | Column | Connects To |
|-----|-----|--------|-------------|
| **EMITTER** | 55 | A | Left Blue Rail (-) GND |
| **BASE** | 55 | B | 2.2kΩ resistor from GPIO 12 |
| **COLLECTOR** | 55 | C | Motor - (black wire) |

### Motor Wires:

| Motor Wire | Connects To | Position |
|-----------|-------------|----------|
| **+ (Red)** | TP4057 OUT+ | Row 7, Col H (battery voltage) |
| **- (Black)** | Transistor COLLECTOR | Row 55, Col C |

### Flyback Diode (1N4148):

| Diode End | Position | Notes |
|-----------|----------|-------|
| **Cathode (stripe)** | Row 7, Col I | Toward Motor + |
| **Anode** | Row 55, Col D | Toward Motor - |

---

## ⚡ Power Rail Setup

### Left Side:
- **Red Rail (+)** = 3.3V from ESP32 (Row 15, Col D)
- **Blue Rail (-)** = GND from ESP32 (Rows 15, 21, Col F)

### Right Side:
- **Red Rail (+)** = 5V from MT3608 OUT+ (Row 42, Col H)
- **Blue Rail (-)** = GND from MT3608/TP4057

### Bridge:
- Connect Left Blue Rail ←→ Right Blue Rail (across top)

---

## 🔧 Resistor Placements

| Resistor | Value | Position | Purpose |
|----------|-------|----------|---------|
| **R1** | 330Ω | Row 29, Col B-C | LED data line protection |
| **R2** | 2.2kΩ | Row 27 → Row 55, Col B | Transistor base current limit |

---

## ⚠️ Critical Polarity Warnings

### 🔴 GET THESE RIGHT OR COMPONENTS DIE:

1. **1000µF Capacitor:**
   - ✅ Positive (+): Row 42, Col I
   - ✅ Negative (- stripe): Row 43, Col J
   - ❌ Backwards = EXPLOSION 💥

2. **1N4148 Diode:**
   - ✅ Cathode (stripe): Row 7, Col I (Motor +)
   - ✅ Anode: Row 55, Col D (Motor -)
   - ❌ Backwards = Transistor damage

3. **Transistor (S8050/2N2222):**
   - ✅ Flat side faces LEFT
   - ✅ E-B-C from left to right (Row 55, Cols A-B-C)
   - ❌ Wrong orientation = No motor control

4. **MPU6050:**
   - ✅ VCC to 3.3V (Left Red Rail)
   - ❌ VCC to 5V = Sensor DEAD

5. **MT3608 Voltage:**
   - ✅ Adjust to 5.0V BEFORE connecting LEDs
   - ❌ Higher voltage = LEDs DEAD

---

## 🧪 Pre-Power Checklist (30 seconds)

Before connecting battery:

- [ ] ESP32 in Rows 15-34, straddles gap ✓
- [ ] Power rails connected and bridged ✓
- [ ] MT3608 adjusted to 5.0V (use multimeter!) ✓
- [ ] Capacitor: + to Row 42, - to Row 43 ✓
- [ ] Diode: stripe to Row 7 (Motor +) ✓
- [ ] Transistor: flat side left, E-B-C at Row 55 ✓
- [ ] MPU6050 on 3.3V rail (NOT 5V!) ✓
- [ ] All GND rails bridged together ✓

---

## 🎯 Quick Troubleshooting

| Problem | Check This First |
|---------|------------------|
| **ESP32 won't power** | Battery connected? TP4057 BAT+/BAT- correct? |
| **LEDs don't light** | MT3608 = 5.0V? Row 29 Col C connected? Capacitor polarity? |
| **LEDs dim/wrong colors** | MT3608 voltage? Should be 5.0V not 3.7V |
| **Button doesn't work** | Row 50 Col B to Row 25 Col A? Row 52 to GND? |
| **Motor doesn't vibrate** | Transistor E-B-C correct? Row 55 wiring? Diode backwards? |
| **MPU6050 "Not found"** | On 3.3V not 5V? SCL/SDA swapped? Rows 17, 20 connections? |
| **Buzzer doesn't beep** | Row 29 Col H to GPIO 15? Polarity correct? |

---

## 📊 Expected Voltages (Use Multimeter)

| Test Point | Expected Voltage |
|-----------|------------------|
| Left Red Rail (+) | 3.2-3.4V (3.3V) |
| Right Red Rail (+) / Row 42 Col H | 4.9-5.1V (5.0V) |
| All Blue Rails (-) | 0V (GND) |
| TP4057 OUT+ (Row 7 Col H) | 3.7-4.2V (battery) |
| GPIO 15 when buzzing | 3.3V |
| GPIO 12 when motor on | 3.3V |

---

## 🎨 Component Color Guide (For Organization)

| Component | Suggested Wire Color |
|-----------|---------------------|
| **3.3V power** | Red |
| **5V power** | Red (or Orange) |
| **GND** | Black |
| **LED DIN** | White or Green |
| **MPU SCL** | Yellow |
| **MPU SDA** | Green |
| **Button** | Blue |
| **Buzzer +** | Red or Orange |
| **Motor +** | Red |
| **Motor -** | Black |
| **GPIO 12 (motor control)** | Orange or Purple |

---

## ⏱️ Build Time Estimates

| Step | Time | Cumulative |
|------|------|------------|
| Insert ESP32, set power rails | 5 min | 5 min |
| Install TP4057 + MT3608, adjust voltage | 10 min | 15 min |
| Connect LED ring + capacitor | 10 min | 25 min |
| Connect MPU6050 | 5 min | 30 min |
| Connect button | 5 min | 35 min |
| Connect buzzer | 3 min | 38 min |
| Build motor circuit (transistor + diode) | 15 min | 53 min |
| Double-check all connections | 7 min | **60 min** |
| First power-on test | - | **1 hour** |

**Total: About 1 hour for careful, methodical build**

---

## 📱 Upload & Test Commands

```bash
# Navigate to project
cd /Users/austinscipione/table-wars-puck

# Upload firmware
pio run --target upload

# Open serial monitor
pio device monitor
```

**Expected boot sequence:**
1. "ESP32 initialized"
2. "MPU6050 found at 0x68"
3. LEDs spin animation (cyan)
4. Buzzer beep
5. "System ready!"

---

## 🎮 Success = All These Work:

✅ LEDs: Bright rainbow animation
✅ Button: Press → Green flash + beep + vibrate
✅ Shake: Rainbow burst + continuous vibration
✅ Serial: Clean debug output, no errors

---

## 📞 Need More Detail?

| File | Description |
|------|-------------|
| `BREADBOARD_BUILD_GUIDE_DETAILED.md` | Step-by-step with full explanations |
| `BREADBOARD_DIAGRAM_VISUAL.md` | Visual breadboard layout diagram |
| `WIRING_GUIDE.md` | Permanent solder build guide |
| `MT3608_WIRING.md` | Boost converter setup details |

---

**🖨️ PRINT THIS PAGE and keep it at your workbench!**

**Legend:**
- ✅ = Correct / Good
- ❌ = Wrong / Will break
- ⚠️ = Warning / Important
- 🔴 = Critical / Dangerous

---

**Happy Building! You've got this! 🚀**

*Questions? Check the detailed guide or ask for help!*
