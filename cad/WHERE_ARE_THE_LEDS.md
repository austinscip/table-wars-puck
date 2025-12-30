# WHERE THE LED LIGHTS ARE

## 📍 LED LOCATION IN THE PUCK

---

## POSITION:

**Height from base:** 30mm (inside the top area, near the dome)

**Arrangement:** 16 individual LEDs in a perfect circle

**Diameter of circle:** 60mm (29mm radius from center)

**Spacing:** 22.5° apart (360° ÷ 16 = 22.5°)

---

## SIDE VIEW (CROSS-SECTION):

```
        [Button Cap] ← Top (42mm)
             ↓
    ╔════════════════════╗
    ║                    ║
    ║  TRANSLUCENT DOME  ║ ← Light shines through this
    ║                    ║
    ║    ⭕ LED RING     ║ ← 30mm height, 60mm diameter
    ║   (16 LEDs here)   ║    UNDER the dome
    ║                    ║
    ╠────────────────────╣ ← Seam (24mm)
    ║                    ║
    ║   [Battery]        ║ ← 18mm height
    ║                    ║
    ║   [PCB - 89mm]     ║ ← 8.5mm height (base + standoffs)
    ║                    ║
    ╚════════════════════╝
     Bottom Shell (0mm)
```

---

## TOP VIEW (LOOKING DOWN):

```
    ┌─────────────────────┐
    │                     │
    │   Energy Rings      │ ← Decorative on dome surface
    │   (decorative)      │
    │                     │
    │      [Button]       │ ← Center
    │                     │
    │   ⭕⭕⭕⭕⭕⭕⭕⭕   │ ← LED Ring (16 LEDs)
    │  ⭕           ⭕    │    60mm diameter circle
    │ ⭕             ⭕   │    UNDER dome, inside puck
    │ ⭕             ⭕   │
    │  ⭕           ⭕    │
    │   ⭕⭕⭕⭕⭕⭕⭕⭕   │
    │                     │
    └─────────────────────┘
         95mm diameter
```

---

## HOW IT WORKS:

### **LEDs are INSIDE, not visible directly:**
1. **16 WS2812B LEDs** sit on small PCB or main PCB
2. **Positioned at 30mm height** (inside the dome area)
3. **60mm diameter circle** around the center
4. **UNDER the translucent blue dome**

### **Light shines THROUGH the dome:**
1. Top shell is **translucent PETG** material
2. When LEDs are **powered ON**, light passes through
3. Creates **glowing ring effect** visible from outside
4. **Light diffusion channels** spread the light evenly
5. **Energy rings** on surface add visual interest

### **When LEDs are OFF:**
- Dome looks solid translucent blue
- LEDs not visible (hidden inside)
- Clean, sleek appearance

### **When LEDs are ON:**
- Dome **glows from inside**
- **16-point ring of light** visible
- **Orange/amber glow** (or any RGB color you program)
- **Forerunner energy containment** aesthetic
- Light spreads through diffusion channels

---

## FILES JUST OPENED:

### **1. PRODUCT_LEDS_ON_angled.png**
Shows the puck with LEDs glowing (powered on)
- See the orange glow through dome
- 16 LEDs visible as glowing ring

### **2. PRODUCT_LEDS_ON_top.png**
Top view showing LED ring position
- See exact circle of 16 LEDs
- See how they're positioned under dome

### **3. PRODUCT_VIEW_LEDS_ON.scad**
Interactive 3D model in OpenSCAD
- Press F5 to render
- Rotate to see from any angle
- See LED glow effect in 3D

---

## COMPARISON:

### **PRODUCT_VIEW.scad** (LEDs OFF):
- Solid translucent blue dome
- No glow visible
- Clean external appearance
- What it looks like when powered off

### **PRODUCT_VIEW_LEDS_ON.scad** (LEDs ON):
- Dome glowing from inside
- Orange LED ring visible
- Light diffusing through dome
- What it looks like when powered on and playing games

---

## IN REAL LIFE:

**When you 3D print and assemble:**

1. **Print top shell in translucent PETG** (blue, clear, or any color)
2. **Sid assembles electronics** with 16-LED WS2812B ring
3. **LEDs mount at 30mm height** inside the puck
4. **Top shell goes over everything** (dome covers LEDs)
5. **When you power it on**, LEDs glow through the dome
6. **RGB addressable** - you can program any color/pattern:
   - Solid colors
   - Rainbow effect
   - Pulsing
   - Chase animations
   - Game-reactive (different colors for different games)

**The translucent dome acts like a LAMPSHADE** - diffusing and spreading the LED light to create a glowing effect.

---

## WHY YOU DON'T SEE THEM IN PRODUCT_VIEW.scad:

Because that shows the **FINISHED EXTERNAL APPEARANCE** with solid materials.

The LEDs are **INTERNAL COMPONENTS** - hidden inside, just like:
- Battery (also inside, not visible)
- PCB (inside, not visible)
- Wiring (inside, not visible)

**You only see the glow when they're powered on!**

---

**SUMMARY:**

**LED Location:** 30mm from base, 60mm diameter circle, 16 LEDs

**Visibility:** Hidden inside, light glows through translucent dome when powered on

**Effect:** Creates glowing ring around perimeter, Forerunner energy aesthetic

**Current Files Open:** Show the LED glow effect so you can see where they are!
