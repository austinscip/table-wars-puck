// TABLE WARS - Button Glyph Cap V2
// AESTHETIC VERSION - Proper Forerunner glyph

/* [Dimensions] */
outer_diameter = 15;
thickness = 2;
pin_diameter = 3;
pin_height = 3;

/* [Forerunner Glyph] */
glyph_depth = 1.5;        // MUCH DEEPER - very visible
glyph_size = 10;

/* [Resolution] */
$fn = 100;

module button_cap_v2() {
    difference() {
        union() {
            // Main cap with subtle dome
            translate([0, 0, thickness/2])
                scale([1, 1, 0.4])
                    sphere(d = outer_diameter);

            // Flatten bottom
            translate([0, 0, -5])
                cylinder(h = 5, d = outer_diameter);

            // Underside pin
            translate([0, 0, -pin_height])
                cylinder(h = pin_height, d = pin_diameter);
        }

        // Remove top excess
        translate([0, 0, thickness])
            cube([50, 50, 10], center = true);

        // Remove bottom excess
        translate([0, 0, -20])
            cube([50, 50, 20], center = true);

        // Forerunner glyph (complex geometric pattern)
        translate([0, 0, thickness - glyph_depth])
            forerunner_glyph(glyph_size);
    }
}

module forerunner_glyph(size) {
    // Central hexagon
    linear_extrude(height = glyph_depth + 1)
        circle(d = size * 0.4, $fn = 6);

    // Radiating triangular elements (classic Forerunner)
    for (i = [0:2]) {
        rotate([0, 0, i * 120])
            translate([0, size * 0.35, 0])
                linear_extrude(height = glyph_depth + 1)
                    polygon([
                        [0, size * 0.15],
                        [-size * 0.1, -size * 0.05],
                        [size * 0.1, -size * 0.05]
                    ]);
    }

    // Outer ring with segments
    linear_extrude(height = glyph_depth + 1)
        difference() {
            circle(d = size, $fn = 60);
            circle(d = size * 0.85, $fn = 60);

            // Segment gaps
            for (i = [0:5]) {
                rotate([0, 0, i * 60 + 30])
                    translate([size * 0.5, 0, 0])
                        square([size * 0.2, size * 0.3], center = true);
            }
        }
}

button_cap_v2();
