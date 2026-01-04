# Basic Functionality Test Procedure

**Project:** [PROJECT_NAME]
**Version:** 1.0
**Date:** [YYYY-MM-DD]
**Test Level:** Production / Prototype

## Test Equipment Required

- [ ] Power supply (adjustable X-Y V, X A)
- [ ] Multimeter
- [ ] Oscilloscope
- [ ] USB cable (if applicable)
- [ ] Computer with firmware flashing tools
- [ ] [Other test equipment]

## Test Environment

- **Temperature:** 20-25°C (room temperature)
- **Humidity:** 30-70% RH
- **Location:** [Lab bench / production floor]

## Safety Precautions

⚠️ **WARNINGS:**
- Ensure correct polarity before applying power
- Do not exceed maximum voltage rating of X V
- [Other safety warnings]

## Pre-Test Inspection

### Visual Inspection

- [ ] PCB free of manufacturing defects (shorts, opens, tombstones)
- [ ] All components properly placed and oriented
- [ ] No solder bridges or cold joints
- [ ] Solder mask intact, no scratches
- [ ] Silkscreen legible
- [ ] Connectors properly seated
- [ ] Enclosure (if assembled) fits correctly

**Pass:** ☐ Yes ☐ No ☐ N/A
**Notes:**

---

## Test Procedure

### Test 1: Power-On Test

**Objective:** Verify the board powers up without damage

**Steps:**
1. Set power supply to X.X V, current limit to X mA
2. Connect power with correct polarity:
   - Positive to: [Terminal/connector]
   - Negative to: [Terminal/connector]
3. Turn on power supply
4. Observe current draw
5. Check for smoke, burning smell, or excessive heat

**Expected Results:**
- Initial current spike: < X mA for < X ms
- Steady-state current: X-Y mA
- No smoke or burning smell
- No excessive heat (components warm to touch OK)

**Actual Results:**
- Current draw: _____ mA
- Observations:

**Pass:** ☐ Yes ☐ No
**Tested by:** _________ **Date:** _______

---

### Test 2: Voltage Regulation Test

**Objective:** Verify all power rails are within specification

**Steps:**
1. Apply nominal input voltage: X.X V
2. Measure voltage at test points:

| Rail | Test Point | Expected | Measured | Pass/Fail |
|------|-----------|----------|----------|-----------|
| 3.3V | TP1 | 3.3V ± 3% | _____ V | ☐ ☐ |
| 5.0V | TP2 | 5.0V ± 5% | _____ V | ☐ ☐ |
| Battery | TP3 | X.X V ± X% | _____ V | ☐ ☐ |

3. Vary input voltage from X V to Y V, verify regulation

**Pass:** ☐ Yes ☐ No
**Tested by:** _________ **Date:** _______

---

### Test 3: MCU Programming and Boot Test

**Objective:** Verify MCU can be programmed and boots correctly

**Steps:**
1. Connect programmer/debugger:
   - [ ] USB cable connected
   - [ ] SWD/JTAG connected (if applicable)
   - [ ] Serial adapter connected (if applicable)

2. Flash firmware:
   ```bash
   # Command to flash firmware
   platformio run -t upload
   # or
   esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash 0x1000 firmware.bin
   ```

3. Open serial monitor at XXXX baud
4. Press reset button
5. Observe boot messages

**Expected Results:**
- Firmware flashes successfully
- Boot messages appear on serial
- No error messages
- LED blinks during boot (if applicable)

**Actual Results:**
- Flash status: ☐ Success ☐ Failed
- Boot messages: ☐ Correct ☐ Errors
- Logs:
```
[Paste boot log here]
```

**Pass:** ☐ Yes ☐ No
**Tested by:** _________ **Date:** _______

---

### Test 4: Communication Test

**Objective:** Verify communication interfaces work

#### 4A: WiFi/Bluetooth Test (if applicable)

**Steps:**
1. Power on device
2. Use smartphone/computer to scan for device
3. Attempt connection
4. Send test data
5. Verify data received correctly

**Expected Results:**
- Device appears in scan (SSID/BLE name: _______)
- Connection successful
- Data transmitted/received correctly

**Actual Results:**
- Signal strength: _____ dBm
- Connection: ☐ Success ☐ Failed
- Data transfer: ☐ OK ☐ Failed

**Pass:** ☐ Yes ☐ No

#### 4B: USB Communication Test (if applicable)

**Steps:**
1. Connect USB cable to computer
2. Verify device enumeration:
   - Linux: `lsusb` or `dmesg`
   - macOS: System Information → USB
   - Windows: Device Manager

3. Open serial terminal at XXXX baud
4. Send test command: `test`
5. Verify response

**Expected Results:**
- Device recognized as: [Device name/VID:PID]
- Serial port appears: /dev/ttyUSBX or COMX
- Test command returns: `OK` or expected response

