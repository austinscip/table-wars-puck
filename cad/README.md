# TABLE WARS - Gaming Puck CAD Files

Generated OpenSCAD files for 3D printing the Forerunner-style gaming puck enclosure.

## Files Created

### Main Enclosure
- `forerunner_bottom_shell.scad` → Bottom shell with all component mounts
- `forerunner_top_shell.scad` → Top translucent dome with LED ring mounts

### Small Parts
- `button_glyph_cap.scad` → Center button cap (PETG)
- `motor_sock_tpu.scad` → Vibration motor holder (TPU 95A)
- `bumper_ring_tpu.scad` → Equator bumper ring (TPU 95A)

## How to Use

### 1. Open in OpenSCAD
```bash
# Open the application
open -a OpenSCAD

# Or from command line:
open -a OpenSCAD forerunner_bottom_shell.scad
```

### 2. Render and Export STL

**In OpenSCAD:**
1. Click **Design** → **Render** (or press F6)
   - This will take 30-60 seconds for complex parts
   - Wait for "Rendering finished" in console
2. Click **File** → **Export** → **Export as STL**
3. Save as: `forerunner_bottom_shell.stl`

**Repeat for each .scad file.**

### 3. Print Settings

#### Bottom Shell (PETG)
```
Material: PETG
Nozzle: 240°C
Bed: 80°C
Layer height: 0.2mm
Infill: 30% gyroid
Perimeters: 5
Print time: ~6-8 hours
```

#### Top Shell (Translucent PETG)
```
Material: Translucent PETG
Nozzle: 235°C
Bed: 80°C
Layer height: 0.2mm
Infill: 0% (SOLID SHELL for light diffusion)
Perimeters: 5
Speed: 35mm/s (slow for quality)
Print time: ~7-9 hours
```

#### TPU Parts (Motor Sock & Bumper)
```
Material: TPU 95A
Nozzle: 220°C
Bed: 60°C
Layer height: 0.2mm
Infill: 100%
Speed: 20mm/s (SLOW)
Print time: ~1-2 hours each
```

#### Button Cap (PETG)
```
Same as top shell
Print time: ~15 minutes
```

## Command-Line Export (Advanced)

If you want to batch-export all STL files:

```bash
cd ~/table-wars-puck/cad

# Bottom shell
openscad -o forerunner_bottom_shell.stl forerunner_bottom_shell.scad

# Top shell
openscad -o forerunner_top_shell.stl forerunner_top_shell.scad

# Button cap
openscad -o button_glyph_cap.stl button_glyph_cap.scad

# Motor sock
openscad -o motor_sock_tpu.stl motor_sock_tpu.scad

# Bumper ring
openscad -o bumper_ring_tpu.stl bumper_ring_tpu.scad
```

## Customization

All dimensions are parametric - you can edit values at the top of each .scad file:

**Example - Change puck diameter:**
```openscad
/* [Main Dimensions] */
outer_diameter = 100;  // Changed from 95mm to 100mm
```

Save and re-render to see changes instantly.

## Troubleshooting

### "Parse Error" in OpenSCAD
- Check syntax in .scad file
- Ensure all brackets {} are balanced

### Rendering Takes Forever
- Lower $fn value (e.g., $fn = 50 instead of 100)
- Reduce complexity temporarily

### STL has gaps/holes
- Increase $fn for smoother curves
- Check for "manifold" errors in OpenSCAD console

### Part doesn't fit in slicer
- Check that build volume is at least 100mm × 100mm × 50mm
- Parts are designed for standard FDM printers

## What to Do Next

1. **Export all STL files** using OpenSCAD
2. **Import STLs into your slicer** (Cura, PrusaSlicer, etc.)
3. **Slice and print** bottom shell first (test fit)
4. **Print top shell** (test fit with bottom)
5. **Print small parts** (button cap, motor sock, bumper)
6. **Assemble** following ENCLOSURE_SPEC.md instructions

## Estimated Costs

```
Bottom shell: ~60g PETG = $1.20
Top shell: ~45g PETG = $0.90
Button cap: ~2g PETG = $0.04
Motor sock: ~4g TPU = $0.16
Bumper ring: ~4g TPU = $0.16
--------------------------------
TOTAL per puck: ~$2.46 in filament
```

Plus hardware:
- 6× M3 brass inserts: $0.90
- 6× M3 screws: $0.60
- 90mm O-ring: $0.60

**Grand total: ~$4.56 per enclosure**

## Need Help?

- **OpenSCAD Docs**: https://openscad.org/documentation.html
- **3D Printing Guide**: See `ENCLOSURE_SPEC.md` for full details
- **Assembly Instructions**: See `ENCLOSURE_SPEC.md` Section 4

---

**Ready to print!** 🎮✨
