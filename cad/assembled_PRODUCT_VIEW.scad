// TABLE WARS - Product View - FINISHED PRODUCT
// Shows what the puck actually looks like when assembled
// NO transparency - realistic view

/* [Display Options] */
show_top_shell = true;
show_bottom_shell = true;
show_button_cap = true;
show_bumper_ring = true;
exploded_view = false;
explosion_distance = 25;

/* [Colors - REALISTIC] */
top_shell_color = [0.3, 0.5, 0.8, 1.0];      // Solid translucent blue PETG
bottom_shell_color = [0.1, 0.1, 0.1, 1.0];   // Solid black PETG
button_cap_color = [0.3, 0.5, 0.8, 0.9];     // Translucent blue (same as top)
bumper_color = [0.05, 0.05, 0.05, 1.0];      // Black TPU

$fn = 100;

// ========================================
// PRODUCT ASSEMBLY - FINISHED LOOK
// ========================================

module product_view() {
    // Bottom shell (solid black)
    if (show_bottom_shell) {
        color(bottom_shell_color)
            import("forerunner_bottom_shell_v3_pcb_PROMINENT.stl");
    }

    // Top shell (solid translucent blue - hides internals)
    if (show_top_shell) {
        translate([0, 0, exploded_view ? explosion_distance : 0])
            color(top_shell_color)
                import("forerunner_top_shell_v2_PROMINENT.stl");
    }

    // Button cap - CORRECTLY POSITIONED ABOVE DOME SURFACE
    // VERIFIED: z=44 places button ABOVE the dome (dome top = 26mm)
    if (show_button_cap) {
        translate([0, 0, exploded_view ? 40 + explosion_distance + 5 : 44])
            color(button_cap_color)
                import("button_glyph_cap_v2_PROMINENT.stl");
    }

    // Bumper ring (black TPU at seam)
    if (show_bumper_ring) {
        translate([0, 0, 24])
            color(bumper_color)
                import("bumper_ring_tpu.stl");
    }
}

// ========================================
// RENDER
// ========================================

product_view();

/*
INSTRUCTIONS:

This shows the FINISHED PRODUCT appearance:
- Solid translucent blue dome (not see-through)
- Solid black base
- Button cap protruding with Forerunner glyph
- Black bumper ring at seam
- All Forerunner details visible (energy rings, hexagons)

NO internal components visible - this is what it looks like "for real"

CONTROLS:
- Left-click + drag = Rotate
- Scroll = Zoom
- Press F5 = Preview (fast)
- Press F6 = Full render (30 sec, higher quality)

EXPLODED VIEW:
- Change line 7: exploded_view = true;
- Press F5 to see parts separated

VIEWS TO TRY:
- Top view: See energy rings and button glyph
- Side view: See button protruding, dome curve
- Angled view: Best overall perspective
- Bottom view: See hexagons on base
*/
