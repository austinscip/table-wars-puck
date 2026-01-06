# TABLE WARS Enclosure - CAD Designer Checklist

Quick reference for implementing the Forerunner puck enclosure.

---

## 📋 START HERE

**Base files**: Your existing `forerunner_top.stl` and `forerunner_bottom.stl`

**Full spec**: See `ENCLOSURE_SPEC.md` for complete details

**Goal**: Bar-durable 3D-printable enclosure with Halo Forerunner aesthetic

---

## ✅ TOP SHELL CHECKLIST

- [ ] **Diameter**: 95mm (increased from 90mm)
- [ ] **Wall thickness**: 3.0mm (increased from 1.5-2mm)
- [ ] **Dome height**: 8mm above rim
- [ ] **Material**: Design for translucent PETG

### Features to Add:

- [ ] **Button hole**: 12mm diameter in center (NOT flex membrane!)
- [ ] **LED ring mounts**: 4× M2 standoff positions at 53mm diameter circle
  - [ ] Standoff height: 12mm from interior surface
  - [ ] Positions: 0°, 90°, 180°, 270°
- [ ] **Concentric rings**: 3× raised rings (0.5mm height) for light diffusion
- [ ] **Zip-tie anchor**: 2mm diameter post near LED ring
- [ ] **O-ring groove receiver**: 2mm alignment lip on rim (mates with bottom shell)
- [ ] **Interior texture**: Fine sand pattern for light diffusion (optional - can be post-processed)

### Structural:

- [ ] **Screw holes**: 6× countersunk for M3 screw heads
  - [ ] Evenly spaced around perimeter
  - [ ] 6mm diameter shallow recess (hide screw heads)
- [ ] **Alignment nubs**: 3× small pins (2mm dia) for shell alignment

---

## ✅ BOTTOM SHELL CHECKLIST

- [ ] **Diameter**: 95mm (matching top)
- [ ] **Wall thickness**: 3.5mm (increased from 2.5mm)
- [ ] **Internal height**: 32mm
- [ ] **External height**: 40mm total

### Critical Features:

- [ ] **6× screw bosses** with brass insert pockets
  - [ ] M3 × 4mm insert pockets (4.2mm diameter × 5mm deep)
  - [ ] Boss diameter: 7mm (strong enough)
  - [ ] Positions: Match top shell holes

- [ ] **O-ring groove**: 2mm wide × 2mm deep on top rim
  - [ ] For 90mm ID O-ring
  - [ ] Clean sharp corners for good seal

- [ ] **Alignment lip**: 3mm tall × 2mm wide around inside of rim

- [ ] **TPU bumper groove**: 2mm × 2mm channel around equator seam line

### Component Mounts:

- [ ] **Center button tower**: 20mm × 20mm × 10mm tall
  - [ ] Positioned dead center
  - [ ] Hollow interior for wiring
  - [ ] 2× M2 mounting holes on top surface

- [ ] **ESP32 standoffs**: 4× M2 threaded posts
  - [ ] Height: 6mm from base
  - [ ] Positions: Match ESP32 mounting holes (56mm × 28mm spacing)
  - [ ] 3mm clearance to side walls

- [ ] **MPU6050 standoffs**: 2× M2 threaded posts
  - [ ] Height: 5mm from base
  - [ ] Position: 25mm from center (near edge)

- [ ] **Battery tray**: Recessed pocket
  - [ ] Dimensions: 62mm × 37mm × 9mm deep
  - [ ] 5mm × 50mm flat area for velcro
  - [ ] Tray floor: 2mm thick (solid)
  - [ ] 4× ventilation slots: 3mm × 15mm

- [ ] **Motor pocket**: Circular recess
  - [ ] Diameter: 12.5mm
  - [ ] Depth: 8mm
  - [ ] Position: 30mm from center (opposite side from MPU)

- [ ] **Buzzer recess**: Circular pocket
  - [ ] Diameter: 23mm
  - [ ] Depth: 4mm
  - [ ] Position: 20mm from center

- [ ] **TP4057 charger cutout**: Rectangular opening in side wall
  - [ ] Width: 10mm
  - [ ] Height: 5mm
  - [ ] Center height: 8mm from base
  - [ ] 0.5mm fillet on interior corners
  - [ ] Small mounting area for 2× M2 screws or hot glue

### Ventilation:

- [ ] **4× thermal vent glyphs** near ESP32 location
  - [ ] Each vent: 3mm × 10mm slot
  - [ ] 90° spacing, 15mm from center
  - [ ] Forerunner symbol shape

- [ ] **6× sound vents** above buzzer location
  - [ ] Each vent: 2mm × 8mm slot
  - [ ] Circular pattern
  - [ ] Also serves as heat exhaust

### Base Features:

- [ ] **4× TPU bumper recesses** on bottom
  - [ ] Diameter: 8mm
  - [ ] Depth: 2mm
  - [ ] Arranged in square pattern

- [ ] **Anti-slip texture** on bottom (optional)
  - [ ] Fine diamond knurl: 0.2mm depth

### Wire Management:

- [ ] **Wire routing channels**: Connect all components in star pattern from ESP32
  - [ ] Width: 4mm
  - [ ] Depth: 3mm
  - [ ] Rounded entries: 1mm radius
  - [ ] Routes:
    - [ ] ESP32 → LED ring (top path through center)
    - [ ] ESP32 → Button (center path)
    - [ ] ESP32 → Motor (side path)
    - [ ] ESP32 → Buzzer (side path)
    - [ ] ESP32 → MPU6050 (I2C lines)
    - [ ] Battery → TP4057 → ESP32 (power path)

