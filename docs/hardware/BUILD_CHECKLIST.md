# Table Wars Puck - Build Checklist

**Print this page and check off each step as you go!**

---

## ☑️ Pre-Build

- [ ] Read `README.md` fully
- [ ] Read `WIRING_GUIDE.md` fully
- [ ] Review `SCHEMATIC.txt` for visual reference
- [ ] Gather all components (see parts list below)
- [ ] Prepare workspace with:
  - [ ] Soldering iron + solder
  - [ ] Wire strippers
  - [ ] Multimeter
  - [ ] Heat shrink tubing
  - [ ] Helping hands / PCB holder

---

## ☑️ Software Setup

- [ ] Install PlatformIO (VS Code extension or CLI)
- [ ] Open `table-wars-puck/` folder in VS Code
- [ ] Verify `platformio.ini` is detected
- [ ] Run initial build: `pio run` (downloads libraries)
- [ ] Connect ESP32 via USB-C
- [ ] Verify ESP32 detected in device manager
- [ ] Install CP210x driver if needed

---

## ☑️ Power System Assembly

- [ ] Connect LiPo battery PH2.0 connector to TP4057 BAT+/BAT-
  - [ ] Red wire → BAT+
  - [ ] Black wire → BAT-
- [ ] Connect TP4057 OUT+ to ESP32 5V pin AND MT3608 IN+
- [ ] Connect TP4057 OUT- to breadboard GND rail
- [ ] Connect all ESP32 GND pins to GND rail
- [ ] Connect MT3608 IN- to GND rail
- [ ] **TEST:** Plug in battery, ESP32 power LED should light
- [ ] **TEST:** Plug USB-C into TP4057, charging LED should light
- [ ] Disconnect battery before proceeding

---

## ☑️ MT3608 Boost Converter Setup ⭐ CRITICAL!

**Do this BEFORE connecting LED ring!**

- [ ] MT3608 module placed on breadboard
- [ ] TP4057 OUT+ connected to MT3608 IN+
- [ ] GND rail connected to MT3608 IN-
- [ ] **LEAVE MT3608 OUT+ and OUT- disconnected** (no load yet)
- [ ] Connect battery or USB power
- [ ] Using multimeter:
  - [ ] Red probe → MT3608 OUT+
  - [ ] Black probe → MT3608 OUT- (or GND)
  - [ ] Note current voltage (probably 5-12V from factory)
- [ ] Using small Phillips screwdriver, adjust blue potentiometer:
  - [ ] Turn **clockwise** to increase voltage
  - [ ] Turn **counter-clockwise** to decrease voltage
  - [ ] Adjust until multimeter reads **5.0V** (4.9-5.1V acceptable)
- [ ] Watch voltage for 30 seconds - should stay stable
- [ ] Disconnect power
- [ ] ✅ **MT3608 is now ready for LED connection**

---

## ☑️ LED Ring Assembly

- [ ] Identify LED ring pads: DIN, 5V, GND
- [ ] Solder 330Ω resistor to DIN pad (leave ~1cm lead)
- [ ] Solder 1000µF capacitor across 5V and GND pads
  - [ ] **CRITICAL:** Check polarity! (- leg to GND)
  - [ ] Capacitor stripe/minus marking toward GND
- [ ] Connect resistor lead to ESP32 GPIO 13
- [ ] Connect LED 5V to **MT3608 OUT+** (regulated 5V)
- [ ] Connect LED GND to GND rail
- [ ] **TEST:** Upload `TEST_MODE_LEDS`, LEDs should cycle colors **BRIGHTLY**
- [ ] **TEST:** Colors should be vivid (especially blue and white!)

---

## ☑️ Button Assembly

- [ ] Identify button legs (any 2 opposite legs)
- [ ] Connect one leg to ESP32 GPIO 27
- [ ] Connect other leg to GND rail
- [ ] **TEST:** Upload `TEST_MODE_BUTTON`, press button → green LEDs

---

## ☑️ Buzzer Assembly

- [ ] Identify buzzer polarity (+ is usually marked or red wire)
- [ ] Connect buzzer + to ESP32 GPIO 15
- [ ] Connect buzzer - to GND rail
- [ ] **TEST:** Upload `TEST_MODE_BUZZER`, should hear beeps

---

## ☑️ MPU6050 Assembly

