// DEBUG: Show full assembly with reference planes
$fn = 100;

// Bottom shell
color([0.1, 0.1, 0.1, 1.0])
    import("forerunner_bottom_shell_v3_pcb_PROMINENT.stl");

// Top shell
color([0.3, 0.5, 0.8, 0.5])  // MORE transparent to see button
    import("forerunner_top_shell_v2_PROMINENT.stl");

// Bumper ring
translate([0, 0, 24])
    color([0.05, 0.05, 0.05, 1.0])
        import("bumper_ring_tpu.stl");

// BUTTON - testing different heights
// Current position: z=32
translate([0, 0, 32])
    color([1, 0, 0, 1.0])  // BRIGHT RED
        import("button_glyph_cap_v2_PROMINENT.stl");

// ALSO try z=38 to compare
translate([20, 0, 38])
    color([0, 1, 0, 1.0])  // BRIGHT GREEN
        import("button_glyph_cap_v2_PROMINENT.stl");

// ALSO try z=44 to compare
translate([-20, 0, 44])
    color([0, 0, 1, 1.0])  // BRIGHT BLUE
        import("button_glyph_cap_v2_PROMINENT.stl");

// Reference plane at z=26 (dome top surface)
translate([0, 0, 26])
    color([1, 1, 0, 0.3])
        cylinder(h=0.5, d=60, $fn=100);
