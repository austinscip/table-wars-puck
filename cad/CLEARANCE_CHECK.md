# CLEARANCE CHECK - Gaming Puck Internal Layout

## Current Dimensions (from V2 design)

### Shell Heights:
- Base thickness: **2.5mm**
- Internal height: **32mm**
- Total height: **40mm**
- **Usable internal space: 2.5mm → 34.5mm** (32mm cavity)

---

## Component Stack Heights (Bottom to Top)

### 1. Base Level (2.5mm - 8.5mm)
**ESP32 on standoffs:**
- Standoff height: 6mm
- ESP32 board: ~1mm PCB
- **Top of standoffs: 8.5mm**

### 2. ESP32 Level (8.5mm - 23.5mm)
**ESP32 DevKitC with headers:**
- Board thickness: 1mm
- Components + USB connector height: ~14mm
- **Top of ESP32: 8.5 + 15 = 23.5mm** ✅ GOOD

### 3. Battery Tray Level (26.5mm - 35.5mm)
**Battery placement:**
- Tray starts at: 2.5 + 6 + 18 = **26.5mm**
- Battery thickness: 8mm
- Tray depth: 9mm (includes clearance)
- **Top of battery tray: 26.5 + 9 = 35.5mm** ⚠️ **PROBLEM!**

### 4. Top Shell Join (34.5mm - 40mm)
- Internal cavity ends at: **34.5mm**
- O-ring groove at: ~38mm
- Shell seam at: ~24mm (rim height)

---

## ⚠️ CLEARANCE ISSUE FOUND

**Battery tray collision:**
```
Battery tray top:     35.5mm
Internal cavity top:  34.5mm
OVERLAP:              1.0mm  ❌ PROBLEM
```

**This means the battery tray extends 1mm BEYOND the internal cavity.**

---

## Button Location & Gaming

### Current Button Design:
- **Location:** Dead center (0, 0)
- **Tower height:** 10mm from base
- **Button mounting height:** ~12.5mm from base
- **Accessible through:** 12mm hole in top shell center
- **Travel distance:** ~0.5mm tactile click

### For Gaming - Is This Optimal?

**Pros:**
✅ Thumb naturally rests on center
✅ Easy to press while holding puck
✅ Accessible from any grip angle
✅ Clear tactile feedback

**Cons:**
⚠️ Only ONE button (your games need multiple inputs?)
⚠️ Button tower interferes with wire routing to LED ring
⚠️ No secondary button for complex games

---

## Component Placement Review

### LED Ring (Top Shell Interior)
- **Location:** 53mm diameter shelf, 12mm from top interior
- **Visibility:** Should shine through translucent dome ✅
- **Wire routing:** Goes through center (near button) ⚠️

### MPU6050 (Motion Sensor)
- **Location:** 25mm from center
- **Purpose:** Detects puck movement/acceleration
- **Gaming:** Critical for motion-based games ✅
- **Placement:** Should be centered for best accuracy ⚠️
  - Currently offset - may cause asymmetric motion detection

### Vibration Motor
- **Location:** 30mm from center, opposite MPU6050
- **Purpose:** Haptic feedback
- **Gaming:** Good for impact/collision feedback ✅
- **Concern:** Vibration will affect MPU6050 readings ⚠️

---

## Recommended Fixes

### CRITICAL FIX: Battery Clearance
**Option A - Lower battery tray:**
```scad
tray_z = base_thickness + esp32_standoff_height + 15;  // Changed from 18 to 15
```
- Battery tray top: 2.5 + 6 + 15 + 9 = **32.5mm** ✅
- Clearance to cavity top: 34.5 - 32.5 = **2mm** ✅ GOOD

**Option B - Reduce tray depth:**
```scad
battery_tray_depth = 8.5;  // Changed from 9 to 8.5
```
- Battery is 8mm thick, so 8.5mm gives 0.5mm clearance (tight but OK)

### GAMING OPTIMIZATION

**For your 37 games, verify:**

1. **Single button is enough?**
   - Most games: Hold/Shake/Tap/Multi-tap = ✅ Works
   - Complex games: May need secondary input
   - **Check:** Do any games need 2+ simultaneous buttons?

2. **MPU6050 placement:**
   - **Current:** 25mm offset from center
   - **Better:** Should be at exact center (0, 0) for symmetrical motion
   - **Issue:** Button tower is already at center
   - **Solution:** Move MPU6050 closer to center, offset button slightly?

3. **Motor vibration interference:**
   - Vibration motor at 30mm will shake the whole puck
   - MPU6050 will detect this as false motion
   - **Solution:** Add dampening (TPU motor sock helps ✅) or filter in firmware

---

## Questions for You

Before I fix the design, clarify:

### 1. Button Configuration
**Do any of your 37 games require:**
- Two buttons pressed simultaneously?
- Long-press + short-press combinations?
- Button held while shaking?

**Current design assumes:** Single button is sufficient for all games

### 2. Motion Sensing Priority
**Is accurate motion detection critical?**
- YES → MPU6050 should be at exact center
- NO → Current offset placement is fine

### 3. Component Priority
**What's most important for gameplay:**
- A) Accurate motion/tilt (MPU6050 centered)
- B) Haptic feedback (motor strong vibration)
- C) LED animations (bright, visible ring)
- D) Button responsiveness (tactile, centered)

---

## Current Status

**Functional:** ✅ All components fit (with fixes)
**Gaming-optimized:** ⚠️ Needs verification against game requirements
**Clearance issue:** ❌ Battery tray needs 1mm adjustment

**I can fix the battery clearance in 30 seconds. But I need your input on gaming optimization before making changes.**

---

**Answer these and I'll regenerate optimized CAD files:**

1. Is single center button OK for all 37 games?
2. Do you need precise motion sensing (MPU centered) or is offset OK?
3. What's your priority ranking: Motion, Haptics, LEDs, or Button?
