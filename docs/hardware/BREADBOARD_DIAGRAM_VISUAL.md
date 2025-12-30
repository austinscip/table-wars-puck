# TABLE WARS PUCK - Visual Breadboard Diagram
## Complete Build Layout (63-Row Breadboard) - CORRECTED

---

## 📐 Understanding Your Breadboard Layout

Your breadboard is oriented **VERTICALLY** with power rails running the full length:

```
Physical Layout (breadboard oriented vertically):

Left Side                    Center                   Right Side
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Power Rails    Component Area                Component Area    Power Rails
(Vertical)     (Vertical)                    (Vertical)        (Vertical)

[-] [+] ║  A  B  C  D  E  ║  GAP  ║  F  G  H  I  J  ║ [-] [+]
BLUE RED║                 ║       ║                 ║ BLUE RED
GND 3.3V║   Left Side     ║       ║   Right Side    ║ GND  5V
        ║   Columns       ║       ║   Columns       ║

Rails run from row 3 to row 61 (rows 1-2 and 62-63 are open), with gaps every 5 rows
```

**Key Points:**
- **Power rails** are vertical columns (separate from A-J)
- **Left rails:** Blue (-) outer, Red (+) inner, then gap, then columns A-E
- **Right rails:** Columns F-J, then gap, then Blue (-) inner, Red (+) outer
- **Rails start at row 3, end at row 61** (rows 1-2 and 62-63 have no rails)
- **Rails have gaps every 5 rows** (100 holes total on each side)
- There's a **gap/channel** between rails and component area

---

## 🎨 Full Breadboard Layout (All 63 Rows)

