# TABLE WARS - Breadboard First Approach

**IMPORTANT: Build a breadboard prototype BEFORE you solder anything!**

This guide shows you the smart way to build your first puck.

---

## 🤔 The Confusion: Do I Need a Breadboard?

### Short Answer:
- **Final puck**: No breadboard (everything soldered together permanently)
- **First build**: YES, absolutely use a breadboard for testing!

### Why I Should Have Been Clearer:

**What I described in docs**: Permanent soldered assembly (final product)

**What you should ACTUALLY do first**: Breadboard prototype → Test → THEN permanent solder

**Think of it like this**:
- Breadboard = Rough draft (test, iterate, fix mistakes fast)
- Soldered puck = Final version (permanent, goes in enclosure)

---

## 📋 The Two-Phase Build Strategy

### Phase 1: Breadboard Prototype (1-2 hours) ✅ START HERE

**Goal**: Test that everything works BEFORE committing to solder

**What you need**:
```
Breadboard Test Kit (~$20 if you don't have it):
├─ 1× Full-size breadboard (830 tie points): $6
├─ 1× Jumper wire kit (male-male): $8
├─ 1× Jumper wire kit (male-female): $6
└─ TOTAL: $20

Plus components you already have:
├─ 1× ESP32 DevKitC-32
├─ 1× WS2812B LED ring
├─ 1× MPU6050
├─ 1× Button
├─ 1× Buzzer
├─ 1× Motor
├─ 1× 330Ω resistor
├─ USB-C cable (for power during testing)
```

**What you DON'T need yet**:
- ❌ Battery (use USB power)
- ❌ TP4057 charger (not needed for USB testing)
- ❌ MT3608 boost converter (can test LEDs at 3.3V for now)
- ❌ Soldering iron
- ❌ Enclosure

**Benefits**:
✅ No soldering = no mistakes to fix
✅ Easy to rewire if you mess up
✅ Test firmware before permanent build
✅ Catch wiring errors instantly
✅ Learn how everything connects

**Time**: 1-2 hours to working prototype

---

### Phase 2: Permanent Solder Build (2-4 hours)

**Goal**: Build the actual puck after you KNOW it works

**What you need**:
```
Everything from Phase 1, PLUS:
├─ Soldering iron + solder
├─ 30 AWG wire (for permanent connections)
├─ Battery + TP4057 charger
├─ MT3608 boost converter
├─ Multimeter (for adjusting MT3608)
└─ Enclosure (when ready)
```

**Benefits**:
✅ You already know the wiring (tested on breadboard)
✅ Confidence level: 95% it will work first try
✅ No "is this solder bad or wiring wrong?" debugging
✅ Faster build (just replicate what worked)

**Time**: 2-4 hours (vs 6-8 hours if you skip breadboard)

---

## 🔌 Phase 1: Breadboard Wiring (Step-by-Step)

### What Your Breadboard Will Look Like:

```
Breadboard Layout:
┌────────────────────────────────────────┐
│  [ESP32 DevKitC-32 straddling center]  │
│                                        │
│  Left side:              Right side:   │
│  - 3.3V rail            - GND rail     │
│  - Button               - LED ring     │
│  - MPU6050              - Motor        │
│                         - Buzzer       │
└────────────────────────────────────────┘
```

### Step 1: Insert ESP32 into Breadboard

```
1. Place breadboard flat on table
2. Find the center gap (runs down middle)
3. Insert ESP32 so pins straddle the gap
   - Left side pins go into left columns
   - Right side pins go into right columns
4. Press firmly (don't bend pins!)
```

**Tip**: ESP32 should sit in rows 10-30 (plenty of room above/below)

---

### Step 2: Set Up Power Rails

**Connect 3.3V rail**:
```
ESP32 pin "3.3V" → Breadboard (+) power rail (red line)
```

**Connect GND rail**:
```
ESP32 pin "GND" → Breadboard (-) ground rail (blue/black line)
```

**Use jumper wires** (male-male, included in kit)

**Test**: Plug ESP32 into USB-C → LED on board should light up

---

### Step 3: Connect LED Ring

