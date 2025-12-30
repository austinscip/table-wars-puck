# How to Export STL Files Manually

The command-line export isn't working (likely needs Rosetta 2). Here's how to export using the GUI instead:

## Step-by-Step Instructions

### 1. Open OpenSCAD Application
```bash
open /Applications/OpenSCAD-2021.01.app
```

Or find it in your Applications folder and double-click.

### 2. For Each File, Do This:

#### File 1: Button Cap (15 seconds)
1. **File → Open** → Navigate to `~/table-wars-puck/cad/button_glyph_cap.scad`
2. Wait for preview to appear (automatic)
3. **Design → Render** (or press **F6**)
   - Bottom right will show "Rendering..."
   - Wait for "Rendering finished" (~5-10 seconds)
4. **File → Export → Export as STL**
5. Save as: `button_glyph_cap.stl` (in same folder)

#### File 2: Motor Sock (15 seconds)
1. **File → Open** → `motor_sock_tpu.scad`
2. **Design → Render** (F6)
3. **File → Export → Export as STL**
4. Save as: `motor_sock_tpu.stl`

#### File 3: Bumper Ring (30 seconds)
1. **File → Open** → `bumper_ring_tpu.scad`
2. **Design → Render** (F6)
3. Wait for rendering to finish (~20-30 sec, higher resolution)
4. **File → Export → Export as STL**
5. Save as: `bumper_ring_tpu.stl`

#### File 4: Top Shell (1-2 minutes)
1. **File → Open** → `forerunner_top_shell.scad`
2. **Design → Render** (F6)
3. Wait for rendering (~60-120 seconds, complex geometry)
4. **File → Export → Export as STL**
5. Save as: `forerunner_top_shell.stl`

#### File 5: Bottom Shell (2-3 minutes)
1. **File → Open** → `forerunner_bottom_shell.scad`
2. **Design → Render** (F6)
3. Wait for rendering (~120-180 seconds, most complex)
4. **File → Export → Export as STL**
5. Save as: `forerunner_bottom_shell.stl`

## Total Time: ~5-7 minutes

## Troubleshooting

**"Compile Error" appears:**
- This is just a warning during preview
- Click **Design → Render** anyway
- It will compile properly for rendering

**Rendering seems stuck:**
- Check the bottom-right corner for progress
- Complex parts (shells) can take 2-3 minutes
- Look for "Rendering finished" message

**Can't find the menu:**
- macOS: Menu bar is at the very top of screen, not in the window
- Make sure OpenSCAD window is active (click on it)

## What You'll Have When Done

Five .stl files ready for 3D printing:
- `button_glyph_cap.stl` (~50 KB)
- `motor_sock_tpu.stl` (~100 KB)
- `bumper_ring_tpu.stl` (~200 KB)
- `forerunner_top_shell.stl` (~500 KB - 1 MB)
- `forerunner_bottom_shell.stl` (~1-2 MB)

## Next Steps

1. **Test the STLs**: Open in your slicer to verify they look correct
2. **Send to Sid**: Attach the 5 .stl files to your Freelancer message
3. **Or use a 3D printing service**: Upload to Xometry, Craftcloud, etc.

---

**Start here:** Open OpenSCAD and begin with the button cap (fastest render).
