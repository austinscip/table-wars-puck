# TABLE WARS — FORERUNNER ARTIFACT PUCK
## Engineered Enclosure Specification v2.0

**Design Goal**: Create a fully 3D-printable, bar-durable, two-part enclosure modeled after Halo 3 Forerunner Energy Cores, housing an ESP32-based interactive puck with LEDs, haptics, sound, and motion sensing.

---

## 1. EXTERIOR DESIGN (Halo Forerunner Core Aesthetic)

### Top Shell (Translucent Dome)

**Overall Shape**:
- Smooth Forerunner curves with ancient tech aesthetic
- Domed profile rising from circular rim
- Diameter: **95 mm** (increased from 90mm for better durability)
- Dome height: 8 mm above rim
- Wall thickness: **3.0 mm** (increased from 1.5-2mm for drop resistance)

**Surface Details**:
- 3× concentric energy rings (0.5mm RAISED, not engraved)
  - Aligned with LED ring position for light diffusion
  - Rings help with structural rigidity
- Center button area: 12mm diameter recessed glyph circle
- 6× decorative Forerunner hexagon details around perimeter
- Light diffusion channels radiating from center (0.3mm × 1mm)

**Materials**:
- Primary: Translucent PETG (natural or blue-tinted)
- Alternative: Translucent white PLA with frosted finish

**Button Mechanism** ⚠️ CRITICAL CHANGE:
- **Direct tactile button** (NOT flex membrane)
- 12mm diameter through-hole in center
- Separate printed "Forerunner Glyph Cap" (2mm thick)
  - Cap sits flush with top surface
  - Small 3mm pin on underside contacts button stem
  - Friction-fit or light glue to button top
- Button travel: 0.5mm (tactile click feel)

### Bottom Shell (Structural Body)

**Overall Shape**:
- Solid circular body with subtle Forerunner ridges
- Diameter: **95 mm** (matching top shell)
- Internal height: 32 mm
- External height: 40 mm total
- Wall thickness: **3.5 mm** (increased from 2.5mm)

**Base Features**:
- Flat bottom with 4× TPU bumper recesses (8mm diameter × 2mm deep)
- Optional: Forerunner glyph engraving on bottom (0.3mm deep)
- Anti-slip texture: fine diamond knurl pattern (0.2mm)

**Thermal Ventilation** 🌡️ NEW:
- 4× Forerunner vent glyphs near ESP32 location
  - Each vent: 3mm × 10mm slots
  - Positioned 15mm from center, 90° apart
  - Internal air channel ribs directing flow

**Equator Bumper Ring** 🛡️ NEW:
- 2mm wide TPU ring around seam line
- Printed separately in TPU 95A (shore hardness)
- Friction-fits into 2mm × 2mm groove
- Color options: Black, blue, or translucent
- Acts as crumple zone for drops

### Shell Closure System

**Fasteners** 🔩 UPGRADED:
- **6× M3 screws** (upgraded from 4× M2)
- Screw length: 10mm
- Positions: Evenly spaced around perimeter
- Screw heads hidden in shallow Forerunner symbol recesses (6mm diameter)

**Brass Inserts** 🔧 NEW:
- 6× M3 × 4mm brass heat-set inserts
- Installed in bottom shell screw bosses
- Prevents thread stripping during assembly/disassembly
- Install with soldering iron at 200°C

**Sealing** 💧 NEW:
- 2mm × 2mm O-ring groove in bottom shell rim
- O-ring: 90mm ID × 2mm thickness (Buna-N or silicone)
- Provides IP54 splash resistance
- Critical for bar environment (beer spills!)

**Alignment Features**:
- 3mm tall × 2mm wide alignment lip on bottom shell
- 3× small alignment nubs (2mm diameter pins)
- Prevents shell rotation during screw tightening

---

## 2. INTERNAL ENGINEERING LAYOUT

### A. LED Ring Mount

**Component**: 50mm WS2812B 16-LED ring
**Position**: Centered in top shell, facing outward

**Mounting**:
- 4× M2 × 0.4 standoffs (brass or printed)
- Standoff height: 12 mm from top shell interior
- Ring shelf diameter: 53 mm
- Standoffs positioned at 0°, 90°, 180°, 270°

**Light Diffusion Layer** 🎨 NEW:
- Optional: 52mm diameter × 1mm translucent acrylic disc
- Sits 3mm below top shell interior
- Snap-clips or glue in place
- Creates even glow, eliminates LED hot spots
- Sand interior of top shell with 220-grit for frosted effect

