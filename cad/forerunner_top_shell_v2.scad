// TABLE WARS - Forerunner Gaming Puck - Top Shell V2
// AESTHETIC VERSION - Proper Forerunner styling
// Use OpenSCAD to render and export to STL

/* [Main Dimensions] */
outer_diameter = 95;          // mm
wall_thickness = 3.0;         // mm
dome_height = 8;              // mm above rim
rim_height = 16;              // mm
total_height = dome_height + rim_height;

/* [Button Hole] */
button_hole_diameter = 12;    // mm

/* [LED Ring Mounts] */
led_ring_shelf_diameter = 53;
led_ring_standoff_height = 12;
led_standoff_diameter = 5;
m2_hole_diameter = 2.2;

/* [Screw Holes] */
num_screw_holes = 6;
screw_hole_diameter = 3.5;
screw_positions_radius = 40;
screw_countersink_diameter = 6;
screw_countersink_depth = 2;

/* [Aesthetics] */
energy_ring_count = 3;
energy_ring_height = 2.0;     // MUCH MORE PROMINENT
energy_ring_width = 2.5;
hexagon_count = 6;            // Decorative hexagons
diffusion_channel_count = 16; // Light channels

/* [Resolution] */
$fn = 120; // Higher resolution for smoother curves

// ========================================
// MAIN ASSEMBLY
// ========================================

module top_shell_v2() {
    difference() {
        union() {
            // Enhanced dome shell with smooth transitions
            enhanced_dome_shell();

            // LED ring standoffs
            led_ring_standoffs();

            // Decorative energy rings (more prominent)
            enhanced_energy_rings();

            // Forerunner hexagonal details around rim
            hexagonal_details();

            // Alignment nubs
            alignment_nubs();
        }

        // Cutouts
        union() {
            // Hollow interior
            hollow_interior();

            // Center button hole with decorative recess
            enhanced_button_hole();

            // Screw holes with decorative recesses
            enhanced_screw_holes();

            // LED standoff holes
            led_standoff_holes();

            // Light diffusion channels radiating from center
            light_diffusion_channels();
        }
    }
}

// ========================================
// ENHANCED DOME SHELL
// ========================================

module enhanced_dome_shell() {
    difference() {
        union() {
            // Cylindrical rim with subtle taper
            cylinder(h = rim_height, d1 = outer_diameter + 0.5, d2 = outer_diameter);

            // Smoother dome using scale
            translate([0, 0, rim_height])
                scale([1, 1, 0.35])  // Elliptical dome for better proportions
                    sphere(d = outer_diameter);

            // Transition ring at dome base
            translate([0, 0, rim_height - 0.5])
                cylinder(h = 1, d1 = outer_diameter, d2 = outer_diameter - 1);
        }

        // Flatten bottom
        translate([0, 0, -50])
            cube([200, 200, 100], center = true);

        // Remove excess above dome
        translate([0, 0, rim_height + dome_height + 0.5])
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

            // Hollow dome (slightly smaller dome inside)
            translate([0, 0, rim_height])
                scale([1, 1, 0.35])
                    sphere(d = inner_diameter);
        }

        // Keep floor solid
        translate([0, 0, -2])
            cube([200, 200, 4], center = true);
    }
}

// ========================================
// ENHANCED BUTTON HOLE
// ========================================

module enhanced_button_hole() {
    // Through-hole with decorative stepped recess
    translate([0, 0, -1])
        cylinder(h = total_height + 10, d = button_hole_diameter);

    // Decorative recessed circle around button
    translate([0, 0, rim_height + dome_height - 0.8])
        cylinder(h = 1, d = button_hole_diameter + 4, $fn = 60);

    // Subtle ring detail
    translate([0, 0, rim_height + dome_height - 0.4])
        difference() {
            cylinder(h = 0.5, d = button_hole_diameter + 6);
            cylinder(h = 0.6, d = button_hole_diameter + 5);
        }
}

// ========================================
// LED RING STANDOFFS
// ========================================

module led_ring_standoffs() {
    for (i = [0:3]) {
        angle = i * 90;
        rotate([0, 0, angle])
            translate([led_ring_shelf_diameter/2, 0, 0])
                cylinder(h = led_ring_standoff_height, d = led_standoff_diameter);
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
// ENHANCED SCREW HOLES
// ========================================

module enhanced_screw_holes() {
    for (i = [0:num_screw_holes-1]) {
        angle = i * (360 / num_screw_holes);
        rotate([0, 0, angle])
            translate([screw_positions_radius, 0, -1]) {
                // Through hole
                cylinder(h = rim_height + 5, d = screw_hole_diameter);

                // Decorative hexagonal countersink
                cylinder(h = screw_countersink_depth, d = screw_countersink_diameter, $fn = 6);

                // Subtle outer ring
                difference() {
                    cylinder(h = 0.5, d = screw_countersink_diameter + 2, $fn = 6);
                    translate([0, 0, -0.1])
                        cylinder(h = 0.7, d = screw_countersink_diameter, $fn = 6);
                }
            }
    }
}

// ========================================
// ENHANCED ENERGY RINGS
// ========================================

module enhanced_energy_rings() {
    for (i = [1:energy_ring_count]) {
        ring_diameter = 25 + (i * 15);

        translate([0, 0, rim_height + dome_height - 0.2])
            difference() {
                // Outer cylinder
                cylinder(h = energy_ring_height, d = ring_diameter + energy_ring_width);

                // Inner cutout
                translate([0, 0, -0.5])
                    cylinder(h = energy_ring_height + 1, d = ring_diameter - energy_ring_width);

                // Subtle faceting for Forerunner look
                for (j = [0:11]) {
                    rotate([0, 0, j * 30])
                        translate([ring_diameter/2, 0, energy_ring_height/2])
                            rotate([0, 3, 0])
                                cube([2, 5, energy_ring_height + 1], center = true);
                }
            }
    }
}

// ========================================
// HEXAGONAL DECORATIVE DETAILS
// ========================================

module hexagonal_details() {
    // 6× decorative Forerunner hexagons around perimeter
    for (i = [0:hexagon_count-1]) {
        angle = (i * 60) + 30; // Offset from screw holes
        rotate([0, 0, angle])
            translate([outer_diameter/2 - 4, 0, rim_height/2])
                rotate([90, 0, 0])
                    difference() {
                        cylinder(h = 0.8, d = 5, $fn = 6, center = true);
                        // Small indent in center
                        cylinder(h = 1, d = 2, $fn = 6, center = true);
                    }
    }
}

// ========================================
// LIGHT DIFFUSION CHANNELS
// ========================================

module light_diffusion_channels() {
    // Radial channels from center for light diffusion - DEEPER AND WIDER
    for (i = [0:diffusion_channel_count-1]) {
        angle = i * (360 / diffusion_channel_count);
        rotate([0, 0, angle])
            translate([0, 0, rim_height + dome_height - 1.5])
                hull() {
                    // Inner point
                    translate([button_hole_diameter/2 + 2, 0, 0])
                        cylinder(h = 2, d = 1.5);
                    // Outer point
                    translate([35, 0, 0])
                        cylinder(h = 2, d = 2.0);
                }
    }
}

// ========================================
// ALIGNMENT FEATURES
// ========================================

module alignment_nubs() {
    num_alignment_nubs = 3;
    for (i = [0:num_alignment_nubs-1]) {
        angle = (i * (360 / num_alignment_nubs)) + 30;
        rotate([0, 0, angle])
            translate([outer_diameter/2 - wall_thickness - 1, 0, -2])
                cylinder(h = 2, d = 2);
    }
}

// ========================================
// RENDER
// ========================================

top_shell_v2();
