# TABLE WARS - Manufacturing Specifications

## Parts List

### PETG Parts (Translucent Blue + Black)
1. **top_shell_petg.stl** - Translucent Blue PETG (Qty: 1)
2. **bottom_shell_petg.stl** - Black PETG (Qty: 1)
3. **button_cap_petg.stl** - Translucent Blue PETG (Qty: 1)

### TPU Parts (Black, Flexible)
4. **bumper_ring_tpu.stl** - Black TPU, Shore 95A (Qty: 1)
5. **motor_sock_tpu.stl** - Black TPU, Shore 95A (Qty: 1)

**Total: 5 parts per puck**

## Materials & Colors

### PETG Filament
- **Top Shell**: Translucent Blue PETG (light passes through for LED glow)
- **Bottom Shell**: Black PETG (solid, opaque)
- **Button Cap**: Translucent Blue PETG (matches top shell)

### TPU Filament
- **Bumper Ring**: Black TPU, Shore 95A (flexible, impact absorption)
- **Motor Sock**: Black TPU, Shore 95A (vibration dampening)

## Key Dimensions

- **Overall Diameter**: 95mm
- **Total Height**: ~50mm assembled
- **Wall Thickness**: 3mm (top and bottom shells)
- **Dome Wall**: 3mm (lets LED light through)
- **Button Protrusion**: 18mm above dome surface
- **PCB Diameter**: 89mm (custom circular PCB)

## Recommended Print Settings

### PETG Parts
- **Layer Height**: 0.2mm (or 0.15mm for finer detail)
- **Infill**: 20-30% (gyroid or honeycomb)
- **Walls**: 3-4 perimeters
- **Top/Bottom Layers**: 5-6 layers
- **Supports**: YES - Required for dome overhang and button hole
- **Support Type**: Tree supports or organic supports (easier removal)
- **Print Orientation**:
  - Top shell: Upside down (rim on build plate)
  - Bottom shell: Right-side up (base on build plate)
  - Button cap: Upside down (top surface on build plate)

### TPU Parts
- **Layer Height**: 0.2mm
- **Infill**: 100% (flexible parts need solid fill)
- **Walls**: 3 perimeters
- **Print Speed**: 25-35 mm/s (slow for TPU)
- **Retraction**: Minimal (1-2mm to prevent jams)
- **Supports**: Not needed

## Assembly Notes

### Screw Attachment
- 6x M2.5 screws (8-10mm length recommended)
- Screws at 60° intervals, 40mm radius from center
- Bottom shell has standoff posts with M2.5 threads
- Top shell has countersunk screw recesses (hexagonal)

### Custom PCB Integration
- 89mm diameter circular PCB
- MPU6050 sensor CENTERED (critical for precision tilt detection)
- PCB mounts to 6 standoffs in bottom shell (38mm radius)
- Center support post for MPU6050 chip
- 15mm center hole in PCB for button access

### LED Ring
- 16x WS2812B LEDs in ring formation
- 58mm diameter LED circle (29mm radius from center)
- LEDs mounted to PCB (not printed parts)
- Light shines UP through translucent blue dome
- No opening needed in dome - light passes through translucent PETG

### Button Assembly
- Tactile switch on PCB (center)
- Button stem extends through PCB and top shell
- Button cap sits 18mm ABOVE dome surface
- Button cap has Forerunner glyph engraved 1.5mm deep

### Bumper Ring
- Black TPU ring sits at seam between top/bottom shells
- Provides impact protection and grip
- Installed at z=24mm height

## Forerunner Aesthetic Details

### Top Shell Features
- 3x raised energy rings (concentric circles, 2mm height)
- 16x radial light diffusion channels
- 6x decorative hexagons at screw positions
- Smooth dome curve for premium look

### Bottom Shell Features
- 6x large hexagons around perimeter (8mm diameter)
- Hexagonal caps on all standoff posts
- Recessed base (2.5mm) for stability

### Button Cap
- Forerunner symbol deeply engraved (1.5mm depth)
- Complex geometric pattern (hexagon + triangles + segmented ring)
- 15mm outer diameter, 2mm thickness

## Special Notes

1. **Translucent vs Transparent PETG**: Must be translucent (not fully transparent/clear) for proper LED diffusion and to hide internal components
2. **Wall Thickness**: 3mm is critical - DO NOT scale parts or change wall thickness
3. **Button Position**: Button cap MUST protrude 18mm above dome surface (critical for gameplay)
4. **PCB Integration**: Design optimized for custom 89mm circular PCB with centered MPU6050 sensor
5. **Support Removal**: Use care removing supports from dome interior, energy rings, and hexagonal details
6. **Post-Processing**: Light sanding recommended on shell seam surfaces for smooth assembly fit
7. **No LED Openings**: Dome is solid - LED light passes through translucent material (do not drill holes)

## Hardware Not Included

The following hardware is NOT part of this 3D printing package:
- 6x M2.5 screws (8-10mm length)
- Custom 89mm circular PCB with components
- 16x WS2812B addressable RGB LEDs
- Electronic components (ESP32, MPU6050, etc.)

This package provides only the 3D printed enclosure parts.

## Questions?

Contact for any clarification on dimensions, materials, or assembly instructions.
