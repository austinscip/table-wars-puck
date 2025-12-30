# Table Wars Puck - Wiring Guide

## ⚡ RECOMMENDED: Professional Build with MT3608 Boost Converter

This guide uses the **MT3608 DC-DC boost converter** to provide proper 5V power to your LED ring. This gives you:
- ✅ **Brighter LEDs** (full 5V vs dim 3.7V)
- ✅ **Accurate colors** (especially blues!)
- ✅ **Consistent brightness** (doesn't fade as battery drains)
- ✅ **Professional results** from day one

**Cost:** ~$1.50 per puck (10-pack for $10-15 on Amazon)

---

## 📋 Complete Wiring Table (WITH MT3608)

### Power Distribution Overview

```
LiPo Battery → TP4057 Charger → MT3608 Boost → 5V to LED Ring
                               ↓
                          3.7-4.2V to ESP32 + Motor
```

### Step 1: Power Rails Setup

| From                    | To                          | Notes                                    |
|-------------------------|----------------------------|------------------------------------------|
| LiPo PH2.0 connector    | TP4057 BAT+ / BAT-         | Red = BAT+, Black = BAT-                |
| TP4057 OUT+             | MT3608 IN+ **AND** ESP32 5V pin | Split to both destinations      |
| TP4057 OUT-             | Common GND bus             | Create GND rail on breadboard          |
| MT3608 IN-              | Common GND bus             | Share GND with everything               |
| MT3608 OUT+             | LED ring 5V pad            | **Regulated 5V for LEDs**               |
| MT3608 OUT-             | Common GND bus             | Tie all GNDs together                   |
| ESP32 GND               | Common GND bus             | Connect all GNDs together               |
| ESP32 3V3               | MPU6050 VCC                | 3.3V supply for sensor                  |

**⚠️ CRITICAL: Adjust MT3608 to exactly 5.0V BEFORE connecting LEDs!** (See MT3608 Setup section below)

---

### Step 2: MT3608 Voltage Adjustment (ONE-TIME SETUP)

**Do this FIRST before connecting any LEDs!**

#### You'll Need:
- Multimeter
- Small Phillips screwdriver

#### Procedure:

1. **Connect power to MT3608 only:**
   - TP4057 OUT+ → MT3608 IN+
   - TP4057 OUT- → MT3608 IN-
   - **Leave OUT+ and OUT- disconnected** (no load yet)

2. **Power on** (connect battery or plug USB-C into TP4057)

3. **Measure output voltage:**
   - Multimeter red probe → MT3608 OUT+
   - Multimeter black probe → MT3608 OUT- (or GND)
   - Note the voltage (factory setting is usually 5-12V)

4. **Adjust the blue potentiometer:**
   - Turn **clockwise** to increase voltage
   - Turn **counter-clockwise** to decrease voltage
   - Adjust until multimeter reads **5.0V** (±0.1V is fine, 4.9-5.1V acceptable)

5. **Verify stability:**
   - Watch for 30 seconds - voltage should stay constant
   - If it drifts, fine-tune adjustment

6. **Power off and disconnect**

7. ✅ **Now you can connect your LED ring to MT3608 OUT+/OUT-**

**Note:** Do this once per MT3608 module. The setting will stay unless you turn the potentiometer.

---

### Step 3: WS2812B LED Ring

| Component               | Connection                 | Notes                                    |
|-------------------------|----------------------------|------------------------------------------|
| LED ring DIN            | **330Ω resistor** → GPIO 13| Resistor protects data line             |
| LED ring 5V             | **MT3608 OUT+**            | Regulated 5V from boost converter        |
| LED ring GND            | Common GND                 |                                          |
| **1000µF capacitor**    | Between LED 5V and GND     | **Negative leg to GND!**                |

**Capacitor placement:** Solder the 1000µF cap **directly across the LED ring's power pads** (5V and GND), close to the ring. This prevents voltage spikes when LEDs change.

**Polarity:** Electrolytic capacitors have polarity! The stripe or minus marking goes to GND.

---

### Step 4: MPU6050 Motion Sensor (I2C)

| MPU6050 Pin | ESP32 Pin    | Notes                         |
|-------------|-------------|-------------------------------|
| VCC         | 3.3V        | **NOT 5V!**                   |
| GND         | GND         | Common ground                 |
| SCL         | GPIO 22     | I2C clock                     |
| SDA         | GPIO 21     | I2C data                      |
| XDA         | (leave unconnected) |                       |
| XCL         | (leave unconnected) |                       |
| AD0         | (leave unconnected) | Defaults to address 0x68 |
| INT         | (leave unconnected) | Not using interrupt  |

---

### Step 5: Button

| Component    | Connection          | Notes                              |
|-------------|---------------------|-------------------------------------|
| Button leg 1 | GPIO 27            | We enable internal pull-up         |
| Button leg 2 | GND                | Button pulls GPIO 27 to GND when pressed |

**No external resistor needed** - code uses `INPUT_PULLUP`.

---

### Step 6: Active Piezo Buzzer (2-wire)

| Buzzer Wire | Connection | Notes                        |
|------------|-----------|------------------------------|
| + (red)    | GPIO 15   | Driven HIGH to beep          |
| - (black)  | GND       | Common ground                |

**Note:** Active buzzers have built-in oscillator. Just apply voltage to beep.

---

### Step 7: Vibration Motor + Transistor Driver

This is the trickiest part. Follow carefully!

#### Parts needed:
- 1× mini vibration motor (3V)
- 1× NPN transistor (S8050 or 2N2222)
- 1× 2.2kΩ resistor (base resistor)
- 1× 1N4148 diode (flyback protection)

#### Wiring:

```
ESP32 GPIO 12 ──[2.2kΩ]──┬── Transistor BASE
                          │
                      GND ─┴── Transistor EMITTER

TP4057 OUT+ (3.7-4.2V) ──┬──── Motor +
                         │
                    Diode cathode (stripe end)
                         │
                    Diode anode
                         │
                         └──── Transistor COLLECTOR ──── Motor -
```

**Step-by-step:**

1. **Identify transistor pins:**
   - S8050/2N2222 in TO-92 package: flat side facing you, legs down
   - Left to right: EMITTER, BASE, COLLECTOR (E-B-C)

2. **Connect transistor:**
   - EMITTER → GND
   - BASE → 2.2kΩ resistor → GPIO 12
   - COLLECTOR → Motor negative wire

3. **Connect motor:**
   - Motor + → TP4057 OUT+ (battery voltage rail, 3.7-4.2V is fine for motor)
   - Motor - → Transistor COLLECTOR

4. **Add flyback diode:**
   - Cathode (end with stripe) → Motor +
   - Anode → Motor -
   - This diode goes **across** the motor terminals

**Why:** Motors are inductive and create voltage spikes when turned off. The diode protects the transistor.

**Note:** Motor runs on battery voltage (3.7-4.2V), which is fine. Only LEDs need the regulated 5V.

---

## 🔧 Assembly Order (Recommended)

### Breadboard Prototype

1. **Power rails first:**
   - Insert ESP32 into breadboard
   - Create dedicated GND rail
   - Create battery voltage rail (3.7-4.2V from TP4057 OUT+)

2. **Install MT3608 boost converter:**
   - Place MT3608 on breadboard
   - Connect TP4057 OUT+ → MT3608 IN+
   - Connect GND rail → MT3608 IN-
   - **STOP HERE** - Adjust voltage to 5.0V (see Step 2 above)
   - Verify 5.0V on OUT+ with multimeter

3. **Test power (no components yet):**
   - Plug in LiPo battery
   - ESP32 power LED should light up
   - Multimeter should read 5.0V at MT3608 OUT+
   - Disconnect battery after test

4. **Add LED ring:**
   - Solder 330Ω resistor to LED ring DIN pad
   - Solder 1000µF capacitor across 5V/GND pads **(watch polarity!)**
   - Connect: resistor → GPIO 13
   - Connect: LED 5V → MT3608 OUT+
   - Connect: LED GND → GND rail

5. **Add button:**
   - GPIO 27 → one leg
   - GND → other leg

6. **Add buzzer:**
   - GPIO 15 → +
   - GND → -

7. **Add MPU6050:**
   - VCC → 3.3V (from ESP32)
   - GND → GND rail
   - SCL → GPIO 22
   - SDA → GPIO 21

8. **Add motor driver (last, most complex):**
   - Build transistor circuit per diagram above
   - Motor + goes to TP4057 OUT+ (battery voltage)
   - Double-check diode polarity!

---

## 🧪 Testing Procedure

### Step 1: Power Test (No Code)
- [ ] Connect battery → TP4057 → MT3608
- [ ] MT3608 indicator LED lights up
- [ ] Multimeter reads 5.0V at MT3608 OUT+
- [ ] ESP32 power LED lights up
- [ ] Disconnect battery after test

### Step 2: LED Test
- [ ] Upload firmware with `#define TEST_MODE_LEDS`
- [ ] LEDs should cycle colors **BRIGHTLY**
- [ ] Colors should be vivid (especially blue and white)

### Step 3: Button Test
- [ ] Upload firmware with `#define TEST_MODE_BUTTON`
- [ ] Press button → LEDs turn green + beep

### Step 4: Buzzer Test
- [ ] Upload firmware with `#define TEST_MODE_BUZZER`
- [ ] Should hear beep patterns

### Step 5: Motor Test
- [ ] Upload firmware with `#define TEST_MODE_MOTOR`
- [ ] Motor should pulse on/off

### Step 6: MPU Test
- [ ] Upload firmware with `#define TEST_MODE_MPU`
- [ ] Open Serial Monitor
- [ ] Shake puck → should print "SHAKE DETECTED"

### Step 7: Normal Mode
- [ ] Upload firmware with `#define NORMAL_MODE`
- [ ] Should see breathing cyan LEDs (bright and vivid!)
- [ ] Button press → flash green + vibrate + beep
- [ ] Shake → rainbow burst + vibrate (colors should POP!)

---

## ⚠️ Common Mistakes

### MT3608 Issues
- ❌ Connected LEDs before adjusting voltage → Could fry LEDs if set >5.5V!
- ❌ MT3608 gets very hot → Output current too high, lower LED brightness
- ❌ Voltage sags during animations → Add 100µF cap across MT3608 input

### LEDs Don't Light
- ❌ MT3608 not adjusted to 5V → Check with multimeter
- ❌ Capacitor backwards (will explode!) → Check polarity
- ❌ Wrong GPIO pin → Should be GPIO 13
- ❌ 330Ω resistor missing → Can damage data line

### Motor Doesn't Work
- ❌ Transistor pins backwards → Check E-B-C pinout
- ❌ Diode backwards → Stripe goes to Motor +
- ❌ No base resistor → Could damage GPIO 12
- ❌ Motor wired directly to GPIO → GPIO can't handle motor current!

### MPU6050 Not Found
- ❌ Powered by 5V instead of 3.3V → Can damage sensor!
- ❌ SDA/SCL swapped → Try swapping them
- ❌ Bad solder joints → Check continuity

### Buzzer Always On
- ❌ Wired to 5V instead of GPIO 15
- ❌ Active vs passive buzzer confusion → You need **active** (2-wire)

---

## 📊 Current Draw Estimates (WITH MT3608)

### Component Current Draw

| Component           | Voltage | Typical Current | Max Current |
|--------------------|---------|-----------------|--------------
| ESP32 (active)     | 3.7-4.2V | 80-160 mA      | 240 mA       |
| LED ring (brightness 80) | 5V | 150-200 mA @ 5V | 960 mA (all white) |
| MT3608 boost (overhead) | - | ~20 mA          | ~50 mA       |
| Motor              | 3.7-4.2V | 40-60 mA       | 100 mA       |
| MPU6050            | 3.3V | 3.5 mA          | 3.5 mA       |
| Buzzer             | 3.3V | 20-30 mA        | 30 mA        |

### Battery Current (from LiPo)

MT3608 boost efficiency: ~93%

| Condition | Output @ 5V | Input @ 3.7V | Total System |
|-----------|------------|--------------|--------------|
| Idle (breathing cyan) | 80 mA | ~110 mA | ~200 mA |
| Button flash (green) | 150 mA | ~205 mA | ~280 mA |
| Rainbow burst | 200 mA | ~270 mA | ~350 mA |
| All LEDs white max | 960 mA | ~1.3 A | ~1.4 A |

**Battery life @ 2000mAh:**
- Idle: **~8-10 hours**
- Active play: **~6-8 hours**
- Max brightness: **~1.5 hours**

TP4057 can handle 1A continuous output safely. At `LED_BRIGHTNESS = 80`, you're well within limits!

---

## 🔋 Battery Safety

✅ **DO:**
- Use the included battery protection PCB
- Charge via TP4057 USB-C port only
- Disconnect battery when not in use for weeks
- Monitor MT3608 temperature during first test (warm is OK, too hot to touch is not)

❌ **DON'T:**
- Short circuit battery terminals
- Exceed 2A output from MT3608 (it will overheat)
- Connect LEDs before adjusting MT3608 voltage
- Over-discharge below 3.0V (protection should prevent this)
- Puncture or crush LiPo cells

---

## 🛠️ Soldering Tips

1. **Use 30 AWG for signals** (button, GPIO, I2C, LED data)
2. **Use 22 AWG for power** (battery, MT3608, motor, LED 5V/GND)
3. **Twist wires before soldering** for strength
4. **Heat shrink everything** to prevent shorts
5. **Test continuity** with multimeter before powering on
6. **Label wires** with tape if building multiple pucks

---

## 📸 Pre-Power-On Checklist

Before first power-on:

- [ ] MT3608 adjusted to 5.0V (verified with multimeter)
- [ ] 1000µF capacitor has correct polarity (- to GND)
- [ ] Diode on motor has stripe toward Motor +
- [ ] MPU6050 connected to 3.3V (NOT 5V)
- [ ] All GND connections tied together
- [ ] No bare wire exposed that could short
- [ ] Battery connected to TP4057 BAT+/BAT- correctly
- [ ] 330Ω resistor in series with LED data line
- [ ] LED ring 5V connected to MT3608 OUT+ (not battery voltage)

---

## 🎨 Visual Comparison: With vs Without MT3608

### Without MT3608 (Battery Voltage 3.7V → LEDs)
- 🔴 Red: Dim
- 🟢 Green: Okay
- 🔵 Blue: **Very dim** (blues need full 5V)
- ⚪ White: Yellowish tint
- 📉 Brightness fades as battery drains

### With MT3608 (Regulated 5V → LEDs)
- 🔴 Red: **BRIGHT!**
- 🟢 Green: **BRIGHT!**
- 🔵 Blue: **BRIGHT!** (blues finally shine!)
- ⚪ White: **True white**
- 📊 Consistent brightness until battery low warning

**Your rainbow burst animation will look PROFESSIONAL! 🌈**

---

## 🚀 Ready to Build!

Follow the **Assembly Order** section, test each component individually, then run **NORMAL_MODE** for the full interactive experience.

**Need help?**
- Check Serial Monitor (115200 baud) for debug output
- See `MT3608_WIRING.md` for detailed boost converter info
- See `SCHEMATIC.txt` for visual wiring diagrams

---

## 📦 Option B: Quick Test Without MT3608

If you want to test without buying MT3608 first:

**Quick wiring:**
- TP4057 OUT+ → LED ring 5V (instead of MT3608 OUT+)
- Everything else stays the same

**Trade-offs:**
- ✅ Works immediately
- ❌ LEDs dimmer (3.7-4.2V instead of 5V)
- ❌ Blue colors weak
- ❌ Brightness varies with battery level

**Recommendation:** Get MT3608 for professional results. It's only $1.50/puck!