**Actual Results:**

**Pass:** ☐ Yes ☐ No
**Tested by:** _________ **Date:** _______

---

### Test 5: Sensor Test

**Objective:** Verify sensors are functional and reading reasonable values

**Steps:**
1. Power on device
2. Read sensor values via serial/display
3. Apply known stimulus to each sensor
4. Verify readings change appropriately

#### Sensor 1: [Name]

| Stimulus | Expected Reading | Actual Reading | Pass/Fail |
|----------|-----------------|---------------|-----------|
| Ambient | X ± Y units | _____ | ☐ ☐ |
| [Test condition 1] | X ± Y units | _____ | ☐ ☐ |
| [Test condition 2] | X ± Y units | _____ | ☐ ☐ |

#### Sensor 2: [Name]

[Same table structure]

**Pass:** ☐ Yes ☐ No
**Tested by:** _________ **Date:** _______

---

### Test 6: Output Test

**Objective:** Verify all outputs function correctly

#### 6A: LED Test

**Steps:**
1. Send command to illuminate each LED
2. Verify correct LED lights up
3. Verify color and brightness

| LED | Expected | Result | Pass/Fail |
|-----|----------|--------|-----------|
| LED1 (Power) | Green, steady | | ☐ ☐ |
| LED2 (Status) | Red, blinking | | ☐ ☐ |
| RGB LED | Cycles colors | | ☐ ☐ |

**Pass:** ☐ Yes ☐ No

#### 6B: Audio Test (if applicable)

**Steps:**
1. Send command to play test tone
2. Verify audible output
3. Measure frequency with oscilloscope (optional)

**Expected:** X Hz tone, X dB volume
**Actual:** _____ Hz, audible ☐ yes ☐ no

**Pass:** ☐ Yes ☐ No

#### 6C: Motor/Actuator Test (if applicable)

[Add steps for testing motors or other actuators]

**Pass:** ☐ Yes ☐ No
**Tested by:** _________ **Date:** _______

---

### Test 7: Button/Input Test

**Objective:** Verify all user inputs work correctly

**Steps:**
1. Press each button
2. Verify device responds
3. Test combinations (if applicable)

| Button | Action | Expected Response | Result | Pass/Fail |
|--------|--------|------------------|--------|-----------|
| Button 1 | Press | LED toggles | | ☐ ☐ |
| Button 2 | Press | Mode change | | ☐ ☐ |
| Buttons 1+2 | Hold 3s | Enter config | | ☐ ☐ |

**Pass:** ☐ Yes ☐ No
**Tested by:** _________ **Date:** _______

---

### Test 8: Battery/Charging Test (if applicable)

**Objective:** Verify battery charging and operation

**Steps:**
1. Disconnect USB/wall power
2. Install battery (X.X V, X mAh)
3. Measure battery voltage at TP: _____ V
4. Power on device, verify operation
5. Connect charger
6. Verify charging LED illuminates
7. Measure charging current: _____ mA
8. Allow to charge for 10 minutes
9. Verify battery voltage increased: _____ V

**Expected Results:**
- Device operates on battery: ☐ Yes
- Charging current: X-Y mA
- Charging LED: ☐ On
- Voltage increase: > 0.1V in 10 min

**Pass:** ☐ Yes ☐ No
**Tested by:** _________ **Date:** _______

---

### Test 9: Stress Test (Optional for Prototype)

**Objective:** Verify operation under extended use

**Steps:**
1. Run device continuously for X hours
2. Monitor temperature every 30 minutes
3. Verify no degradation in performance
4. Check for memory leaks (firmware)

**Temperature Log:**
- 0 min: _____ °C
- 30 min: _____ °C
- 60 min: _____ °C
- [Continue as needed]

**Maximum temperature:** _____ °C
**Component:** [Which component was hottest]

**Pass:** ☐ Yes ☐ No
**Tested by:** _________ **Date:** _______

---

## Test Summary

**Overall Result:** ☐ PASS ☐ FAIL

**Tests Passed:** _____ / _____

**Failed Tests:**
1. [List failed test numbers and brief description]
2.

**Issues Found:**
1. [Issue description]
   - Severity: ☐ Critical ☐ Major ☐ Minor
   - Action: [What needs to be fixed]

**Recommendations:**
- [ ] Pass unit for shipment
- [ ] Rework required: [Describe]
- [ ] Return to engineering for redesign
- [ ] Additional testing needed: [Specify]

---

## Approval

**Tested by:** _____________________ **Date:** __________

**Reviewed by:** ____________________ **Date:** __________

**Disposition:** ☐ Accepted ☐ Rework ☐ Rejected

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | YYYY-MM-DD | Initial release |

---

*Template by Claude Code*
