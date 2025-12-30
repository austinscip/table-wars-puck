# LED Ring - Where It Is and What It Looks Like

## ⚡ LED RING IS ELECTRONIC HARDWARE, NOT 3D PRINTED!

---

## WHAT IS THE LED RING?

**Physical Component:**
- WS2812B addressable RGB LED ring
- 16 individual LEDs in a circle
- 60mm outer diameter
- Pre-mounted on small circular PCB
- Has 3 wires: +5V, GND, Data

**What it looks like:**
```
        LED  LED  LED
      LED           LED
    LED               LED
   LED     [HOLE]      LED
   LED                 LED
    LED               LED
      LED           LED
        LED  LED  LED

↑ 16 LEDs in a ring, 60mm diameter
```

**Example Product:**
- Adafruit NeoPixel Ring - 16 x 5050 RGB LED
- Or equivalent WS2812B ring
- ~$10-15 per ring

---

## WHERE DOES IT GO IN THE ASSEMBLY?

### **Stack Order (Bottom to Top):**

```
Layer 7: Button Cap (translucent, you press this)
         ↓
Layer 6: Top Shell (dome, translucent blue PETG)
         ↓
Layer 5: LED RING ← HERE! (sits near top, under dome)
         ↓
Layer 4: Battery (3.7V LiPo, above PCB)
         ↓
Layer 3: Custom PCB (89mm circular, has all electronics)
         ↓
Layer 2: PCB Standoffs (6 posts, hold PCB)
         ↓
Layer 1: Bottom Shell (base, solid black PETG)
```

**LED Ring Position:**
- Height: ~30mm from base (near the top)
- Sits INSIDE the top shell
- Below the translucent dome
- Light shines UP through dome and creates glow effect

---

## WHAT WE 3D PRINT FOR THE LED RING

### **In Top Shell (forerunner_top_shell_v2.stl):**

**1. LED Ring Standoffs (4 small posts):**
- 4 cylindrical posts at 90° spacing
- 30mm radius from center
- 3mm tall posts
- Hold the LED ring in position

**Where to see them:**
- Open forerunner_top_shell_v2.stl
- Look at INSIDE (flip upside down)
- See 4 small posts in a circle
- These support the LED ring PCB

**2. Light Diffusion Channels (16 radial grooves):**
- 16 shallow grooves radiating from center
- 0.5mm deep channels
- Spread LED light evenly across dome
- Create "energy flowing" Forerunner effect

---

## HOW SID WILL CONNECT IT

### **Option A: Mount on Main PCB**
```
Main PCB (89mm) has:
- LED ring connector pads around edge
- 16 connection points
- LED ring sits on top of PCB or
- LED ring connects with short wires
```

### **Option B: Separate Mount with Wires**
```
LED Ring (separate) connects to:
- Main PCB via 3 wires (+5V, GND, Data)
- LED ring held by standoffs in top shell
- Wires run from PCB to ring
```

**Sid will decide which is better based on PCB layout.**

---

## WHAT IT LOOKS LIKE WHEN ASSEMBLED

### **Powered OFF:**
```
Look through translucent top shell:
- See the faint outline of LED ring
- 16 small LED squares visible
- Circular pattern ~60mm diameter
```

### **Powered ON:**
```
GLOWING dome effect!
- LEDs illuminate translucent dome
- Light diffuses through channels
- Creates Forerunner "energy ring" effect
- Can change colors (RGB addressable)
- Can animate (chase patterns, pulse, etc.)
```

---

## IN THE ASSEMBLED VIEW (OpenSCAD)

**In assembled_view_v3_pcb.scad:**

Look for the **YELLOW ring** near the top:
```openscad
// LED ring (connects to PCB pads, extends up into top shell)
translate([0, 0, pcb_z + 18])
    color(led_ring_color, 0.85)
        difference() {
            cylinder(h = 2, d = 60);
            cylinder(h = 3, d = 50);
        }
```

**How to see it in OpenSCAD:**
1. Open assembled_view_v3_pcb.scad (should be open)
2. Press F5 to preview
3. Look for YELLOW ring near top of assembly
4. It's under the translucent blue dome
5. 60mm diameter donut shape

---

## WHY THERE'S NO LED RING STL FILE

**The LED ring is NOT 3D printed because:**

1. ❌ Can't 3D print LEDs (obviously!)
2. ❌ Can't 3D print electronics
3. ❌ Can't 3D print circuit boards
4. ✅ We buy pre-made WS2812B LED rings
5. ✅ Sid will source and solder it

**What we DO print:**
- ✅ Standoffs to hold it (in top shell)
- ✅ Light diffusion features (channels)
- ✅ Translucent dome (lets light through)

---

## WHAT SID NEEDS TO PROVIDE

**As part of his PCB assembly, Sid will:**