**Wiring Access**:
- 4mm × 3mm wire channel from LED ring to ESP32
- Zip-tie anchor post (2mm diameter) near ring

---

### B. Center Button Assembly

**Component**: 12×12mm tactile button with long stem (or 6×6mm with extender)
**Position**: Exact center of bottom shell

**Mounting** 🔘 REDESIGNED:
- Small PCB carrier (20mm × 20mm) OR
- Direct mount to printed "button tower" standoff
- Height: Adjustable 8-12mm (tune for top shell clearance)
- 2× M2 screws secure button PCB to standoff

**Button Tower**:
- 20mm × 20mm × 10mm tall printed post
- Centered in bottom shell
- Hollow interior for wiring
- Top surface: flat landing pad for button PCB

**Top Shell Interface**:
- 12mm diameter through-hole (not flex area!)
- Printed glyph cap (separate piece):
  - 15mm outer diameter
  - 2mm thick
  - Forerunner symbol on top (0.3mm relief)
  - 3mm pin underneath aligns with button stem
  - Light friction fit or dab of glue to button

**Travel & Feel**:
- 0.5mm tactile travel
- Cap should sit 0.5mm above surface when unpressed
- Ensures reliable "click" feel

---

### C. ESP32 DevKitC-32 Mount

**Board Dimensions**: 56mm × 28mm × 15mm (with headers)
**Orientation**: USB-C port facing side wall cutout

**Mounting**:
- 4× M2 × 0.4 standoffs (6mm tall)
- Positions aligned with ESP32 mounting holes
- Standoffs secured to bottom shell with heat-set inserts or printed threads

**Clearances**:
- 3mm clearance above ESP32 to battery tray bottom
- 2mm clearance to all side walls
- Wire routing channels on all 4 sides (4mm wide)

**Thermal Management** 🌡️ NEW:
- Optional: 50mm × 28mm × 0.5mm aluminum heat spreader
- Adhered to bottom of ESP32 with thermal tape
- Helps dissipate WiFi heat during multiplayer mode
- Cost: ~$0.50

---

### D. MPU6050 Accelerometer (GY-521)

**Board Dimensions**: 20mm × 15mm × 2mm
**Position**: Offset 25mm from center (near edge)

**Mounting**:
- 2× M2 × 0.4 standoffs (5mm tall)
- Direct screw into bottom shell (printed threads OK)
- Orientation: Axes aligned with puck X/Y plane

**Clearances**:
- Must not interfere with battery
- Wire channel to ESP32: 4mm wide

---

### E. Battery Tray & Retention

**Battery Dimensions**: 60mm × 35mm × 8mm (2000mAh LiPo)
**Position**: Lies flat above ESP32, below top shell

**Tray Design** 🔋 IMPROVED:
- Recessed pocket: 62mm × 37mm × 9mm
- **Velcro retention system**:
  - 5mm × 50mm flat surface on tray bottom
  - Matching area on battery
  - Use 3M dual-lock or thin adhesive velcro
- Battery cable routing channel: 4mm wide × 2mm tall
- Routes to TP4057 charger on side wall

**Structural Support**:
- Tray floor: 2mm thick (printed solid)
- Prevents battery from pressing on ESP32
- Ventilation slots under tray (4× 3mm × 15mm)

**Safety**:
- Battery must not touch metal standoffs
- Kapton tape or silicone pad recommended under battery

---

### F. USB-C Charging Port (TP4057)

**Component**: TP4057 Li-Ion charger module (26mm × 17mm)
**Position**: Side wall, 10mm from base

**Wall Cutout Dimensions** 🔌 PRECISE:
- Width: **10.0 mm** (increased from 9mm)
- Height: **5.0 mm** (increased from 4.5mm)
- Center height above base: 8 mm
- Fillet inside corners: 0.5mm radius (easier printing)

**Charger Mounting**:
- 2× M2 standoffs OR
- Hot glue to wall interior (serviceable)
- Ensure USB-C port is flush with exterior wall

**Cable Management**:
- Input from battery: 4mm channel
- Output to ESP32: 4mm channel
- Zip-tie anchor near charger

**Water Protection** 💧 OPTIONAL:
- Print separate rubber plug (TPU 95A)
- Friction-fits into cutout when not charging
- Or use waterproof USB-C charging module

---

### G. Vibration Motor Mount