- [ ] Connect MPU6050 VCC to ESP32 3.3V pin (**NOT 5V!**)
- [ ] Connect MPU6050 GND to GND rail
- [ ] Connect MPU6050 SCL to ESP32 GPIO 22
- [ ] Connect MPU6050 SDA to ESP32 GPIO 21
- [ ] **TEST:** Upload `TEST_MODE_MPU`, shake puck → "SHAKE DETECTED"

---

## ☑️ Vibration Motor + Transistor Assembly

**Most complex part - go slow!**

### Identify Transistor Pins (S8050 or 2N2222)
- [ ] Hold transistor with flat side facing you, legs down
- [ ] Left to right: EMITTER, BASE, COLLECTOR (E-B-C)

### Assemble Circuit
- [ ] Connect transistor EMITTER to GND rail
- [ ] Solder 2.2kΩ resistor between GPIO 12 and transistor BASE
- [ ] Connect motor + (red) to **battery voltage rail** (TP4057 OUT+, 3.7-4.2V)
- [ ] Connect motor - (black) to transistor COLLECTOR
- [ ] Connect 1N4148 diode across motor terminals:
  - [ ] Cathode (stripe end) → Motor +
  - [ ] Anode (plain end) → Motor -

### Double-Check Before Testing
- [ ] Transistor EMITTER to GND? (yes/no)
- [ ] Transistor BASE via 2.2kΩ to GPIO 12? (yes/no)
- [ ] Transistor COLLECTOR to Motor -? (yes/no)
- [ ] Motor + to **battery voltage** (TP4057 OUT+, NOT MT3608 OUT+)? (yes/no)
- [ ] Diode stripe toward Motor +? (yes/no)

- [ ] **TEST:** Upload `TEST_MODE_MOTOR`, motor should pulse on/off

---

## ☑️ Final Integration Test

- [ ] All components connected
- [ ] All GNDs tied together
- [ ] No bare wires touching (risk of shorts)
- [ ] Upload `NORMAL_MODE` firmware
- [ ] Open Serial Monitor (115200 baud)
- [ ] Verify boot sequence:
  - [ ] Spinner animation (cyan)
  - [ ] Flash white
  - [ ] Beep
- [ ] Test idle: LEDs breathing cyan
- [ ] Test button: Flash green + vibrate + beep
- [ ] Test shake: Rainbow burst + vibrate + double beep

---

## ☑️ Battery Life Test

- [ ] Disconnect USB from ESP32
- [ ] Connect fully charged LiPo battery
- [ ] Puck should boot normally
- [ ] Monitor battery voltage over 1 hour
- [ ] Expected draw: ~250mA typical
- [ ] Expected runtime: 6-10 hours (depends on use)

---

## ☑️ Cleanup & Finishing

- [ ] Add heat shrink to all solder joints
- [ ] Secure loose wires with zip ties
- [ ] Label battery with voltage/capacity
- [ ] Test charge cycle (plug USB-C into TP4057)
- [ ] Create enclosure or protective housing (future step)

---

## ⚠️ Safety Final Checks

- [ ] **MT3608 adjusted to 5.0V** (verified with multimeter)?
- [ ] **LED ring 5V connected to MT3608 OUT+** (not battery voltage)?
- [ ] 1000µF capacitor polarity correct? (- to GND)
- [ ] MPU6050 on 3.3V, not 5V?
- [ ] Diode on motor with stripe toward +?
- [ ] Motor + connected to **battery voltage** (TP4057 OUT+)?
- [ ] Motor NOT connected directly to GPIO?
- [ ] No short circuits between power rails?
- [ ] Battery protection circuit intact?
- [ ] MT3608 not overheating during operation?

---

## 🎉 Success Criteria

- [X] All test modes pass
- [X] Normal mode runs smoothly
- [X] Button triggers expected behavior
- [X] Shake detection works
- [X] Battery powers device for >4 hours
- [X] No smoke, burning smell, or hot components
- [X] Serial monitor shows clean boot with no errors

---

## 📝 Notes / Issues

(Use this space to write down any problems or modifications)

```
_____________________________________________________________________________

_____________________________________________________________________________

_____________________________________________________________________________

_____________________________________________________________________________

_____________________________________________________________________________
```

---

**If all checkboxes are marked, congratulations! Your Table Wars puck is complete! 🍻**

Next: Build 5 more pucks and start working on game logic!
