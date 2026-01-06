# TABLE WARS PUCK - Detailed Breadboard Build Guide
## For 60-Row Breadboard (830 tie points)

**Your breadboard has 60 rows with columns A-J on each side of the center gap.**

```
Power Rails Layout - CORRECT ORDER:

From LEFT to RIGHT across your breadboard:
┌────┬────┬─────────────────┬─────┬─────────────────┬────┬────┐
│ -  │ +  │  A B C D E      │ GAP │  F G H I J      │ -  │ +  │
│BLUE│RED │  Component      │     │  Component      │BLUE│RED │
│GND │3.3V│  Area (Left)    │     │  Area (Right)   │GND │5V  │
└────┴────┴─────────────────┴─────┴─────────────────┴────┴────┘

BOTH SIDES ARE SYMMETRICAL!
- Pattern: (-) (+) Columns on BOTH left and right
- Blue rail (-) is BETWEEN red rail and component columns
- Red rail (+) is on the OUTER edge
- Left Red Rail = 3.3V, Right Red Rail = 5V
- Both Blue Rails = GND (bridge them together)
```

---

## 📍 Component Placement Map

### Legend:
- **Columns:** A B C D E | GAP | F G H I J
- **Rows:** 1-60 (you have 60 rows)
- **Power Rails:** Top and bottom rails on each side

---

## ⚠️ PREP STEP: Solder Wires to LED Ring (10 minutes)

**IMPORTANT: WS2812B LED rings have solder PADS (holes), not pre-attached wires!**

### Before breadboard assembly, prepare your LED ring:

