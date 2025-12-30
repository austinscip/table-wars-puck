// TABLE WARS - Forerunner Gaming Puck - Top Shell
// Generated CAD file - all dimensions from ENCLOSURE_SPEC.md v2.0
// Use OpenSCAD to render and export to STL

/* [Main Dimensions] */
outer_diameter = 95;          // mm
wall_thickness = 3.0;         // mm (thinner than bottom)
dome_height = 8;              // mm above rim
rim_height = 16;              // mm (vertical wall below dome)
total_height = dome_height + rim_height; // 24mm

/* [Button Hole] */
button_hole_diameter = 12;    // mm center hole for button

/* [LED Ring Mounts] */
led_ring_shelf_diameter = 53; // mm
led_ring_standoff_height = 12; // mm from interior top
led_standoff_diameter = 5;    // mm
m2_hole_diameter = 2.2;       // mm

/* [Screw Holes] */
num_screw_holes = 6;
screw_hole_diameter = 3.5;    // mm (clearance for M3)
screw_positions_radius = 40;  // mm from center
screw_countersink_diameter = 6; // mm
screw_countersink_depth = 2;  // mm

/* [Alignment Features] */
alignment_nub_diameter = 2;   // mm
alignment_nub_height = 2;     // mm
num_alignment_nubs = 3;

/* [Decorative Features] */
energy_ring_count = 3;        // Concentric raised rings
energy_ring_height = 0.5;     // mm raised
energy_ring_width = 1;        // mm

/* [Zip-Tie Anchor] */
zip_tie_post_diameter = 2;    // mm
zip_tie_post_height = 4;      // mm

/* [Resolution] */
$fn = 100; // Circle resolution

// ========================================
// MAIN ASSEMBLY
// ========================================

module top_shell() {
    difference() {
        union() {
            // Main dome shell
            dome_shell();

            // LED ring standoffs (inside)
            led_ring_standoffs();

            // Decorative energy rings
            energy_rings();

            // Zip-tie anchor near LED ring
            zip_tie_anchor();

            // Alignment nubs on bottom rim
            alignment_nubs();
        }

        // Cutouts
        union() {
            // Hollow interior
            hollow_interior();

            // Center button hole
            button_hole();

            // Screw holes
            screw_holes();

            // M2 holes in LED standoffs
            led_standoff_holes();
        }
    }
}

// ========================================
// DOME SHELL
// ========================================

module dome_shell() {
    // Create dome with smooth transition
    difference() {
        union() {
            // Cylindrical rim
            cylinder(h = rim_height, d = outer_diameter);

            // Dome top
            translate([0, 0, rim_height])
                scale([1, 1, dome_height / (outer_diameter/2)])
                    sphere(d = outer_diameter);
        }

        // Flatten bottom
        translate([0, 0, -50])
            cube([200, 200, 100], center = true);

        // Remove excess above dome
        translate([0, 0, rim_height + dome_height])
            cube([200, 200, 100], center = true);
    }
}

module hollow_interior() {
    inner_diameter = outer_diameter - (2 * wall_thickness);

    difference() {
        union() {
            // Hollow cylindrical section
            translate([0, 0, -1])
                cylinder(h = rim_height + 2, d = inner_diameter);

            // Hollow dome
            translate([0, 0, rim_height])
                scale([1, 1, (dome_height - wall_thickness) / (inner_diameter/2)])
                    sphere(d = inner_diameter);
        }

        // Keep floor solid up to 2mm
        translate([0, 0, -2])
            cube([200, 200, 4], center = true);
    }
}

// ========================================
// BUTTON HOLE
// ========================================

module button_hole() {
    // Through-hole in center for tactile button
    translate([0, 0, -1])
        cylinder(h = total_height + 10, d = button_hole_diameter);
}

// ========================================
// LED RING STANDOFFS
// ========================================

module led_ring_standoffs() {
    // 4× standoffs inside dome for LED ring mounting
    // Positioned at 0°, 90°, 180°, 270°
    for (i = [0:3]) {
        angle = i * 90;
        rotate([0, 0, angle])
            translate([led_ring_shelf_diameter/2, 0, 0])
                difference() {
                    cylinder(h = led_ring_standoff_height, d = led_standoff_diameter);
                }
    }
}

module led_standoff_holes() {
    for (i = [0:3]) {
        angle = i * 90;
        rotate([0, 0, angle])
            translate([led_ring_shelf_diameter/2, 0, 0])
                cylinder(h = led_ring_standoff_height + 1, d = m2_hole_diameter);
    }
}

// ========================================
// SCREW HOLES
// ========================================

module screw_holes() {
    for (i = [0:num_screw_holes-1]) {
        angle = i * (360 / num_screw_holes);
        rotate([0, 0, angle])
            translate([screw_positions_radius, 0, -1]) {
                // Through hole
                cylinder(h = rim_height + 5, d = screw_hole_diameter);

                // Countersink
                cylinder(h = screw_countersink_depth, d = screw_countersink_diameter);
            }
    }
}

// ========================================
// DECORATIVE ENERGY RINGS
// ========================================

module energy_rings() {
    // 3× concentric raised rings on top dome surface
    for (i = [1:energy_ring_count]) {
        ring_diameter = 30 + (i * 12); // Spacing outward
        translate([0, 0, rim_height + dome_height - 0.5])
            difference() {
                cylinder(h = energy_ring_height, d = ring_diameter + energy_ring_width);
                translate([0, 0, -1])
                    cylinder(h = energy_ring_height + 2, d = ring_diameter - energy_ring_width);
            }
    }
}

// ========================================
// ALIGNMENT FEATURES
// ========================================

module alignment_nubs() {
    // 3× small pins on bottom rim for alignment with bottom shell
    for (i = [0:num_alignment_nubs-1]) {
        angle = (i * (360 / num_alignment_nubs)) + 30; // Offset from screws
        rotate([0, 0, angle])
            translate([outer_diameter/2 - wall_thickness - 1, 0, -alignment_nub_height])
                cylinder(h = alignment_nub_height, d = alignment_nub_diameter);
    }
}

// ========================================
// ZIP-TIE ANCHOR
// ========================================

module zip_tie_anchor() {
    // Single post near LED ring for wire management
    translate([led_ring_shelf_diameter/2 + 5, 0, 2])
        cylinder(h = zip_tie_post_height, d = zip_tie_post_diameter);
}

// ========================================
// RENDER
// ========================================

top_shell();
