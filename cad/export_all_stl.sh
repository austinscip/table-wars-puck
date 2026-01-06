#!/bin/bash
# Export all OpenSCAD files to STL
# This may take 5-10 minutes total

echo "🎮 TABLE WARS - Exporting all CAD files to STL..."
echo ""

cd ~/table-wars-puck/cad

echo "1/5 Rendering button cap (30 sec)..."
openscad -o button_glyph_cap.stl button_glyph_cap.scad 2>&1 | grep -i "rendering\|finished\|error"

echo "2/5 Rendering motor sock (30 sec)..."
openscad -o motor_sock_tpu.stl motor_sock_tpu.scad 2>&1 | grep -i "rendering\|finished\|error"

echo "3/5 Rendering bumper ring (1 min)..."
openscad -o bumper_ring_tpu.stl bumper_ring_tpu.scad 2>&1 | grep -i "rendering\|finished\|error"

echo "4/5 Rendering top shell (2-3 min)..."
openscad -o forerunner_top_shell.stl forerunner_top_shell.scad 2>&1 | grep -i "rendering\|finished\|error"

echo "5/5 Rendering bottom shell (3-5 min)..."
openscad -o forerunner_bottom_shell.stl forerunner_bottom_shell.scad 2>&1 | grep -i "rendering\|finished\|error"

echo ""
echo "✅ Done! STL files created:"
ls -lh *.stl

echo ""
echo "Next steps:"
echo "1. Open STL files in your slicer (Cura, PrusaSlicer, etc.)"
echo "2. Print bottom shell first to test fit"
echo "3. See README.md for print settings"