**LED ring has 3 wires**:
```
LED Ring          Breadboard Connection
├─ 5V     →  3.3V rail (for testing, use 3.3V)
├─ GND    →  GND rail
└─ DIN    →  ESP32 GPIO 13 (through 330Ω resistor)
```

**How to connect**:
1. LED ring "5V" wire → (+) power rail (red)
2. LED ring "GND" wire → (-) ground rail (black)
3. 330Ω resistor: One leg in same row as GPIO 13, other leg in empty row
4. LED ring "DIN" wire → Same row as resistor's other leg

**Jumper wires**: Use male-female (male into breadboard, female onto LED ring pins)

**Test**: Upload firmware → LEDs should light up (dimmer than usual, that's okay!)

---

### Step 4: Connect MPU6050

**MPU6050 has 4 wires (I2C)**:
```
MPU6050          Breadboard Connection
├─ VCC    →  3.3V rail (NOT 5V!)
├─ GND    →  GND rail
├─ SDA    →  ESP32 GPIO 21
└─ SCL    →  ESP32 GPIO 22
```

**Jumper wires**: Male-female (male to breadboard, female to MPU6050 pins)

**Test**: Upload firmware → Serial Monitor should show "MPU6050 initialized"

---

### Step 5: Connect Button

**Button has 2 legs**:
```
Button Leg 1  →  ESP32 GPIO 27
Button Leg 2  →  GND rail
```

**How to wire**:
1. Insert button into breadboard (straddles 4 rows)
2. One leg connects to GPIO 27 row (jumper wire)
3. Other leg connects to GND rail (jumper wire)

**Test**: Press button → LED should flash green

---

### Step 6: Connect Buzzer

**Buzzer has 2 wires**:
```
Buzzer (+)  →  ESP32 GPIO 15
Buzzer (-)  →  GND rail
```

**Polarity matters!** Red/long leg = (+), Black/short leg = (-)

**Test**: Upload firmware → Should hear beep on startup

---

### Step 7: Connect Motor

**Motor needs transistor circuit** (slightly complex, but doable):

```
Circuit:
ESP32 GPIO 12 → 2.2kΩ resistor → Transistor BASE
Transistor EMITTER → GND rail
Transistor COLLECTOR → Motor (-)
Motor (+) → 3.3V rail
1N4148 diode across motor (stripe to +)
```

**Step-by-step**:
1. Insert transistor into breadboard (3 legs: E-B-C)
2. 2.2kΩ resistor from GPIO 12 to transistor BASE
3. Transistor EMITTER to GND rail
4. Motor (-) wire to transistor COLLECTOR row
5. Motor (+) wire to 3.3V rail
6. Diode: Stripe end to 3.3V rail, other end to motor (-)

**Test**: Upload firmware → Motor should vibrate briefly

---

### Complete Breadboard Wiring Diagram

```
ESP32 Pins → Connections:
├─ 3.3V    → Power rail (+)
├─ GND     → Ground rail (-)
├─ GPIO 13 → 330Ω resistor → LED Ring DIN
├─ GPIO 21 → MPU6050 SDA
├─ GPIO 22 → MPU6050 SCL
├─ GPIO 27 → Button leg 1 (leg 2 to GND)
├─ GPIO 15 → Buzzer (+) ((-) to GND)
└─ GPIO 12 → 2.2kΩ → Transistor BASE → Motor circuit

LED Ring:
├─ 5V  → 3.3V rail (temp, for testing)
├─ GND → GND rail
└─ DIN → GPIO 13 (via 330Ω)

MPU6050:
├─ VCC → 3.3V rail
├─ GND → GND rail
├─ SDA → GPIO 21
└─ SCL → GPIO 22

Motor Circuit:
├─ Motor (+) → 3.3V rail
├─ Motor (-) → Transistor COLLECTOR
├─ Transistor EMITTER → GND
├─ Transistor BASE → 2.2kΩ → GPIO 12
└─ Diode across motor (stripe to +)
```

---

## ✅ Testing Your Breadboard Prototype

### Upload Firmware

```bash
cd table-wars-puck
pio run --target upload
pio device monitor
```

### What Should Happen:

**On boot**:
✅ Serial Monitor: "ESP32 initialized"
✅ LEDs: Spin animation (cyan)
✅ Buzzer: Single beep
✅ Serial: "MPU6050 initialized"

**Press button**:
✅ LEDs: Flash green
✅ Buzzer: Beep
✅ Motor: Quick vibration
✅ Serial: "Button pressed"

**Shake puck**:
✅ LEDs: Rainbow burst
✅ Motor: Vibrate during animation
✅ Serial: "Shake detected! Magnitude: 18.5"

**If all of the above works → YOU'RE READY FOR PERMANENT BUILD!**

---

## 🚨 Troubleshooting Breadboard Build

### LEDs Don't Light Up

**Check**:
- [ ] LED ring 5V connected to 3.3V rail?
- [ ] LED ring GND connected to GND rail?
- [ ] GPIO 13 → 330Ω resistor → LED DIN?
- [ ] 330Ω resistor oriented correctly? (doesn't matter, but check connection)
- [ ] LED ring is WS2812B? (not WS2811 or WS2813)

**Test**: Use multimeter → Check voltage at LED ring 5V pin (should be ~3.3V)

---

### MPU6050 "Not Found" Error

**Check**:
- [ ] MPU VCC connected to 3.3V (NOT 5V!)
- [ ] SDA to GPIO 21?
- [ ] SCL to GPIO 22?
- [ ] Not swapped? (Try swapping SDA ↔ SCL)

**Test**:
```bash
pio device monitor
# Look for "I2C device found at address 0x68"
```

---

### Button Doesn't Work

**Check**:
- [ ] One button leg to GPIO 27?
- [ ] Other leg to GND?
- [ ] Button fully inserted into breadboard?

**Test**: Use multimeter in continuity mode
- Touch probes to button legs
- Press button → should beep

---

### Motor Doesn't Vibrate

**Check**:
- [ ] Transistor oriented correctly? (E-B-C, check datasheet)
- [ ] 2.2kΩ resistor from GPIO 12 to BASE?
- [ ] Motor (+) to 3.3V?
- [ ] Motor (-) to COLLECTOR?
- [ ] EMITTER to GND?
- [ ] Diode stripe facing correct way? (toward +)

**Test**: Bypass transistor
- Connect motor (+) directly to 3.3V
- Connect motor (-) directly to GND
- Motor should spin

If motor works direct → transistor circuit is wrong

---

### Everything Looks Right But Doesn't Work

**Systematic debug**:

1. **Check power first**:
   - Measure 3.3V rail with multimeter (should be 3.2-3.4V)
   - Measure GND (should be 0V)

2. **Test ESP32 alone**:
   - Disconnect everything
   - Upload simple "blink" sketch
   - If that works, ESP32 is fine

3. **Add components one by one**:
   - Start with LEDs only → Test
   - Add MPU6050 → Test
   - Add button → Test
   - Add buzzer → Test
   - Add motor → Test

4. **Check jumper wires**:
   - Pull out, reinsert firmly
   - Some jumpers are bad (buy spares)

5. **Take a break**:
   - Walk away for 15 minutes
   - Come back with fresh eyes
   - You'll probably spot the issue

---

## 🎯 Phase 2: Permanent Solder Build

**ONLY after breadboard prototype works 100%!**

### Key Differences from Breadboard:

| Breadboard | Permanent Solder |
|-----------|------------------|
| 3.3V power (USB) | 3.7V battery |
| No MT3608 | MT3608 for 5V LEDs |
| No TP4057 | TP4057 for charging |
| Jumper wires | 30 AWG soldered wires |
| Loose connections | Permanent solder joints |
| No enclosure | Fits in 95mm enclosure |

### Assembly Steps:

**Step 1**: Adjust MT3608 to 5.0V (see MT3608_WIRING.md)

**Step 2**: Solder wires to ESP32 pins (same connections as breadboard)

**Step 3**: Solder wires to LED ring (now use 5V from MT3608)

**Step 4**: Solder MPU6050, button, buzzer (same as breadboard)

**Step 5**: Build motor transistor circuit on small PCB or perfboard

**Step 6**: Add battery + TP4057 charger

**Step 7**: Test everything before putting in enclosure

**Step 8**: Install in enclosure (once 3D printed)

**Time**: 2-4 hours (you already know it works!)

---

## 🛒 What to Buy Right Now

### If You Have ZERO Parts:

**Buy this week** (Breadboard test kit - $60 total):
- [ ] Breadboard (830 tie points): $6
- [ ] Jumper wire kit (male-male, 65 pcs): $6
- [ ] Jumper wire kit (male-female, 40 pcs): $6
- [ ] 1× ESP32 DevKitC-32: $8
- [ ] 1× WS2812B LED ring: $5
- [ ] 1× GY-521 MPU6050: $3
- [ ] 1× Button (pack of 25): $5
- [ ] 1× Buzzer (pack of 10): $8
- [ ] 1× Vibration motor (pack of 5): $8
- [ ] Resistor kit (330Ω, 2.2kΩ): $10
- [ ] 1N4148 diode pack: $5

**Build ONLY the breadboard prototype this week**

**Test firmware, play games, demo to friends**

**LATER** (after breadboard works):
- [ ] Battery + charger + MT3608 (for permanent build)
- [ ] Soldering supplies
- [ ] More ESP32s for scaling

---

### If You Already Have Parts (Like You):

**Buy just the breadboard kit** ($20):
- [ ] Breadboard: $6
- [ ] Jumper wires (male-male): $8
- [ ] Jumper wires (male-female): $6

**You already have**:
✅ ESP32, LED ring, MPU6050, button, buzzer, motor, resistors

**Build breadboard prototype THIS WEEK**

**Order permanent build stuff LATER** (battery, charger, MT3608, enclosure)

---

## 📊 Time & Cost Comparison

### Path A: Skip Breadboard (What I Originally Described)

```
Time:
├─ Read wiring guide: 30 min
├─ Solder everything: 3 hours
├─ Power on... doesn't work: 5 min
├─ Debug for 2 hours (is it solder? wiring? dead part?)
├─ Desolder, fix, re-solder: 1 hour
├─ Test again... works!
└─ TOTAL: 6.5 hours (high frustration)

Cost:
├─ Components: $45
├─ No breadboard needed: $0
└─ TOTAL: $45

Success Rate: 50% on first try
```

---

### Path B: Breadboard First (SMART PATH)

```
Time:
├─ Breadboard prototype: 1.5 hours
├─ Test, fix mistakes (easy!): 30 min
├─ Permanent solder build: 2.5 hours
├─ Power on... WORKS FIRST TIME!
└─ TOTAL: 4.5 hours (low frustration)

Cost:
├─ Components: $45
├─ Breadboard + jumpers: $20
└─ TOTAL: $65

Success Rate: 90% on first try

Savings:
├─ 2 hours saved (vs Path A)
├─ Way less frustration
├─ Breadboard reusable for pucks 2-6
└─ Worth the extra $20!
```

---

## ✅ My Strong Recommendation

### **Breadboard First. Always.**

**Why**:
1. You'll understand the system deeply
2. You can demo to bars while testing (good enough for pilots!)
3. You'll catch mistakes BEFORE committing to solder
4. You'll build confidence before permanent assembly
5. The $20 breadboard cost saves you 2-4 hours

**Timeline**:

**This week**:
- Order breadboard kit ($20)
- Build prototype (1-2 hours)
- Test all games (1 hour)

**Next week**:
- Demo to 5 bars using breadboard prototype!
- It's functional, LEDs work, games play
- Bars don't care if it's on a breadboard

**Week 3-4**:
- If bars want to pilot → build permanent versions
- Order batteries, chargers, MT3608
- Solder permanent pucks for deployment

**Don't build 6 permanent pucks until you validate demand!**

---

## 🎯 Bottom Line

### The Question You Asked: "Do I Need a Breadboard?"

**Answer**:

**Final puck? No.**

**First build? ABSOLUTELY YES.**

**It's the difference between**:
- 😰 6 hours of soldering + debugging + frustration
- 😊 2 hours of easy plug-and-play testing

**Buy the $20 breadboard kit. Build the prototype. Test it.**

**THEN decide if you want to build 6 permanent soldered pucks.**

**You might even use the breadboard version for your first 5 pilot bars!**

It works. It's ugly. But it proves the concept.

**That's what validation looks like.** 🚀