**What you need:**
- WS2812B 16-LED ring
- 3× pieces of 22 AWG solid core wire (6" each)
- Soldering iron & solder

**Steps:**
1. **Cut and strip wires:**
   - RED wire (6") for 5V
   - BLACK wire (6") for GND
   - GREEN/WHITE wire (6") for DIN
   - Strip ¼" from one end of each

2. **Solder wires to LED ring pads:**
   - Identify pads: 5V, GND, DIN (ignore DOUT)
   - Heat pad with iron, apply solder to tin it
   - Insert stripped wire through pad from back
   - Heat pad from front, wire sinks into solder
   - Hold still 2 seconds while cooling

3. **Test connections:**
   - Tug each wire gently - should be secure
   - Use multimeter continuity mode to verify

**✅ LED ring now ready for breadboard!**

**For detailed soldering instructions, see LED_RING_PREP_GUIDE.md**

---

## STEP 1: Insert ESP32 into Breadboard

### ESP32 Placement:
```
Position: Rows 15-33 (19 rows total, straddles the gap)

IMPORTANT: ESP32 DevKitC-32 is WIDE!
- Uses 4 columns on EACH side
- Left side: Columns B, C, D, E (leaves only A open)
- Right side: Columns F, G, H, I (leaves only J open)

Left Side Pins (Columns B-C-D-E):      Right Side Pins (Columns F-G-H-I):
Row 15: 3.3V                           Row 15: GND
Row 16: EN                             Row 16: GPIO 23
Row 17: GPIO 36                        Row 17: GPIO 22 ← MPU6050 SCL
Row 18: GPIO 39                        Row 18: GPIO 1 (TX)
Row 19: GPIO 34                        Row 19: GPIO 3 (RX)
Row 20: GPIO 35                        Row 20: GPIO 21 ← MPU6050 SDA
Row 21: GPIO 32                        Row 21: GND
Row 22: GPIO 33                        Row 22: GPIO 19
Row 23: GPIO 25                        Row 23: GPIO 18
Row 24: GPIO 26                        Row 24: GPIO 5
Row 25: GPIO 27 ← Button               Row 25: GPIO 17
Row 26: GPIO 14                        Row 26: GPIO 16
Row 27: GPIO 12 ← Motor Control        Row 27: GPIO 4
Row 28: GND                            Row 28: GPIO 2
Row 29: GPIO 13 ← LED Ring Data        Row 29: GPIO 15 ← Buzzer
Row 30: GPIO 9                         Row 30: GND
Row 31: GPIO 10                        Row 31: 5V (not used, use 3.3V)
Row 32: GPIO 11                        Row 32: CMD
Row 33: VIN (not used)                 Row 33: CLK
```

**ESP32 has 19 pins per side, ending at Row 33**

### Instructions:
1. Hold ESP32 with USB-C port facing you
2. Align leftmost pins with Row 15, Columns B-C-D-E (all 4 columns)
3. Align rightmost pins with Row 15, Columns F-G-H-I (all 4 columns)
4. Press firmly but gently - all pins should insert evenly
5. ESP32 should straddle the center gap
6. Only Column A (left) and Column J (right) will be visible/open

---

## STEP 2: Power Rails Setup

### Connection 1: 3.3V Power Rail
**FROM:** ESP32 3.3V pin (Row 15, Column D)
**TO:** Left Red Power Rail (OUTERMOST left edge, marked +)

**How to connect:**
- Jumper wire from Row 15, Column A → Left Red Rail (outer edge, marked +)

---

### Connection 2: Ground Rail (Left Side)
**FROM:** ESP32 GND pin (Row 15, Column F)
**TO:** Left Blue Power Rail (between red rail and columns, marked -)

**How to connect:**
- Jumper wire from Row 15, Column A → Left Blue Rail (inner, marked -)

---

### Connection 3: Additional GND
**FROM:** ESP32 GND pin (Row 21, Column F)
**TO:** Left Blue Power Rail (marked -)

**How to connect:**
- Jumper wire from Row 21, Column A → Left Blue Rail (marked -)

---

## STEP 3: Connect TP4057 Charger + MT3608 Boost Converter

### TP4057 Placement:
```
Position: Rows 5-8, Right side (Columns H-J)

Row 5 (H): BAT+  ← Battery Red Wire
Row 6 (I): BAT-  ← Battery Black Wire
Row 7 (H): OUT+  → MT3608 IN+ AND ESP32 5V
Row 8 (I): OUT-  → GND Rail
```

---

### MT3608 Placement:
```
Position: Rows 40-45, Right side (Columns H-J)

Row 40 (H): IN+   ← TP4057 OUT+
Row 41 (I): IN-   → GND Rail
Row 42 (H): OUT+  → LED Ring 5V (AFTER ADJUSTMENT!)
Row 43 (I): OUT-  → GND Rail
```

---

### Power Connections:

#### Connection 4: TP4057 BAT+ to Battery
**Component:** Red wire from LiPo battery
**Position:** Row 5, Column H

#### Connection 5: TP4057 BAT- to Battery
**Component:** Black wire from LiPo battery
**Position:** Row 6, Column I

#### Connection 6: TP4057 OUT+ to MT3608 IN+
**FROM:** Row 7, Column H
**TO:** Row 40, Column H
**Wire:** Red jumper wire

#### Connection 7: TP4057 OUT- to GND Rail
**FROM:** Row 8, Column I
**TO:** Right Blue Rail (between columns and outer red rail, marked -)
**Wire:** Black jumper wire

#### Connection 8: MT3608 IN- to GND Rail
**FROM:** Row 41, Column I
**TO:** Right Blue Rail (marked -)
**Wire:** Black jumper wire

#### Connection 9: MT3608 OUT- to GND Rail
**FROM:** Row 43, Column I
**TO:** Right Blue Rail (marked -)
**Wire:** Black jumper wire

#### Connection 10: Bridge Left and Right GND Rails
**FROM:** Left Blue Rail (between red rail and columns, marked -)
**TO:** Right Blue Rail (between columns and red rail, marked -)
**Wire:** Black jumper wire (bridge across top of breadboard)

**Note:** Both blue rails should be connected together so all GND points are common

---

### ⚠️ CRITICAL: Adjust MT3608 to 5.0V BEFORE proceeding!

**Procedure:**
1. Connect battery to TP4057
2. Use multimeter: Red probe to Row 42 Column H, Black probe to GND
3. Turn MT3608 blue potentiometer with small screwdriver
4. Adjust until multimeter reads **5.0V** (±0.1V acceptable)
5. Disconnect battery
6. ✅ Now safe to connect LEDs

---

## STEP 4: Connect WS2812B LED Ring

### LED Ring has 3 wires (usually):
- **Red/5V:** Power (needs 5V)
- **Black/GND:** Ground
- **Green/White/DIN:** Data Input

---

### Component Placement:

#### Connection 11: 330Ω Resistor for LED Data
**Position:** Row 29, Columns B-C (in series with GPIO 13)

**FROM:** ESP32 GPIO 13 (Row 29, Column E)
**TO:** Row 29, Column B (one leg of resistor)
**Other resistor leg:** Row 29, Column C

---

#### Connection 12: LED Ring DIN (Data)
**FROM:** LED Ring DIN wire (male-female jumper)
**TO:** Row 29, Column C (connects to resistor)

---

#### Connection 13: LED Ring 5V
**FROM:** LED Ring 5V/+ wire
**TO:** MT3608 OUT+ (Row 42, Column H)

**Use:** Red male-female jumper wire

---

#### Connection 14: LED Ring GND
**FROM:** LED Ring GND/- wire
**TO:** Right Blue Rail (-)

**Use:** Black male-female jumper wire

---

#### Connection 15: 1000µF Capacitor
**Position:** Across MT3608 OUT+ and OUT-

**Positive leg (+):** Row 42, Column I
**Negative leg (-):** Row 43, Column J (marked with stripe)

**⚠️ POLARITY MATTERS!** Stripe/negative goes to GND

---

## STEP 5: Connect MPU6050 Motion Sensor

### MPU6050 Placement:
The MPU6050 typically has pins in this order:
- VCC
- GND
- SCL
- SDA
- (XDA, XCL, AD0, INT - leave unconnected)

---

### Connections:

#### Connection 16: MPU6050 VCC to 3.3V
**FROM:** MPU6050 VCC pin
**TO:** Left Red Rail (+) = 3.3V

**Use:** Red male-female jumper wire
**⚠️ Use 3.3V NOT 5V!**

---

#### Connection 17: MPU6050 GND
**FROM:** MPU6050 GND pin
**TO:** Left Blue Rail (-)

**Use:** Black male-female jumper wire

---

#### Connection 18: MPU6050 SCL to GPIO 22
**FROM:** MPU6050 SCL pin
**TO:** Row 17, Column H (GPIO 22)

**Use:** Yellow/Orange male-female jumper wire

---

#### Connection 19: MPU6050 SDA to GPIO 21
**FROM:** MPU6050 SDA pin
**TO:** Row 20, Column H (GPIO 21)

**Use:** Green male-female jumper wire

---

## STEP 6: Connect Button

### Button Placement:
```
Position: Rows 50-52, straddles gap

Left legs:  Row 50 Column D, Row 52 Column D
Right legs: Row 50 Column G, Row 52 Column G
```

---

### Connections:

#### Connection 20: Button to GPIO 27
**FROM:** ESP32 GPIO 27 (Row 25, Column D)
**TO:** Row 50, Column D (button leg)

**Use:** Jumper wire from Row 25, Column A → Row 50, Column B

---

#### Connection 21: Button to GND
**FROM:** Row 52, Column D (opposite button leg)
**TO:** Left Blue Rail (-)

**Use:** Jumper wire from Row 52, Column A → Left Blue Rail (-)

---

## STEP 7: Connect Buzzer

### Buzzer Connections:

#### Connection 22: Buzzer + (Red) to GPIO 15
**FROM:** Buzzer + wire (red/long leg)
**TO:** Row 29, Column H (GPIO 15)

**Use:** Red male-female jumper wire

---

#### Connection 23: Buzzer - (Black) to GND
**FROM:** Buzzer - wire (black/short leg)
**TO:** Left Blue Rail (-)

**Use:** Black male-female jumper wire

---

## STEP 8: Connect Motor with Transistor Circuit

### This is the most complex part!

### Component Placement:

#### Transistor (S8050 or 2N2222):
```
Position: Row 55, Columns A-B-C
(TO-92 package, flat side facing left)

Pin arrangement (flat side left, pins down):
Row 55, Column A: EMITTER   → GND
Row 55, Column B: BASE      ← 2.2kΩ resistor ← GPIO 12
Row 55, Column C: COLLECTOR → Motor -
```

---

### Connections:

#### Connection 24: 2.2kΩ Base Resistor
**Position:** Rows 27-55

**One leg:** Row 27, Column B (same row as GPIO 12, Column G)
**Other leg:** Row 55, Column B (transistor BASE)

**Jumper:** Row 27, Column G → Row 27, Column A (bridges to left side)

---

#### Connection 25: Transistor EMITTER to GND
**FROM:** Row 55, Column A (transistor EMITTER)
**TO:** Left Blue Rail (-)

**Use:** Black jumper wire

---

#### Connection 26: Motor + to Battery Voltage
**FROM:** Motor + wire (red)
**TO:** Row 7, Column H (TP4057 OUT+, battery voltage 3.7-4.2V)

**Use:** Red male-female jumper wire
**Note:** Motor runs on battery voltage, not regulated 5V

---

#### Connection 27: Motor - to Transistor COLLECTOR
**FROM:** Motor - wire (black)
**TO:** Row 55, Column C (transistor COLLECTOR)

**Use:** Black male-female jumper wire

---

#### Connection 28: 1N4148 Flyback Diode
**Position:** Across motor terminals

**Cathode (stripe end):** Row 7, Column I (near Motor +, battery voltage)
**Anode:** Row 55, Column D (near Motor -, COLLECTOR)

**Purpose:** Protects transistor from voltage spikes when motor turns off

---

## 🎨 Complete Breadboard Layout Diagram

```
TOP VIEW (60 rows)
═══════════════════════════════════════════════════════════

[+] ─────────────────────────────────────────── [+]
RED (3.3V from ESP32)                   RED (5V from MT3608)

[-] ─────────────────────────────────────────── [-]
BLUE (GND)              BRIDGE              BLUE (GND)

Row  A  B  C  D  E | GAP |  F  G  H  I  J
═══════════════════════════════════════════════════════════

 1-4: [Empty]

 5-8:                              TP4057 CHARGER
                                   (Columns H-J)
                                   Row 5: BAT+ ← Battery
                                   Row 6: BAT- ← Battery
                                   Row 7: OUT+ → MT3608 & Motor
                                   Row 8: OUT- → GND

 9-14: [Empty]

15-34:           ESP32 DEVKITC-32
                 (Straddles Gap D-E | F-G)

     A  B  C  D  E | GAP |  F  G  H  I  J
Row 15: ─────── 3.3V      GND ──────────── (Power)
Row 17: ─────── GP36      GP22 ← MPU SCL ─
Row 20: ─────── GP35      GP21 ← MPU SDA ─
Row 25: ─────── GP27 ← Button
Row 27: ── Res ─ GP12 ← Motor Control
Row 29: ── Res ─ GP13 ← LED Data  GP15 → Buzzer

35-39: [Empty]

40-45:                            MT3608 BOOST
                                   (Columns H-J)
                                   Row 40: IN+  ← TP4057 OUT+
                                   Row 41: IN-  → GND
                                   Row 42: OUT+ → LED 5V & Cap+
                                   Row 43: OUT- → GND & Cap-

46-49: [Empty]

50-52:           BUTTON
     ─── Leg ─ Leg | GAP | Leg ─ Leg ───
     Row 50: ← GPIO 27        [Empty]
     Row 52: → GND            [Empty]

53-54: [Empty]

55-57:  TRANSISTOR CIRCUIT
     Row 55: E  B  C  D
             ↓  ↓  ↓  ↓
            GND Res Motor- Diode
                 ↑      ↑
              GPIO12  ←┘

58-60: [Empty]

OFF-BOARD CONNECTIONS:
├─ MPU6050 → 3.3V, GND, Row 17 (SCL), Row 20 (SDA)
├─ LED Ring → Row 42 (5V), GND, Row 29 (DIN via resistor)
├─ Buzzer → Row 29 (GPIO 15), GND
├─ Motor → Row 7 (Motor+), Row 55 (Motor-)
└─ Battery → TP4057 BAT+/BAT-

LEGEND:
═══════════════════════════════════════════════════════════
GP = GPIO pin
Res = Resistor
Cap = Capacitor
E-B-C = Emitter-Base-Collector (transistor)
```

---

## 📋 Connection Summary Table

| # | Component | From | To | Breadboard Position | Wire Color |
|---|-----------|------|-----|---------------------|------------|
| 1 | 3.3V Rail | ESP32 3.3V | Left Red Rail | Row 15 Col A → Rail | Red |
| 2 | GND Rail | ESP32 GND | Left Blue Rail | Row 15 Col J → Rail | Black |
| 3 | GND Rail | ESP32 GND | Left Blue Rail | Row 21 Col J → Rail | Black |
| 4 | Battery+ | LiPo Red | TP4057 BAT+ | Row 5 Col H | Red |
| 5 | Battery- | LiPo Black | TP4057 BAT- | Row 6 Col I | Black |
| 6 | Power Link | TP4057 OUT+ | MT3608 IN+ | Row 7 Col H → Row 40 Col H | Red |
| 7 | GND Link | TP4057 OUT- | Right Blue Rail | Row 8 Col I → Rail | Black |
| 8 | GND Link | MT3608 IN- | Right Blue Rail | Row 41 Col I → Rail | Black |
| 9 | GND Link | MT3608 OUT- | Right Blue Rail | Row 43 Col I → Rail | Black |
| 10 | GND Bridge | Left Blue Rail | Right Blue Rail | Rail to Rail | Black |
| 11 | LED Resistor | GPIO 13 | 330Ω Resistor | Row 29 Col E → Row 29 Col B-C | - |
| 12 | LED Data | Resistor | LED Ring DIN | Row 29 Col C → LED DIN | Green/White |
| 13 | LED Power | MT3608 OUT+ | LED Ring 5V | Row 42 Col H → LED 5V | Red |
| 14 | LED Ground | Right Blue Rail | LED Ring GND | Rail → LED GND | Black |
| 15 | Capacitor | MT3608 OUT+ | MT3608 OUT- | Row 42 Col I (+) / Row 43 Col J (-) | - |
| 16 | MPU Power | 3.3V Rail | MPU6050 VCC | Rail → MPU VCC | Red |
| 17 | MPU Ground | Left Blue Rail | MPU6050 GND | Rail → MPU GND | Black |
| 18 | MPU Clock | GPIO 22 | MPU6050 SCL | Row 17 Col H → MPU SCL | Yellow |
| 19 | MPU Data | GPIO 21 | MPU6050 SDA | Row 20 Col H → MPU SDA | Green |
| 20 | Button In | GPIO 27 | Button Leg 1 | Row 25 Col A → Row 50 Col B | Any |
| 21 | Button GND | Button Leg 2 | GND Rail | Row 52 Col A → Left Blue Rail | Black |
| 22 | Buzzer + | GPIO 15 | Buzzer + | Row 29 Col H → Buzzer + | Red |
| 23 | Buzzer - | GND Rail | Buzzer - | Left Blue Rail → Buzzer - | Black |
| 24 | Base Resistor | GPIO 12 | 2.2kΩ → Base | Row 27 Col A → Row 55 Col B | - |
| 25 | Emitter | Transistor E | GND Rail | Row 55 Col A → Left Blue Rail | Black |
| 26 | Motor + | Battery Voltage | Motor + | Row 7 Col H → Motor + | Red |
| 27 | Motor - | Motor - | Transistor C | Motor - → Row 55 Col C | Black |
| 28 | Diode | Motor + & Motor - | Flyback | Row 7 Col I → Row 55 Col D | - |

---

## ✅ Pre-Power-On Checklist

Before connecting battery, verify:

- [ ] ESP32 inserted correctly (Row 15-34, straddles gap)
- [ ] 3.3V rail connected (Row 15 Col D → Left Red Rail)
- [ ] All GND rails connected and bridged
- [ ] MT3608 adjusted to **5.0V** with multimeter
- [ ] 330Ω resistor between GPIO 13 and LED DIN (Row 29)
- [ ] 1000µF capacitor correct polarity (+ to Row 42, - to Row 43)
- [ ] MPU6050 connected to **3.3V** not 5V
- [ ] Button legs in Row 50 & 52
- [ ] Buzzer polarity correct (+ to GPIO 15)
- [ ] Motor diode stripe toward Motor + (Row 7)
- [ ] Transistor in correct orientation (E-B-C at Row 55)
- [ ] 2.2kΩ resistor from GPIO 12 to transistor BASE
- [ ] No wires crossing or shorting
- [ ] Battery connected to TP4057 BAT+/BAT- correctly

---

## 🧪 Testing Sequence

### Test 1: Power Test
1. Connect battery to TP4057
2. ESP32 power LED should light up
3. Check voltages with multimeter:
   - Left Red Rail: **3.3V**
   - Row 42 Col H (MT3608 OUT+): **5.0V**
   - All Blue Rails: **0V**

### Test 2: LED Test
1. Upload firmware
2. LEDs should light BRIGHT and colorful
3. Rainbow animation should show vivid blues

### Test 3: Button Test
1. Press button (Row 50-52)
2. Should see LED flash green
3. Should hear buzzer beep

### Test 4: Motion Test
1. Shake breadboard
2. Should see rainbow burst
3. Should feel motor vibrate
4. Serial monitor shows "SHAKE DETECTED"

---

## 🎯 Troubleshooting by Position

### LEDs Don't Work
- Check Row 29 Col C → LED DIN connected?
- Check Row 42 Col H → LED 5V = 5.0V with multimeter?
- Check capacitor polarity at Rows 42-43

### Button Doesn't Work
- Check Row 50 Col B connected to Row 25 Col A?
- Check Row 52 Col A connected to GND Rail?
- Button fully inserted?

### Motor Doesn't Work
- Check Row 55 transistor orientation (E-B-C left to right)
- Check Row 27 Col A → Row 55 Col B resistor connection
- Check diode stripe at Row 7 (toward Motor +)

### MPU6050 Not Found
- Check Row 17 Col H and Row 20 Col H connections
- Check MPU gets 3.3V not 5V
- Try swapping SCL/SDA connections

---

## 🔧 Next Steps

Once breadboard works:
1. ✅ You've validated the circuit!
2. ✅ You know all components work
3. ✅ Ready to build permanent soldered version
4. ✅ Can demo to bars using breadboard prototype

**This breadboard setup is functional enough for pilot testing!**

---

## 📸 Want a Visual Diagram?

I can generate a detailed visual breadboard diagram showing:
- Exact component placement with colors
- All wire routing
- Power rail connections
- Component orientations

Let me know if you'd like me to create that next!

---

**Build time:** 1-2 hours
**Difficulty:** Moderate (transistor circuit is tricky)
**Reusability:** Can test multiple pucks with same breadboard

**Happy building! 🚀**
