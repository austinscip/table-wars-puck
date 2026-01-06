// BUTTON POSITION TEST - Find the right height

// Show dome alone
color([0.3, 0.5, 0.8, 0.7])
    import("forerunner_top_shell_v2_PROMINENT.stl");

// Show button MUCH HIGHER - testing different heights
// Dome top = 26mm, trying button at 32mm (6mm above green plane)
translate([0, 0, 32])
    color([1, 0, 0, 1.0])  // RED so we can see it clearly
        import("button_glyph_cap_v2_PROMINENT.stl");

// Reference line showing dome top surface
translate([0, 0, 26])
    color([0, 1, 0, 0.5])
        cylinder(h=0.2, d=50, $fn=100);
