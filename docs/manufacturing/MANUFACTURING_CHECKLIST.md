# Manufacturing Files Checklist

Use this checklist when you receive files back from the freelancer.

---

## ✅ File Verification

### **Gerber Files** (Should receive a .zip file)
Open the zip and verify it contains:

- [ ] `.GTL` - Top copper layer
- [ ] `.GBL` - Bottom copper layer
- [ ] `.GTS` - Top soldermask
- [ ] `.GBS` - Bottom soldermask
- [ ] `.GTO` - Top silkscreen (component labels)
- [ ] `.GBO` - Bottom silkscreen
- [ ] `.GKO` or `.GM1` - Board outline
- [ ] `.TXT` or `.DRL` - Drill file
- [ ] At least 8-10 files total

**Quick Test:**
1. Go to https://www.pcbway.com/project/OnlineGerberViewer.html
2. Upload the Gerber zip file
3. You should see the circular PCB with all components visible
4. Check that it looks like the screenshots (1.jpg, 2.jpg)

---

### **Bill of Materials (BOM)**
Open the Excel/CSV file and verify:

- [ ] Has columns: Reference, Part Number, Description, Quantity, Package
- [ ] Lists all components from EXTRACTED_BOM.md (26+ items)
- [ ] ESP32-DEVKITC is listed
- [ ] MPU-6050 is listed (U4)
- [ ] Button SKRAAKE010 is listed (SW1)
- [ ] Buzzer PKMCS is listed (LS1)
- [ ] WS2812B LEDs listed (how many? Should be 16)
- [ ] All resistors (R1-R13) have values
- [ ] All capacitors (C1, C2, C4) have values and voltage ratings
- [ ] Part numbers are real (not "Generic" or "TBD")

**Red Flags:**
- ❌ If many parts say "Generic" or "TBD" - ask for specific part numbers
- ❌ If quantities don't add up - ask for clarification
- ❌ If expensive parts (ESP32, MPU6050) have wrong specs

---

### **Pick-and-Place File** (CPL or .csv)
Open the file and verify:

- [ ] Has columns: Designator, X, Y, Rotation, Layer
- [ ] Lists all SMD components (not through-hole parts)
- [ ] Coordinates are numbers (e.g., X=15.24, Y=20.32)

**Purpose:** Automated machines use this to place components. Not critical if you're hand-soldering.

---

### **Assembly Drawings** (PDF)
Open the PDF and verify:

- [ ] Shows top view with component outlines
- [ ] Shows bottom view (if components on both sides)
- [ ] Component labels visible (U1, R1, C1, etc.)
- [ ] Clear enough to identify where each part goes

**Purpose:** Visual guide for assembly. Critical if hand-soldering or debugging.

---

### **Schematic PDF**
Open the PDF and verify:

- [ ] Shows all circuit connections
- [ ] Component values visible (resistor values, capacitor values)
- [ ] ESP32 pin connections labeled
- [ ] Power supply section visible
- [ ] Multiple pages (likely 2-4 pages)

**Purpose:** Understanding how the circuit works. Critical for debugging.

---

## 🎯 Next Steps After Verification

### **Option 1: Get a Quote from JLCPCB** (Recommended)

1. Go to https://cart.jlcpcb.com/quote
2. Upload your Gerber zip file
3. Settings:
   - **Quantity:** 5 (for prototypes)
   - **PCB Thickness:** 1.6mm
   - **PCB Color:** Black (looks sick for a puck!)
   - **Surface Finish:** ENIG (better for USB-C)
   - **Remove Order Number:** Yes (if you want clean look)

4. Click **"SMT Assembly"** if you want them to solder components:
   - Upload BOM file
   - Upload Pick-and-place file
   - Select parts from their library
   - They'll quote assembly cost

**Expected Costs:**
- 5 bare PCBs: ~$10-20
- With assembly: +$50-100 (setup fee) + ~$15-25 per board
- **Total for 5 assembled boards:** ~$150-250

---

### **Option 2: Get a Quote from PCBWay**

1. Go to https://www.pcbway.com/orderonline.aspx
2. Upload Gerber zip
3. Similar settings as JLCPCB
4. They also offer assembly service

**Usually slightly more expensive but better customer service.**

---

### **Option 3: Order Bare PCBs + DIY Assembly**

**If you're comfortable soldering:**
1. Order bare PCBs from JLCPCB (~$10-20 for 5 boards)
2. Order components from Digikey/Mouser using the BOM
3. Solder components yourself

**Pros:** Cheaper (~$50-80 total for 5 pucks)
**Cons:** Requires soldering skills, takes time, easy to make mistakes

---

## ⚠️ Before You Order - Final Checks

### **Verify Against Your Firmware:**

Your firmware expects:
- [ ] **MPU6050** on I2C pins (GPIO 21/22 default)
- [ ] **Button** on GPIO 27
- [ ] **LEDs** on GPIO 13 (16x WS2812B)
- [ ] **Buzzer** on a PWM pin
- [ ] **Motor** on a transistor-controlled pin

**Action:** Cross-reference BOM with firmware pin assignments in `Config.h`

---

### **Component Availability Check:**

Before ordering PCBs, verify you can actually buy the parts:

1. Open the BOM
2. Search for each IC on Digikey.com:
   - ESP32-DEVKITC
   - MPU-6050 (or GY-521 module)
   - TP4057
   - MT3608
   - WS2812B2020

3. Check if they're **in stock**
4. If something is out of stock, ask freelancer for alternative part number

---

## 💡 Pro Tips

### **Start Small:**
- Order **5 boards** first, not 100
- Test one fully before ordering more
- Expect to find at least one bug in v1

### **Assembly Service Worth It?**
**Yes, if:**
- You've never soldered SMD components
- You value your time
- You want professional quality

**No, if:**
- You have soldering experience
- You enjoy DIY
- Budget is tight

### **Hybrid Approach (Best Value):**
1. Have PCB fab assemble **SMD components** (tiny parts like resistors, ICs)
2. You hand-solder **large parts** (ESP32 module, connectors, battery)
3. Good balance of cost vs. effort

---

## 📞 When to Contact Freelancer Again

Contact them if:
- ❌ Gerbers don't open in online viewer
- ❌ BOM has many "Generic" or "TBD" parts
- ❌ Part numbers don't exist on Digikey/Mouser
- ❌ Missing any of the required files
- ❌ LED count isn't 16 (your firmware requirement)
- ❌ MPU6050 or button aren't in the BOM

---

## 🎯 Success Criteria

**You're ready to order when:**
- ✅ Gerbers open in online viewer and look correct
- ✅ BOM has specific part numbers for all components
- ✅ All critical components (ESP32, MPU6050, button, LEDs) confirmed
- ✅ You've gotten a quote from manufacturer
- ✅ Total cost is acceptable (~$150-250 for 5 assembled boards)
- ✅ You understand the assembly process

---

## 🚀 After Manufacturing

**When you receive the boards:**

1. **Visual inspection** - Check for obvious defects
2. **Continuity test** - Use multimeter to verify no short circuits
3. **Power test** - Connect USB-C, measure voltages
4. **Program ESP32** - Upload your firmware
5. **Functional test** - Test BLE, WiFi, LEDs, button, sensor
6. **Report issues** - Document anything that doesn't work

**Then come back and we'll debug together!** 🎉

---

**You've got this!** The hardest part (designing the PCB) is done. Now it's just following the manufacturing process.