1. **Source the LED ring:**
   - WS2812B 16-LED ring (60mm)
   - Or equivalent addressable RGB ring
   - ~$10-15 component cost

2. **Connect it to main PCB:**
   - Either mount on PCB directly, OR
   - Connect with wires (3 wires: +5V, GND, Data)
   - Add level shifter (3.3V→5V) for data line

3. **Test it:**
   - Verify all 16 LEDs work
   - Test color control
   - Test animations

**This is included in the assembly quote you'll get from Sid.**

---

## LED RING IN THE 5 STL FILES

Here's what each STL file does for the LED system:

```
┌─────────────────────────────────┬──────────────────┐
│ STL File                        │ LED Function     │
├─────────────────────────────────┼──────────────────┤
│ forerunner_top_shell_v2.stl     │ • Standoffs      │
│                                 │ • Light channels │
│                                 │ • Translucent    │
├─────────────────────────────────┼──────────────────┤
│ forerunner_bottom_shell_v3.stl  │ • Wire routing   │
│                                 │ • PCB mounting   │
├─────────────────────────────────┼──────────────────┤
│ button_glyph_cap_v2.stl         │ • (none)         │
├─────────────────────────────────┼──────────────────┤
│ bumper_ring_tpu.stl             │ • (none)         │
├─────────────────────────────────┼──────────────────┤
│ motor_sock_tpu.stl              │ • (none)         │
└─────────────────────────────────┴──────────────────┘
```

**Only the top shell has LED-related features!**

---

## VISUAL REFERENCE

### **Where LED Ring Sits:**

```
Side View Cross-Section:

        [Button Cap] ← You press here
             ↓
    ╔════════════════════╗
    ║  Top Shell (dome)  ║ ← Translucent PETG
    ║                    ║
    ║    ⭕ LED RING     ║ ← 60mm ring, ~30mm height
    ║                    ║
    ╠────────────────────╣ ← Seam
    ║                    ║
    ║   [Battery]        ║
    ║                    ║
    ║   [PCB - 89mm]     ║ ← All electronics
    ║                    ║
    ╚════════════════════╝
     Bottom Shell (base)
```

### **Top View:**

```
Looking Down Through Top Shell:

         Energy Rings
         (decorative)
            ↓
    ┌─────────────────┐
    │    ╱╲  ╱╲  ╱╲   │ ← Light diffusion channels
    │   ╱  ╲╱  ╲╱  ╲  │    (radial grooves)
    │  │   [BTN]   │  │ ← Button at center
    │   ╲  ╱╲  ╱╲  ╱  │
    │    ╲╱  ╲╱  ╲╱   │
    │                 │
    │   ⭕⭕⭕⭕⭕⭕⭕  │ ← LED Ring (60mm circle)
    │  ⭕         ⭕   │    16 LEDs around perimeter
    │ ⭕           ⭕  │
    │ ⭕           ⭕  │
    │  ⭕         ⭕   │
    │   ⭕⭕⭕⭕⭕⭕⭕  │
    │                 │
    └─────────────────┘
```

---

## SHOULD YOU SEE IT IN THE STL FILES?

**NO! Because:**

1. **Top Shell STL** - You'll see:
   - ✅ 4 small standoff posts (for mounting LED ring)
   - ✅ Light diffusion channels (grooves)
   - ❌ No LED ring (it's hardware, not printed)

2. **Bottom Shell STL** - You'll see:
   - ❌ No LED features (LEDs are at the top)

3. **Other STL Files** - No LED features

**The LED ring itself comes from Sid as electronic hardware!**

---

## SUMMARY

**3D Printed Parts (What You Send to Sid):**
- Top shell with LED standoffs ✅
- Bottom shell ✅
- Button cap ✅
- TPU parts ✅

**Electronic Hardware (What Sid Provides):**
- WS2812B LED ring (16 LEDs, 60mm) ← THIS!
- Custom PCB
- ESP32 chip
- MPU6050
- Battery
- All other components

**Final Assembly:**
- Sid installs LED ring in top shell
- LED ring connects to main PCB
- Light shines through translucent dome
- Creates awesome Forerunner glow effect

---

## IN PREVIEW APP RIGHT NOW

**You should see 5 Preview windows (or tabs):**

1. **forerunner_top_shell_v2.stl** (LARGEST)
   - Domed lid
   - Look inside: See 4 small LED standoff posts
   - Look outside: See energy rings on top

2. **forerunner_bottom_shell_v3_pcb.stl**
   - Cup shape
   - See 6 PCB standoffs inside

3. **button_glyph_cap_v2.stl** (SMALL)
   - Disc with Forerunner glyph

4. **bumper_ring_tpu.stl**
   - Donut/ring shape

5. **motor_sock_tpu.stl** (TINY)
   - Small cylinder

**Do you see these 5 files in Preview now?**

**LED ring is NOT in there - it's electronic hardware Sid will provide!**