**Component**: 10mm cylindrical coin motor (10mm dia × 2.5mm)
**Position**: Offset 30mm from center (near edge, opposite MPU)

**Mounting** 🔊 REDESIGNED:
- TPU "motor sock" (print separately in TPU 95A):
  - 12mm outer diameter × 8mm tall cylinder
  - 10.2mm inner diameter (tight friction fit on motor)
  - 0.8mm wall thickness
- Sock friction-fits into printed pocket in bottom shell:
  - Pocket: 12.5mm diameter × 8mm deep
  - Prevents motor rattle
  - Dampens vibration noise

**Wiring**:
- 4mm channel to ESP32
- Motor wires: 30 AWG silicone (flexible!)

**Alternative** (if no TPU):
- Hot glue or silicone RTV adhesive
- Less ideal but serviceable

---

### H. Piezo Buzzer Mount

**Component**: 12mm or 22mm piezo buzzer
**Position**: Near side wall, 20mm from center

**Mounting**:
- Circular recess: 23mm diameter × 4mm deep
- Buzzer sits flush or slightly recessed
- Hot glue or double-sided tape to secure

**Sound Vents** 🔊 NEW:
- 6× decorative Forerunner glyph vents above buzzer
- Each vent: 2mm × 8mm slots
- Arranged in circular pattern
- Also serve as heat exhaust for ESP32

**Sound Quality**:
- Avoid covering buzzer completely (muffles sound)
- Vents should expose 30-40% of buzzer surface area

---

### I. Wire Routing System

**Wire Gauge**: 30 AWG silicone wire (flexible, high temp)

**Channel Specifications** 🔧 IMPROVED:
- Width: **4.0 mm** (increased from 3mm)
- Depth: **3.0 mm** (increased from 2mm)
- Channels connect all components in "star" pattern from ESP32

**Cable Management**:
- 6× zip-tie anchor posts (2mm diameter × 4mm tall)
- Positioned at key routing points:
  - Near LED ring
  - Near ESP32 (2 posts)
  - Near battery
  - Near motor
  - Near buzzer

**Channel Routes**:
1. ESP32 → LED ring (top path)
2. ESP32 → Button (center path)
3. ESP32 → Motor (side path)
4. ESP32 → Buzzer (side path)
5. ESP32 → MPU6050 (I2C lines)
6. Battery → TP4057 → ESP32 (power path)

**Wire Strain Relief**:
- All channels have rounded entries (1mm radius)
- No sharp edges that could cut wire insulation

---

## 3. PRINTING SPECIFICATIONS

### Material Selection

**Top Shell**:
- **Recommended**: Translucent PETG (natural or blue-tinted)
- **Alternative**: Translucent white PLA
- **Why PETG**: Better impact resistance, less brittle than PLA

**Bottom Shell**:
- **Recommended**: Standard PETG (any color)
- **Alternative**: PLA (if low drop risk environment)

**TPU Parts** (print separately):
- Shore hardness: TPU 95A
- Parts: Equator bumper ring, motor sock, optional button cap

### Print Settings - Top Shell (Translucent)

```ini
Material: PETG Translucent
Nozzle temp: 235°C
Bed temp: 80°C
Layer height: 0.2mm
Infill: 0% (SOLID SHELL for even light diffusion)
Perimeters: 5
Top/bottom layers: 6
Print speed: 35mm/s (slow for quality)
Cooling: 30% fan after first layer
Supports: None needed (dome printed face-up)
```

**Post-Processing**:
- Sand interior with 220 → 400 → 600 grit (frosted diffusion)
- Optionally: vapor smooth if using ABS
- DO NOT sand exterior (ruins Forerunner details)

### Print Settings - Bottom Shell (Structural)

```ini
Material: PETG
Nozzle temp: 240°C
Bed temp: 80°C
Layer height: 0.2mm
Infill: 30% gyroid pattern
Perimeters: 5
Top/bottom layers: 6
Print speed: 45mm/s
Cooling: 50% fan
Supports: Only for screw boss overhangs (tree supports)
```

**Post-Processing**:
- Install brass heat-set inserts while print is warm (200°C iron)
- Test-fit all components before final assembly
- Deburr screw holes with 3.5mm drill bit

### Print Settings - TPU Parts

```ini
Material: TPU 95A
Nozzle temp: 220°C
Bed temp: 60°C
Layer height: 0.2mm
Infill: 100%
Perimeters: 3
Print speed: 20mm/s (SLOW for TPU)
Retraction: 2mm @ 25mm/s
```

