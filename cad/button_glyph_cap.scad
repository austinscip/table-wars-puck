// TABLE WARS - Button Glyph Cap
// Printed separately in PETG, glued to tactile button

/* [Dimensions] */
outer_diameter = 15;      // mm
thickness = 2;            // mm
pin_diameter = 3;         // mm (underside pin for button stem)
pin_height = 3;           // mm

/* [Forerunner Glyph] */
glyph_depth = 0.3;        // mm (engraved symbol)
glyph_diameter = 10;      // mm

/* [Resolution] */
$fn = 100;

module button_cap() {
    difference() {
        union() {
            // Main cap disc
            cylinder(h = thickness, d = outer_diameter);

            // Underside pin (contacts button stem)
            translate([0, 0, -pin_height])
                cylinder(h = pin_height, d = pin_diameter);
        }

        // Forerunner glyph on top (simplified hexagon)
        translate([0, 0, thickness - glyph_depth])
            linear_extrude(height = glyph_depth + 0.5)
                circle(d = glyph_diameter, $fn = 6); // Hexagon
    }
}

button_cap();
