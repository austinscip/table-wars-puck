# GAMEPLAN TO FIX THE FUCKING BUTTON

## THE PROBLEM:
Button keeps appearing INSIDE the dome hole, not sticking OUT above the surface.

## WHY IT'S HAPPENING:
The dome has a HOLE in the center (for the button to go through).
I'm positioning the button AT a height, but it's sitting IN that hole, not ABOVE the dome surface.

## THE FIX - STEP BY STEP:

### STEP 1: MEASURE THE DOME TOP SURFACE
- Render ONLY the top shell (no button)
- Measure the HIGHEST POINT of the dome surface
- Dome specs: rim_height=16mm + dome_height=8mm = 24mm base
- Energy rings add 2mm on top = 26mm HIGHEST SURFACE

### STEP 2: MEASURE THE BUTTON CAP
- Check button_glyph_cap_v2.scad to see dimensions
- Find where the PRESSABLE DISC starts (not the pin underneath)
- Understand the button's coordinate system (where is z=0?)

### STEP 3: CALCULATE CORRECT POSITION
- Button's BOTTOM surface needs to be ABOVE 26mm (dome top)
- Add 2-3mm gap so button clearly protrudes
- Button bottom should be at ~28-29mm minimum
- Account for button cap's internal coordinate system

### STEP 4: TEST RENDER SIDE-BY-SIDE
- Render top shell ALONE
- Render button ALONE
- Render BOTH TOGETHER
- Verify button is VISIBLY ABOVE dome surface

### STEP 5: VERIFY FROM MULTIPLE ANGLES
- Top view: Button should be OUTSIDE the dome outline
- Side view: Button should clearly stick UP above dome curve
- 45° angle: Button should be obviously protruding

## EXECUTION PLAN:

1. Read button_glyph_cap_v2.scad to understand dimensions
2. Render top shell alone to confirm dome height
3. Calculate exact button position accounting for:
   - Dome top = 26mm
   - Button cap thickness = ?mm
   - Protrusion desired = 3-4mm
4. Update all 3 assembled view files with CORRECT position
5. Render and SHOW YOU before claiming it's fixed

## NO MORE GUESSING:
- No more random heights (28, 30, 35)
- MEASURE first, THEN position
- VERIFY before showing you

Let me execute this NOW.