### Print Orientation

**Top Shell**:
- Dome facing UP
- No supports needed
- Brim: 5mm (helps adhesion)

**Bottom Shell**:
- Open side facing UP
- Minimal supports for screw boss overhangs
- Use tree supports (easier removal)

**Small Parts**:
- Button cap: face up
- Motor sock: standing vertically
- Bumper ring: laying flat

### Estimated Print Times & Material

```
Top Shell: 7-9 hours
Bottom Shell: 6-8 hours
TPU Parts: 1-2 hours
Total per puck: 14-19 hours

Material Usage:
Top Shell: ~45g PETG
Bottom Shell: ~60g PETG
TPU Parts: ~8g TPU
Total: ~113g per complete enclosure
```

---

## 4. ASSEMBLY INSTRUCTIONS (Quick Reference)

### Tools Required
- M3 hex key (2.5mm)
- M2 hex key (1.5mm)
- Soldering iron (for heat-set inserts)
- Small Phillips screwdriver
- Wire cutters & strippers
- Hot glue gun
- Multimeter

### Assembly Order

1. **Install brass inserts** in bottom shell (6× M3)
2. **Mount ESP32** on 4× standoffs
3. **Mount MPU6050** on 2× standoffs
4. **Install button** on center tower
5. **Glue motor** into TPU sock, insert into pocket
6. **Mount buzzer** with hot glue
7. **Install TP4057** charger near wall cutout
8. **Route all wiring** through channels, zip-tie secure
9. **Mount LED ring** in top shell on 4× standoffs
10. **Connect LED wiring** through center opening
11. **Attach battery** with velcro to tray
12. **Test all functions** before closing!
13. **Install O-ring** in groove
14. **Apply TPU bumper ring** around equator
15. **Align shells**, insert 6× M3 screws
16. **Attach button glyph cap** to button top

### First Power-On Checklist

- [ ] All LEDs light up (test with firmware)
- [ ] Button registers presses (check Serial Monitor)
- [ ] Motor vibrates on command
- [ ] Buzzer sounds clearly
- [ ] MPU6050 detects motion
- [ ] No rattling when shaken
- [ ] No light leaks at seam
- [ ] USB-C charging works
- [ ] Shells feel secure (no flexing)

---

## 5. DURABILITY TESTING PROTOCOL

Before deploying to a bar, test each puck:

### Drop Test
- Drop from 1 meter onto concrete (3× different angles)
- Check for cracks, loose components, LED function
- Should survive with no damage

### Shake Test
- Vigorous shaking for 30 seconds
- No rattling sounds
- All components secure

### Splash Test
- Spray with water mist for 10 seconds
- Dry exterior, check for moisture inside
- Should pass IP54 (splash resistant)

### Thermal Test
- Run WiFi sync + full LED brightness for 20 minutes
- ESP32 should stay under 70°C
- No warping of shell

### Button Longevity
- 1000 button presses in rapid succession
- Button should still click reliably
- No cracking around button hole

---

## 6. COST BREAKDOWN

```
Materials per enclosure:
┌─────────────────────────────────────┬─────────┐
│ PETG filament (105g @ $0.02/g)      │  $2.10  │
│ TPU filament (8g @ $0.04/g)         │  $0.32  │
│ 6× M3 brass inserts                 │  $0.90  │
│ 6× M3 × 10mm screws (stainless)     │  $0.60  │
│ 4× M2 standoffs (brass, 6mm)        │  $0.80  │
│ 90mm O-ring (Buna-N)                │  $0.60  │
│ Velcro strip (50mm)                 │  $0.30  │
│ Optional: aluminum heat spreader    │  $0.50  │
│ Optional: acrylic diffuser disc     │  $0.80  │
│ Optional: metallic spray paint      │  $2.00  │
├─────────────────────────────────────┼─────────┤
│ TOTAL (basic):                      │  $5.62  │
│ TOTAL (with all options):           │  $8.92  │
└─────────────────────────────────────┴─────────┘

Labor:
Print time: 14-19 hours
Assembly time: 45-60 minutes per puck
```

---

## 7. AESTHETIC CUSTOMIZATION OPTIONS

### Color Schemes

**Classic Forerunner**:
- Top: Translucent blue PETG
- Bottom: Gunmetal gray PETG
- Bumper: Black TPU
- Post-process: Aluminum metallic spray on bottom

**Energy Core**:
- Top: Translucent natural PETG
- Bottom: White PETG
- Bumper: Translucent blue TPU
- LED colors: Blue/cyan theme

