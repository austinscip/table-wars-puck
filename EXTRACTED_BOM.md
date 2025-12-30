# TABLE WARS - Extracted Bill of Materials (BOM)

**Source:** Extracted from Hardware.rar project logs
**Date:** December 15, 2025

---

## Complete Component List

| Ref | Component | Part Number | Value | Package | Description |
|-----|-----------|-------------|-------|---------|-------------|
| **U2** | **ESP32 Module** | ESP32-DEVKITC | - | Module | Main microcontroller (WiFi + BLE) |
| **U4** | **Motion Sensor** | MPU-6050 | - | QFN-24 | 6-axis gyroscope + accelerometer ✅ |
| **U1** | **Boost Converter** | MT3608 | - | SOT23-6 | Step-up DC-DC converter |
| **J1** | **Battery Charger** | TP4057 | - | SOT23-6 | LiPo battery charging IC |
| **U3** | **Logic Buffer** | 74AHCT1G125 | - | SOT-353 | CMOS buffer/driver |
| **Q1** | **P-MOSFET** | AO3407A | - | SOT-23 | Power switching transistor |
| **Q2** | **NPN Transistor** | Generic | - | TO-92 | General purpose NPN |
| **D1** | **Diode** | 10TQ | - | TO-220AC | Power diode |
| **D2** | **RGB LED** | WS2812B2020 | - | 2020 SMD | Addressable LED (1 shown, likely more) |
| **SW1** | **Tactile Switch** | SKRAAKE010 | - | SMD | Physical button ✅ |
| **LS1** | **Buzzer** | PKMCS | 4kHz | SMD 9x9mm | Piezo buzzer for sound |
| **C1** | Capacitor | Generic | 1µF | Radial | Filter capacitor |
| **C2** | Capacitor | Generic | 10µF | Radial | Filter capacitor |
| **C4** | Capacitor | Generic | 100µF | Radial | Power supply cap |
| **R1** | Resistor | Generic | 4.7kΩ | Axial | - |
| **R2** | Resistor | Generic | 2.4kΩ | Axial | - |
| **R3** | Resistor | Generic | 100kΩ | Axial | - |
| **R4** | Resistor | Generic | 20kΩ | Axial | - |
| **R10** | Resistor | Generic | 4.7kΩ | Axial | - |
| **R11** | Resistor | Generic | 4.7kΩ | Axial | - |
| **R12** | Resistor | Generic | 10kΩ | Axial | - |
| **R13** | Resistor | Generic | 100Ω | Axial | - |
| **Rled** | LED Resistor | Generic | TBD | LED-0 | Current limiting resistor |
| **P1** | Pin Header | Generic | 1x8 | Through-hole | Programming/debug header |
| **IST-PHL** | Pin Header | Generic | 1x2 | Through-hole | ISP/programming header |
| **USB-C** | USB Connector | Generic | - | SMD | Charging port |

---

## ✅ CONFIRMED FEATURES

### **Good News:**
1. ✅ **MPU6050 is included!** (U4) - Your firmware's shake detection will work
2. ✅ **Physical button is included!** (SW1) - Tactile switch for user input
3. ✅ **Buzzer is included!** (LS1) - Sound effects ready
4. ✅ **Complete power management** - TP4057 charger + MT3608 boost converter
5. ✅ **WS2812B LEDs** - At least one shown (likely for LED ring)

### **Questions Remaining:**
- ❓ **LED count:** How many WS2812B LEDs total? (Firmware expects 16)
- ❓ **LED ring:** Separate PCB or on-board?
- ❓ **Vibration motor:** Connector visible? (Q2 might drive it)
- ❓ **Battery connector:** Type/specification?

---

## Component Sources & Pricing

### **Main ICs:**
- **ESP32-DEVKITC:** $6-8 (AliExpress/Amazon)
- **MPU-6050:** $2-3 (GY-521 module or bare chip)
- **TP4057:** $0.50 (common battery charger)
- **MT3608:** $0.50 (boost converter module)
- **WS2812B2020:** $0.20 each x 16 = $3.20

### **Passives (bulk):**
- Resistors (13x): ~$0.50 total
- Capacitors (3x): ~$1.00 total
- Transistors/diodes: ~$1.00

### **Other:**
- USB-C connector: $0.50
- Button (SKRAAKE010): $0.30
- Buzzer: $0.50
- Headers: $0.50

**Estimated Component Cost:** ~$18-25 per puck (buying in qty 10-50)

---

## Manufacturing Recommendations

### **PCB Fabrication:**
- **Vendor:** JLCPCB or PCBWay
- **Quantity:** Start with 5-10 prototypes
- **Color:** Black PCB would look sick for a puck
- **Finish:** ENIG (better for USB-C pads)

### **Assembly:**
- **SMD components:** PCB house assembly recommended (tiny parts)
- **Through-hole:** Hand solder (easy: ESP32, headers, caps)
- **Hybrid approach:** SMD assembled + you add ESP32/connectors

---

## What You Still Need from Freelancer

1. **BOM as Excel/CSV** with:
   - Exact part numbers (especially for U3, D1, Q2)
   - Manufacturer names
   - Digikey/Mouser/LCSC part numbers
   - Quantities

2. **Gerber files** - Full manufacturing set

3. **Assembly drawings** - Component placement diagrams

4. **Clarifications:**
   - Total LED count and configuration
   - Battery connector specification
   - Motor connection details

---

## Next Steps

1. **Request proper BOM export from freelancer**
2. **Get Gerber files**
3. **Upload to JLCPCB for quote**
4. **Order prototype run** (5-10 boards)
5. **Test first puck with your firmware**

---

**This PCB design is LEGIT!** All the hardware your firmware needs is accounted for:
- ✅ ESP32 for WiFi/BLE
- ✅ MPU6050 for shake detection
- ✅ Button for user input
- ✅ Buzzer for sound
- ✅ LEDs for animations
- ✅ Complete power system

Just need those manufacturing files!