```
TABLE WARS PUCK - BREADBOARD BUILD DIAGRAM

Left Power Rails      Left Components   Center   Right Components      Right Power Rails
[-]  [+]              A  B  C  D  E      GAP      F  G  H  I  J              [-]  [+]
BLUE RED                                                                     BLUE RED
GND  3.3V                                                                    GND  5V
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Row 1:          ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║
Row 2:          ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║
Row 3:  [-] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]
Row 4:  [-] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]
Row 5:  [-] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [+] [ ] [ ] ║ [-] [+]  ← TP4057 BAT+
Row 6:  [-] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [-] [ ] [ ] ║ [-] [+]  ← TP4057 BAT-
Row 7:  [-] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [+] [D] [ ] ║ [-] [+]  ← TP4057 OUT+
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ GAP
Row 8:          ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [-] [ ] [ ] ║            ← TP4057 OUT-
Row 9:  [-] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]
Row 10: [-] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]
Row 11: [-] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]
Row 12: [-] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]
Row 13: [-] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ GAP
Row 14:         ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                    ESP32 DEVKITC-32 (Rows 15-33)
         ESP32 board covers columns C-D-E and F-G-H, but pins only in B and I
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Row 15: [G] [P] ║ [ ] [●] [█] [█] [█] ║      ║ [█] [█] [█] [●] [ ] ║ [-] [+]  ← 3.3V & GND
Row 16: [-] [+] ║ [ ] [●] [█] [█] [█] ║      ║ [█] [█] [█] [●] [ ] ║ [-] [+]
Row 17: [-] [+] ║ [ ] [●] [█] [█] [█] ║      ║ [█] [█] [█] [●] [ ] ║ [-] [+]  ← GPIO 22 (SCL)
Row 18: [-] [+] ║ [ ] [●] [█] [█] [█] ║      ║ [█] [█] [█] [●] [ ] ║ [-] [+]
Row 19: [-] [+] ║ [ ] [●] [█] [█] [█] ║      ║ [█] [█] [█] [●] [ ] ║ [-] [+]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ GAP
Row 20:         ║ [ ] [●] [█] [█] [█] ║      ║ [█] [█] [█] [●] [ ] ║            ← GPIO 21 (SDA)
Row 21: [G] [+] ║ [ ] [●] [█] [█] [█] ║      ║ [█] [█] [█] [●] [ ] ║ [-] [+]  ← GND
Row 22: [-] [+] ║ [ ] [●] [█] [█] [█] ║      ║ [█] [█] [█] [●] [ ] ║ [-] [+]
Row 23: [-] [+] ║ [ ] [●] [█] [█] [█] ║      ║ [█] [█] [█] [●] [ ] ║ [-] [+]
Row 24: [-] [+] ║ [ ] [●] [█] [█] [█] ║      ║ [█] [█] [█] [●] [ ] ║ [-] [+]
Row 25: [-] [+] ║ [ ] [●] [█] [█] [█] ║      ║ [█] [█] [█] [●] [ ] ║ [-] [+]  ← GPIO 27 (Button)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ GAP
Row 26:         ║ [ ] [●] [█] [█] [█] ║      ║ [█] [█] [█] [●] [ ] ║
Row 27: [-] [+] ║ [ ] [●] [█] [█] [█] ║      ║ [█] [█] [█] [●] [ ] ║ [-] [+]  ← GPIO 12 (Motor)
Row 28: [G] [+] ║ [ ] [●] [█] [█] [█] ║      ║ [█] [█] [█] [●] [ ] ║ [-] [+]  ← GND
Row 29: [-] [+] ║ [ ] [●] [█] [█] [█] ║      ║ [█] [█] [█] [●] [ ] ║ [-] [+]  ← GPIO 13, 15
Row 30: [-] [+] ║ [ ] [●] [█] [█] [█] ║      ║ [█] [█] [█] [●] [ ] ║ [-] [+]
Row 31: [-] [+] ║ [ ] [●] [█] [█] [█] ║      ║ [█] [█] [█] [●] [ ] ║ [-] [+]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ GAP
Row 32:         ║ [ ] [●] [█] [█] [█] ║      ║ [█] [█] [█] [●] [ ] ║
Row 33: [-] [+] ║ [ ] [●] [█] [█] [█] ║      ║ [█] [█] [█] [●] [ ] ║ [-] [+]  ← Last ESP32 row
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                    MPU6050 ACCELEROMETER (Rows 34-37)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Row 34: [G] [P] ║ [V] [G] [S] [D] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]  ← MPU6050: VCC GND SCL SDA
Row 35: [-] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]
Row 36: [-] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]
Row 37: [-] [+] ║ [ ] [R] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]  ← 2.2kΩ Resistor (one leg)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ GAP
Row 38:         ║ [ ] [R] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║            ← 2.2kΩ Resistor (spans to row 54)
Row 39: [-] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [Z] [Z] ║ [-] [+]  ← Buzzer legs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                    MT3608 BOOST CONVERTER (Rows 40-43)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Row 40: [-] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [+] [ ] [ ] ║ [-] [P]  ← MT3608 IN+
Row 41: [G] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [-] [ ] [ ] ║ [-] [+]  ← MT3608 IN-
Row 42: [-] [P] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [+] [C] [ ] ║ [-] [P]  ← MT3608 OUT+ (5V!)
Row 43: [G] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [-] [ ] [C] ║ [-] [+]  ← MT3608 OUT-
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ GAP
Row 44:         ║ [ ] [R] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║            ← 2.2kΩ Resistor (spanning)
Row 45: [-] [+] ║ [ ] [R] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]  ← 2.2kΩ Resistor (spanning)
Row 46: [-] [+] ║ [ ] [R] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]  ← 2.2kΩ Resistor (spanning)
Row 47: [-] [+] ║ [ ] [R] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]  ← 2.2kΩ Resistor (spanning)
Row 48: [-] [+] ║ [ ] [R] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]  ← 2.2kΩ Resistor (spanning)
Row 49: [-] [+] ║ [ ] [R] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]  ← 2.2kΩ Resistor (spanning)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ GAP
Row 50:         ║ [ ] [B] [●] [●] [ ] ║      ║ [ ] [●] [●] [ ] [ ] ║            ← Button legs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                    BUTTON (Rows 50-52)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Row 51: [-] [+] ║ [ ] [R] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]  ← 2.2kΩ Resistor (spanning)
Row 52: [G] [+] ║ [ ] [B] [●] [●] [ ] ║      ║ [ ] [●] [●] [ ] [ ] ║ [-] [+]  ← Button legs
Row 53: [-] [+] ║ [ ] [R] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]  ← 2.2kΩ Resistor (spanning)
Row 54: [-] [+] ║ [ ] [R] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]  ← 2.2kΩ Resistor (other leg)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                TRANSISTOR & MOTOR (Row 55)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Row 55: [G] [+] ║ [E] [B] [C] [M] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]  ← Transistor E-B-C, Motor-
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ GAP
Row 56:         ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                    TRANSISTOR CIRCUIT (Row 55)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Row 57: [-] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]
Row 58: [-] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]
Row 59: [-] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]
Row 60: [-] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]
Row 61: [-] [+] ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║ [-] [+]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ GAP
Row 62:         ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║
Row 63:         ║ [ ] [ ] [ ] [ ] [ ] ║      ║ [ ] [ ] [ ] [ ] [ ] ║

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POWER RAILS: Start at row 3, end at row 61 (rows 1-2 and 62-63 have no rails)
Gaps every 5 rows (at rows 8, 14, 20, 26, 32, 38, 44, 50, 56, 62)
100 holes total on each side
Left: [-] BLUE GND    [+] RED 3.3V
Right: [-] BLUE GND    [+] RED 5V
Bridge both blue rails together at top
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🔌 Legend

| Symbol | Meaning |
|--------|---------|
| **[-]** | Blue power rail (GND) - vertical column |
| **[+]** | Red power rail (PWR) - vertical column |
| **║** | Gap/channel between rails and components |
| **[●]** | ESP32 pin (actual metal pin in hole) |
| **[█]** | ESP32 board covers this hole (no pin, blocked) |
| **[G]** | Ground connection (use jumper wire to rail) |
| **[P]** | Power connection (use jumper wire to rail) |
| **[V]** | VCC/Power pin for MPU6050 (3.3V) |
| **[S]** | SCL pin (I2C clock - GPIO 22) |
| **[D]** | SDA pin (I2C data - GPIO 21) OR Diode |
| **[R]** | Resistor leg (2.2kΩ spanning rows 37-54) |
| **[B]** | Button leg |
| **[E][B][C]** | Transistor Emitter-Base-Collector (2N2222) |
| **[M]** | Motor wire connection (Motor- to collector) |
| **[C]** | Capacitor leg (100µF for MT3608 output) |
| **[Z]** | Buzzer leg |
| **Jumper wires** | Connect between holes to complete all circuits |
| **[ ]** | Empty hole |

---

## 📍 Key Connections

### Power Rails (Vertical):
- **Left Blue Rail (-):** Connect to ESP32 GND at rows 15, 21, 28, 34
- **Left Red Rail (+):** Connect to ESP32 3.3V at row 15
- **Right Blue Rail (-):** Connect to TP4057/MT3608 grounds
- **Right Red Rail (+):** Connect to MT3608 OUT+ at row 42
- **Bridge:** Connect left blue rail to right blue rail at top

### ESP32 (Rows 15-33):
- **19 pins per side** (19 rows total)
- Straddles center gap
- **Board is WIDE:** covers columns C-D-E (left) and F-G-H (right)
- **Actual pins:** Only in columns B and I
  - Left side: Pins in column B only
  - Right side: Pins in column I only
  - Columns C-D-E and F-G-H are covered by the board (no pins)
- Column A is open on left (no ESP32 coverage)
- Column J is open on right (no ESP32 coverage)

### TP4057 Charger (Rows 5-8):
- Battery connections at row 5-6, column H
- Output at rows 7-8, column H

### MT3608 Boost (Rows 40-43):
- Input from TP4057 at row 40, column H
- Output (5V) at row 42, column H
- **Adjust to 5.0V before connecting LEDs!**

### Button (Rows 50-52):
- One side connects to GPIO 27 (row 25, column B)
- Other side connects to left blue rail (GND)

### MPU6050 Accelerometer (Row 34):
- VCC (col A) → Jumper to left red rail (3.3V)
- GND (col B) → Jumper to left blue rail (GND)
- SCL (col C) → Jumper to GPIO 22 (row 17, col B)
- SDA (col D) → Jumper to GPIO 21 (row 20, col B)

### 2.2kΩ Resistor (Rows 37-54):
- One leg at row 37, column B
- Other leg at row 54, column B
- Connects GPIO 12 (row 27) to transistor base (row 55)
- Use jumper wire from row 27 col B to row 37 col B

### Buzzer (Row 39):
- Positive leg (col I) → Jumper to available GPIO pin
- Negative leg (col J) → Jumper to left blue rail (GND)

### Transistor (Row 55):
- Emitter (col A) → Jumper to left blue rail (GND)
- Base (col B) ← Connects to 2.2kΩ resistor (row 54, col B)
- Collector (col C) → Jumper to motor negative wire (col D)

### Motor:
- Motor negative (row 55, col D) → Connects to transistor collector
- Motor positive → Jumper to right red rail (5V from MT3608)

---

## 🎯 This Is Now Correct!

- **63 rows total** in the component area
- **Rails run from row 3 to row 61** (rows 1-2 and 62-63 have no power rails)
- **Rails have gaps every 5 rows** (at rows 8, 14, 20, 26, 32, 38, 44, 50, 56, 62)
- **100 holes total on each side** for power rails
- **ESP32 pins only in columns B and I** (columns C-D-E and F-G-H are covered by the board)
- **Columns A and J are open** (not labeled, just empty holes)
- **Rails are vertical columns** (not horizontal top/bottom)
- **Clear separation** (║) between rails and component area
- **Both sides symmetrical:** Rail(-) Rail(+) on left AND right
- **ALL components now shown:**
  - TP4057 battery charger (rows 5-8)
  - ESP32 DevKit (rows 15-33)
  - MPU6050 accelerometer (row 34)
  - 2.2kΩ resistor (rows 37-54)
  - Buzzer (row 39)
  - MT3608 boost converter (rows 40-43)
  - Button (rows 50-52)
  - Transistor & motor connection (row 55)

Ready to build! 🚀