**Stealth**:
- Top: Translucent smoke gray PETG
- Bottom: Matte black PETG
- Bumper: Black TPU
- LED colors: Red theme

### Surface Treatments

1. **Metallic finish**: Aluminum or copper spray paint on bottom shell
2. **Battle damage**: Light sanding/scratching for "ancient artifact" look
3. **Glow effect**: Add glow-in-the-dark PLA accents
4. **Anodized look**: Use metallic markers on raised details
5. **Clear coat**: 2-3 coats of matte or gloss clear (UV protection)

### LED Underglow (Optional)

Add Forerunner blue ambient lighting:
- 3× blue LEDs on bottom shell exterior
- Point downward at 45° angle
- Wired to ESP32 (separate channel from main ring)
- Creates dramatic table glow effect
- Cost: ~$0.50 in parts

---

## 8. CAD FILE DELIVERABLES

When complete, provide:

### Required Files
- [ ] `forerunner_top_v2.stl` - Top shell (95mm, 3mm walls)
- [ ] `forerunner_bottom_v2.stl` - Bottom shell (95mm, 3.5mm walls)
- [ ] `button_glyph_cap.stl` - Center button cap
- [ ] `motor_sock_tpu.stl` - Vibration motor mount (TPU)
- [ ] `bumper_ring_tpu.stl` - Equator bumper (TPU)

### Optional Files
- [ ] `diffuser_disc.dxf` - Acrylic cutting pattern
- [ ] `usb_plug_tpu.stl` - Waterproof port cover (TPU)
- [ ] `assembly_jig.stl` - Alignment tool for assembly

### Documentation
- [ ] Assembly diagram (exploded view)
- [ ] Wiring schematic overlay
- [ ] Print settings reference card

### Source Files
- [ ] `.f3d` or `.step` file (for modifications)
- [ ] Component library (all standoffs, inserts, etc.)

---

## 9. DESIGN ITERATION STRATEGY

**DO NOT skip prototyping!** Follow this path:

### Phase 1: Simple Box Test (2-3 days)
✅ Print basic rectangular enclosure
✅ Verify all components fit
✅ Test wire routing
✅ Confirm button mechanism works
✅ Drop test prototype

### Phase 2: Cylinder Prototype (1 week)
✅ Print basic 95mm cylinder (no Forerunner details)
✅ Add all mounts, standoffs, screw bosses
✅ Test thermal performance (WiFi on for 30 min)
✅ Test assembly/disassembly 5× times
✅ Get feedback from test users on feel/weight

### Phase 3: Detailed Forerunner Design (1-2 weeks)
✅ Add all aesthetic details (glyphs, rings, vents)
✅ Fine-tune tolerances based on Phase 2
✅ Print 2-3 test versions
✅ Polish print settings for best quality
✅ Finalize color scheme

### Phase 4: Production (ongoing)
✅ Print full set of 6 pucks
✅ Document any issues during assembly
✅ Create assembly manual for future builds

**Budget**: Expect 5-8 test prints before final design ($20-40 in filament)

---

## 10. TROUBLESHOOTING GUIDE

### Print Issues

**Top shell warping**:
- Increase bed temp to 85°C
- Add 10mm brim
- Enclose printer (reduce drafts)

**Layer separation on walls**:
- Increase nozzle temp by 5°C
- Slow down print speed to 35mm/s
- Check for partial nozzle clog

**Supports stuck in screw holes**:
- Use tree supports (easier removal)
- Increase support gap to 0.3mm
- Apply support blocker in holes

**Translucent shell shows layer lines**:
- Print slower (30mm/s)
- Increase flow rate by 3-5%
- Sand interior 220 → 400 → 600 grit

### Assembly Issues

