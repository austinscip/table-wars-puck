# Message to Send to Freelancer

Copy and paste this message to your freelancer:

---

**Subject: Table Wars PCB - Need Manufacturing Files**

Hi [Freelancer Name],

Thanks for the Altium project files! The PCB design looks really professional - I'm impressed with the circular layout and component selection.

However, I don't have Altium Designer to open the source files, and I'm ready to move forward with manufacturing. Could you please export the following manufacturing files from the project?

## Required Files:

### 1. **Gerber Files (Complete Set)**
- Top layer (.GTL)
- Bottom layer (.GBL)
- Top soldermask (.GTS)
- Bottom soldermask (.GBS)
- Top silkscreen (.GTO)
- Bottom silkscreen (.GBO)
- Board outline (.GKO or .GM1)
- Drill file (.TXT or .DRL)
- NC Drill file

**Format:** Zip file containing all Gerbers (RS-274X format preferred)

### 2. **Bill of Materials (BOM)**
- Export as Excel (.xlsx) or CSV (.csv)
- Must include:
  - Reference designators (U1, R1, C1, etc.)
  - Part numbers (manufacturer part numbers)
  - Descriptions
  - Values (for resistors/caps)
  - Quantities
  - Package/footprint
  - Supplier part numbers (Digikey, Mouser, or LCSC preferred)

### 3. **Assembly Files**
- Pick-and-place file (.csv or .txt) with XY coordinates
- Component placement drawing (PDF)
- Assembly drawing showing top and bottom views

### 4. **Documentation**
- Schematic as PDF (all pages)
- PCB layout as PDF (all layers)
- Design notes or special assembly instructions (if any)

## Questions About the Design:

I noticed a few things I wanted to confirm before manufacturing:

1. **MPU6050 Motion Sensor** - I see it's included as U4. Perfect! Can you confirm the I2C pins it's connected to on the ESP32?

2. **Physical Button (SW1)** - Confirmed it's there. Which GPIO pin is it connected to?

3. **LED Ring** - How many WS2812B LEDs total? My firmware expects 16. Are they:
   - All on the main PCB?
   - On a separate ring PCB that connects via cable?
   - What's the data pin connection to ESP32?

4. **Vibration Motor** - Is there a connector for a vibration motor? If so, which transistor/pin controls it?

5. **Battery** - What type of connector is used for the LiPo battery? (JST-PH 2.0mm? JST-XH 2.54mm?)

6. **Passive Components** - Are all resistors and capacitors rated correctly for:
   - R1-R13: Wattage rating? (1/4W sufficient?)
   - C1, C2, C4: Voltage rating? (6.3V, 16V, 25V?)

## Timeline:

I'd like to get quotes from PCB manufacturers this week, so if you could provide these files within the next few days, that would be great!

## What I'll Do Next:

Once I have these files, I'll:
1. Upload Gerbers to JLCPCB/PCBWay for quote
2. Review BOM and source components
3. Order 5-10 prototype boards for testing
4. Report back on the manufacturing quality!

Thanks again for the solid design work. Looking forward to getting these made!

Best regards,
[Your Name]

---

## Alternative Shorter Version (If You Want to Be More Direct):

---

**Subject: Need Manufacturing Files for PCB**

Hi [Freelancer Name],

The PCB design looks great! I'm ready to manufacture but need the export files:

**Required:**
1. ✅ Gerber files (complete set in .zip)
2. ✅ BOM as Excel/CSV (with part numbers and quantities)
3. ✅ Pick-and-place file (.csv)
4. ✅ Assembly drawings (PDF)
5. ✅ Schematic as PDF

**Quick Questions:**
- Total number of WS2812B LEDs? (Need 16 for firmware)
- Battery connector type?
- Motor connection details?

Timeline: Need files this week to get manufacturing quotes.

Thanks!
[Your Name]

---

Choose whichever style fits your communication with the freelancer!