- [ ] **6× zip-tie anchor posts**: 2mm diameter × 4mm tall
  - [ ] Near LED ring
  - [ ] Near ESP32 (2 posts)
  - [ ] Near battery
  - [ ] Near motor
  - [ ] Near buzzer

---

## ✅ SEPARATE PARTS TO MODEL

### 1. Button Glyph Cap
- [ ] **Outer diameter**: 15mm
- [ ] **Thickness**: 2mm
- [ ] **Forerunner symbol** on top (0.3mm relief)
- [ ] **Center pin**: 3mm diameter × 3mm tall on underside
- [ ] Material: Same as top shell (translucent PETG)

### 2. TPU Motor Sock
- [ ] **Outer diameter**: 12mm
- [ ] **Inner diameter**: 10.2mm (tight friction fit)
- [ ] **Height**: 8mm
- [ ] **Wall thickness**: 0.8mm
- [ ] Material: TPU 95A

### 3. TPU Equator Bumper Ring
- [ ] **Inner diameter**: 95mm (matches shell diameter)
- [ ] **Cross-section**: 2mm × 2mm square profile
- [ ] **Groove fit**: Friction-fits into bottom shell groove
- [ ] Material: TPU 95A

### 4. Optional: USB-C Plug Cover
- [ ] **Fits**: 10mm × 5mm cutout
- [ ] **Thickness**: 3mm
- [ ] **Friction fit** with small retention lip
- [ ] Material: TPU 95A

---

## 📐 CRITICAL DIMENSIONS SUMMARY

```
OVERALL:
├─ Enclosure diameter: 95mm
├─ Total height: 40mm
├─ Top shell wall: 3.0mm
├─ Bottom shell wall: 3.5mm
└─ Seam location: 24mm from base

COMPONENT CLEARANCES:
├─ LED ring shelf: 53mm diameter @ 12mm from top interior
├─ ESP32 area: 56 × 28mm @ 6mm from base
├─ Battery tray: 62 × 37 × 9mm (above ESP32)
├─ Button tower: 20 × 20mm centered
└─ Motor/Buzzer: Near perimeter (30mm from center)

FASTENERS:
├─ 6× M3 screws (10mm length)
├─ 6× M3 × 4mm brass inserts
├─ 4× M2 standoffs for LED ring
└─ Multiple M2 threaded holes for components

SEALING:
├─ O-ring: 90mm ID × 2mm thickness
└─ Bumper: 2 × 2mm square cross-section
```

---

## 🎨 AESTHETIC REQUIREMENTS

Keep the Halo 3 Forerunner style:

- [ ] **Smooth curves** (not angular/blocky)
- [ ] **Concentric energy rings** on top dome
- [ ] **Hexagonal details** around perimeter
- [ ] **Forerunner glyphs** on vents and recesses
- [ ] **Subtle ridges** on bottom shell
- [ ] **Light diffusion channels** radiating from center
- [ ] **"Ancient technology" feel** - polished but weathered

Reference: Halo 3 Forerunner Energy Core / Light Bridge activators

---

## 🖨️ PRINT CONSIDERATIONS

Design with these constraints:

- [ ] **No overhangs > 45°** without support
- [ ] **Minimum wall thickness**: 2.5mm anywhere
- [ ] **Screw boss draft angle**: 2° for easy printing
- [ ] **Support blockers** in screw holes (design consideration)
- [ ] **Brim-friendly base** (flat with no undercuts)
- [ ] **Layer-friendly button hole** (round = good)

Assume printer specs:
- 0.4mm nozzle
- 0.2mm layer height
- ±0.1mm dimensional accuracy

---

## 🔧 ASSEMBLY VALIDATION

Before finalizing, verify:

- [ ] **All screw holes align** between shells
- [ ] **O-ring groove seals properly** (test with real O-ring)
- [ ] **Button hole is accessible** (clearance for 15mm cap)
- [ ] **USB-C is flush** with exterior wall
- [ ] **No interference** between components (use assembly view)
- [ ] **Wire channels connect** all components
- [ ] **Brass inserts fit** properly (test print screw boss first!)

---

## 📦 FINAL DELIVERABLES

Export these files:

### STL Files (Printable):
- [ ] `forerunner_top_v2.stl`
- [ ] `forerunner_bottom_v2.stl`
- [ ] `button_glyph_cap.stl`
- [ ] `motor_sock_tpu.stl`
- [ ] `bumper_ring_tpu.stl`
- [ ] Optional: `usb_plug_tpu.stl`

### Source Files (Editable):
- [ ] `.f3d` or `.step` file for future modifications
- [ ] Component library (all standoffs, inserts, screws)

### Documentation:
- [ ] Exploded assembly view (PNG or PDF)
- [ ] Dimensioned cross-section view
- [ ] Wiring diagram overlay (top view)

---

## ⚡ QUICK WINS (Do These First)

If you're iterating, prioritize:

1. **Screw boss test print** - Verify brass insert fit
2. **Button hole sizing** - Print just the center 30mm × 30mm to test button cap
3. **ESP32 standoff test** - Print mini test piece with 4× standoffs
4. **O-ring groove** - Print 20mm × 20mm rim section to test seal
5. **USB-C cutout** - Print 20mm × 20mm wall section to test TP4057 fit

These mini test prints save hours of full-scale printing!

---

## 🆘 NEED HELP?

**Full details**: See `ENCLOSURE_SPEC.md` (13 sections, 600+ lines)

**Component datasheets**: See `PARTS_LIST.md`

**Electronics layout**: See `WIRING_GUIDE.md`

**Questions?**: Contact project lead with specific CAD questions

---

**Target delivery**: Working STL files for test print within 1-2 weeks

**Success metric**: 6 pucks assembled and tested before bar deployment

Let's build something awesome! 🎮✨