**Brass inserts won't stay put**:
- Heat iron to 210°C (hotter)
- Press straight down (don't angle)
- Let cool completely before removing iron

**Button feels mushy**:
- Check button cap pin alignment
- Reduce cap thickness to 1.5mm
- Ensure button stem has 0.5mm travel

**Motor rattles**:
- TPU sock too loose - print at 99% scale
- Add small dab of hot glue on motor body

**LED hot spots visible**:
- Sand interior of top shell more thoroughly
- Add acrylic diffuser disc
- Reduce LED brightness to 60-80

**Light leaks at seam**:
- Check O-ring is seated properly
- Increase screw tension slightly
- Add thin black tape inside seam (temp fix)

**USB-C doesn't fit**:
- File/sand cutout slightly larger
- Check TP4057 board is flush mounted
- Verify print dimensional accuracy (recalibrate)

---

## 11. SAFETY WARNINGS ⚠️

**Fire Risk**:
- Never exceed LED brightness beyond power supply limits
- Monitor ESP32 temperature during extended WiFi use
- Use thermal fuse on battery if possible

**Battery Safety**:
- Use quality LiPo batteries with protection circuit
- Never puncture or crush battery
- Keep battery away from metal standoffs (insulate!)
- Don't charge unattended

**Drop Risk**:
- Test enclosure durability before public deployment
- Consider insurance for bar deployment
- Warn users not to throw (it's a game puck, not a ball!)

**Chemical Safety**:
- Work in ventilated area when using spray paint
- Wear gloves when handling solvents
- Let finishes cure 48 hours before electronics assembly

---

## 12. QUICK START FOR CAD DESIGNER

**Start with your existing STLs** (`forerunner_top.stl`, `forerunner_bottom.stl`) and add:

### Top Shell Modifications:
1. Thicken walls to 3.0mm
2. Increase diameter to 95mm
3. Add 12mm button hole in center (remove flex area)
4. Add 4× LED ring screw boss positions
5. Add internal frosted texture (optional)
6. Add zip-tie anchor post near LED ring

### Bottom Shell Modifications:
1. Thicken walls to 3.5mm
2. Increase diameter to 95mm
3. Add 6× M3 screw boss positions with brass insert pockets
4. Add 2mm × 2mm O-ring groove on rim
5. Add center button tower (20×20×10mm)
6. Add ESP32 standoff positions (4× M2)
7. Add MPU6050 standoff positions (2× M2)
8. Add battery tray with velcro surface
9. Add TP4057 cutout (10×5mm) on side wall
10. Add motor pocket (12.5mm diameter)
11. Add buzzer recess (23mm diameter)
12. Add 4× thermal vent glyphs
13. Add 6× sound vent glyphs above buzzer
14. Add 4× TPU bumper recesses on base
15. Add 2mm × 2mm bumper groove around equator
16. Add wire routing channels (4mm wide × 3mm tall)
17. Add 6× zip-tie anchor posts

### New Parts to Model:
1. Button glyph cap (15mm dia, 2mm thick, Forerunner symbol)
2. TPU motor sock (12mm OD × 10.2mm ID × 8mm tall)
3. TPU equator bumper ring (95mm ID, 2mm × 2mm cross-section)
4. Optional: USB-C plug cover (TPU)

### Assembly File:
- Import all components (ESP32 STEP, LED ring, battery, etc.)
- Use interference detection to verify clearances
- Create exploded view for documentation

---

## 13. REFERENCE DIMENSIONS SUMMARY

| Component | Dimensions (mm) | Mount Height (mm) |
|-----------|----------------|-------------------|
| Enclosure OD | 95 diameter | 40 total height |
| Top shell wall | 3.0 thick | 8 dome height |
| Bottom shell wall | 3.5 thick | 32 internal height |
| LED ring | 50 ID, 60 OD | 12 from top shell |
| ESP32 board | 56 × 28 × 15 | 6 from base |
| Battery | 60 × 35 × 8 | Above ESP32 |
| MPU6050 | 20 × 15 × 2 | 5 from base |
| Button tower | 20 × 20 × 10 | Centered |
| Motor pocket | 12.5 diameter | 4 deep |
| Buzzer recess | 23 diameter | 4 deep |
| USB-C cutout | 10 × 5 | 8 center height |
| Screw bosses | 6× M3 | Full height |
| O-ring groove | 2 × 2 | Top rim |
| Bumper groove | 2 × 2 | Equator |

---

## VERSION HISTORY

**v2.0** (2025-01-18) - Major revision:
- Increased diameter to 95mm
- Thickened walls for durability
- Redesigned button mechanism (direct tactile)
- Added O-ring seal for splash resistance
- Added TPU bumper ring for drop protection
- Added thermal ventilation system
- Improved wire management with zip-tie anchors
- Added battery velcro retention
- Upgraded to M3 screws with brass inserts
- Added detailed print settings and assembly guide

**v1.0** (Original spec):
- 90mm diameter
- Basic component layout
- Flex membrane button (problematic)
- No sealing or thermal management

---

**Ready to build? This spec is 100% manufacturable and bar-ready! 🎮✨**
