# Quote Request for Sid - Ready to Send

## Message Template for Freelancer.com

---

**Subject:** Milestone 1 Approved - Quote Request for Custom PCB Gaming Puck

---

Hi Sid,

I've reviewed your Milestone 1 technical document and approved it. Excellent work on the architecture and component selection.

## PROJECT SCOPE

**Custom PCB Gaming Puck - 10 Units**

I need a complete quote for professional manufacturing of gaming pucks with custom circular PCB assembly.

---

## PCB SPECIFICATIONS

Based on your technical document, with these additional requirements:

**PCB Design:**
- Circular PCB: 89mm diameter (I have enclosure CAD designed to this spec)
- All components per your Milestone 1 doc:
  - ESP32-WROOM-32 module (or bare ESP32 chip if you prefer)
  - MPU6050 accelerometer/gyro **CENTERED** at exact center (0,0) for symmetric motion sensing
  - TP4057 USB-C charging circuit
  - MT3608 boost converter (5V for LEDs)
  - WS2812B LED ring connector pads (16 LEDs, external ring)
  - Vibration motor driver circuit
  - Piezo buzzer circuit
  - Tactile button (center)
  - All protection circuits, decoupling caps, pullup resistors per your spec

**Load-Sharing Approach:**
- Recommend Option B or C from your document
- Let me know which you suggest based on cost/reliability tradeoff

**PCB Mounting:**
- 6× M2.5 mounting holes at 38mm radius (60° spacing)
- Center area clear for through-hole button + MPU6050 on top
- USB-C port accessible from side edge

**Critical Requirement:**
- MPU6050 MUST be centered at (0, 0) for symmetric tilt detection
- This is essential for gameplay - precision tilt angles in all directions

---

## DELIVERABLES NEEDED

### **Option A: Full Turnkey (Preferred)**
1. Custom PCB design (schematic + layout)
2. PCB fabrication (10 boards)
3. Component sourcing + assembly (10 units)
4. 3D printed enclosures (10 sets, 5 parts each - specs below)
5. Full assembly (electronics installed in enclosures)
6. Testing + programming
7. 30-day warranty on workmanship

### **Option B: Electronics Only**
1. Custom PCB design (schematic + layout)
2. PCB fabrication (10 boards)
3. Component sourcing + assembly (10 units)
4. Testing + programming
5. 30-day warranty on electronics
6. (I handle 3D printing + final assembly separately)

---

## 3D PRINTED ENCLOSURE SPECIFICATIONS

**I have production-ready STL files attached.**

### Parts per unit (5 pieces):
1. **Bottom shell** (forerunner_bottom_shell_v3_pcb.stl)
   - Material: PETG
   - Color: Black or dark gray
   - Infill: 20%
   - Layer height: 0.2mm
   - Supports: Yes (for internal features)

2. **Top shell** (forerunner_top_shell_v2.stl)
   - Material: PETG (translucent preferred for LED visibility)
   - Color: Translucent blue or clear
   - Infill: 20%
   - Layer height: 0.2mm
   - Supports: Minimal

3. **Button cap** (button_glyph_cap_v2.stl)
   - Material: PETG (translucent preferred)
   - Color: Translucent blue or clear
   - Infill: 100%
   - Layer height: 0.1mm (for glyph detail)
   - Supports: No

4. **Bumper ring** (bumper_ring_tpu.stl)
   - Material: TPU 95A (flexible)
   - Color: Black
   - Infill: 100%
   - Layer height: 0.2mm
   - Supports: No

5. **Motor sock** (motor_sock_tpu.stl)
   - Material: TPU 95A (flexible)
   - Color: Black
   - Infill: 100%
   - Layer height: 0.2mm
   - Supports: No

**Additional Hardware (if you're doing full assembly):**
- 60× M3 brass heat-set inserts (M3×4mm OD×5mm length)
- 60× M3×10mm screws (stainless steel)
- 10× O-rings (90mm ID × 2mm thickness, Buna-N rubber)
- Velcro strips for battery mounting

---

## QUOTE REQUEST

Please provide detailed breakdown:

### **PCB Design (One-time cost):**
- Schematic design: $___
- PCB layout: $___
- Design review + revisions: $___
- **Subtotal PCB Design:** $___

### **Per Unit Cost (for 10 units):**
- PCB fabrication (per board): $___
- Components (BOM per unit): $___
- PCB assembly labor (per unit): $___
- Testing + programming (per unit): $___
- **Subtotal Electronics (per unit):** $___

### **3D Printing (if Option A):**
- Printing per unit (5 parts): $___
- Hardware kit per unit: $___
- Final assembly per unit: $___
- **Subtotal Enclosures (per unit):** $___

### **TOTAL QUOTES:**
- **Option A (Full Turnkey):** $_____ (design + 10 complete units)
- **Option B (Electronics Only):** $_____ (design + 10 assembled PCBs)

### **Timeline Estimate:**
- PCB design completion: ___ weeks
- PCB fab + assembly: ___ weeks
- Enclosures (if Option A): ___ weeks
- **Total timeline:** ___ weeks from approval

---

## PAYMENT MILESTONES

Suggested breakdown (negotiable):

**Milestone 2:** PCB Design
- Deliverable: Schematic + PCB layout files
- Review + revision round
- Payment: $___

**Milestone 3:** Prototype Build
- Deliverable: 2× assembled PCBs (or 2× complete units if Option A)
- Functional testing
- Payment: $___

**Milestone 4:** Production Run
- Deliverable: Remaining 8 units
- Full QA testing
- Payment: $___

---

## ATTACHED FILES

1. **Your Milestone 1 Document:** ESP32 Gaming Puck Technical V1.0.docx (approved)
2. **My Enclosure STL Files (5 files):**
   - forerunner_bottom_shell_v3_pcb.stl
   - forerunner_top_shell_v2.stl
   - button_glyph_cap_v2.stl
   - bumper_ring_tpu.stl
   - motor_sock_tpu.stl

---

## NOTES

- Timeline is flexible - prioritize quality over speed
- MPU6050 centering is critical (affects 37 games I'm developing)
- I prefer Option A (full turnkey) if you have reliable 3D printing
- 30-day warranty on workmanship is required
- Open to your suggestions on load-sharing circuit and any component substitutions

Looking forward to your detailed quote!

Thanks,
Austin

---

## CHECKLIST BEFORE SENDING:

- [ ] Attach Sid's Milestone 1 doc
- [ ] Attach all 5 STL files
- [ ] Verify you want Option A or B (or ask for both quotes)
- [ ] Review quote request format
- [ ] Send via Freelancer.com messaging

