// TABLE WARS - Forerunner Gaming Puck - Bottom Shell V3
// CUSTOM PCB VERSION - Optimized for 88-90mm circular PCB
// Follows Sid's technical specification exactly

/* [Main Dimensions] */
outer_diameter = 95;
wall_thickness = 3.5;
internal_height = 32;
total_height = 40;
base_thickness = 2.5;

/* [PCB Mounting] */
pcb_diameter = 89;              // 88-90mm circular PCB
pcb_thickness = 1.6;            // Standard PCB thickness
pcb_standoff_height = 6;        // Height from base to PCB bottom
pcb_standoff_diameter = 5;      // Standoff post diameter
num_pcb_standoffs = 6;          // Mounting points around PCB
pcb_standoff_radius = 38;       // Distance from center
m2_5_hole_diameter = 2.7;       // M2.5 mounting holes

/* [Screw Bosses - M3] */
num_screw_bosses = 6;
screw_boss_diameter = 7;
screw_boss_height = 35;
m3_insert_diameter = 4.2;
m3_insert_depth = 5;
screw_positions_radius = 40;

/* [O-Ring Groove] */
o_ring_groove_width = 2;
o_ring_groove_depth = 2;
o_ring_groove_id = 89;

/* [Component Clearances on PCB] */
// These are keepout zones where PCB components sit
led_ring_diameter = 60;         // LED ring on PCB edge
mpu_centered = true;            // MPU6050 at exact center
center_keepout_diameter = 25;   // Central area for MPU + button
usb_cutout_width = 10;
usb_cutout_height = 5;
usb_cutout_center_height = 8;
usb_cutout_angle = 90;

/* [Battery Mount] */
battery_tray_x = 62;
battery_tray_y = 37;
battery_tray_depth = 8.5;       // Reduced from 9mm to fix clearance
battery_tray_z_offset = 24;     // Height from base (lowered 3mm)

/* [Wire Channels] */
wire_channel_width = 4;
wire_channel_depth = 3;

/* [Ventilation] */
thermal_vent_width = 3;
thermal_vent_length = 10;
sound_vent_width = 2;
sound_vent_length = 8;

/* [Aesthetics] */
base_detail_count = 4;
hexagon_detail_count = 6;

/* [Resolution] */
$fn = 120;

// ========================================
// MAIN ASSEMBLY
// ========================================

module bottom_shell_v3_pcb() {
    difference() {
        union() {
            // Enhanced shell body
            enhanced_shell_body();

            // Screw bosses with decorative caps
            enhanced_screw_bosses();

            // PCB standoffs (replaces component-specific mounts)
            pcb_standoffs();

            // Decorative elements
            base_decorative_ridges();
            forerunner_hexagons();
        }

        // Cutouts
        union() {
            hollow_interior();
            o_ring_groove();
            screw_boss_inserts();

            // Battery tray (above PCB)
            battery_tray_cutout();

            // USB-C cutout for TP4057 on PCB
            usb_cutout();

            // Ventilation vents
            enhanced_thermal_vents();
            enhanced_sound_vents();

            // Wire routing channels
            wire_channels();

            // M2.5 holes in PCB standoffs
            pcb_standoff_holes();
        }
    }
}

// ========================================
// SHELL BODY
// ========================================

module enhanced_shell_body() {
    difference() {
        // Outer cylinder with subtle taper
        cylinder(h = total_height, d1 = outer_diameter, d2 = outer_diameter - 0.5);

        // Remove top
        translate([0, 0, total_height - 0.1])
            cylinder(h = 5, d = outer_diameter + 2);
    }
}

module hollow_interior() {
    inner_diameter = outer_diameter - (2 * wall_thickness);
    translate([0, 0, base_thickness])
        cylinder(h = internal_height + 10, d = inner_diameter);
}

// ========================================
// PCB MOUNTING SYSTEM
// ========================================

module pcb_standoffs() {
    // 6 standoffs around PCB perimeter for M2.5 screws
    for (i = [0:num_pcb_standoffs-1]) {
        angle = i * (360 / num_pcb_standoffs);
        rotate([0, 0, angle])
            translate([pcb_standoff_radius, 0, base_thickness]) {
                // Main standoff post
                cylinder(h = pcb_standoff_height, d = pcb_standoff_diameter);

                // Decorative top cap
                translate([0, 0, pcb_standoff_height - 0.5])
                    cylinder(h = 0.5, d = pcb_standoff_diameter + 1, $fn = 6);
            }
    }

    // Center support post (doesn't interfere with centered MPU)
    // Small post under PCB center for mechanical support
    translate([0, 0, base_thickness])
        cylinder(h = pcb_standoff_height - 1, d = 8);
}

module pcb_standoff_holes() {
    // M2.5 mounting holes in standoffs
    for (i = [0:num_pcb_standoffs-1]) {
        angle = i * (360 / num_pcb_standoffs);
        rotate([0, 0, angle])
            translate([pcb_standoff_radius, 0, base_thickness])
                cylinder(h = pcb_standoff_height + 2, d = m2_5_hole_diameter);
    }
}

// ========================================
// SCREW BOSSES
// ========================================

module enhanced_screw_bosses() {
    for (i = [0:num_screw_bosses-1]) {
        angle = i * (360 / num_screw_bosses);
        rotate([0, 0, angle])
            translate([screw_positions_radius, 0, 0]) {
                // Main boss
                cylinder(h = screw_boss_height, d = screw_boss_diameter);

                // Decorative hexagonal cap
                translate([0, 0, screw_boss_height - 2])
                    cylinder(h = 2, d = screw_boss_diameter + 1, $fn = 6);
            }
    }
}

module screw_boss_inserts() {
    for (i = [0:num_screw_bosses-1]) {
        angle = i * (360 / num_screw_bosses);
        rotate([0, 0, angle])
            translate([screw_positions_radius, 0, screw_boss_height - m3_insert_depth])
                cylinder(h = m3_insert_depth + 1, d = m3_insert_diameter);
    }
}

// ========================================
// O-RING GROOVE
// ========================================

module o_ring_groove() {
    translate([0, 0, total_height - o_ring_groove_depth])
        difference() {
            cylinder(h = o_ring_groove_depth + 1, d = outer_diameter - wall_thickness);
            cylinder(h = o_ring_groove_depth + 1, d = o_ring_groove_id);
        }
}

// ========================================
// BATTERY TRAY (ABOVE PCB)
// ========================================

module battery_tray_cutout() {
    // Battery sits above PCB, below top shell
    // Lowered by 3mm to fix clearance issue
    translate([0, 0, battery_tray_z_offset])
        cube([battery_tray_x, battery_tray_y, battery_tray_depth + 1], center = true);

    // Ventilation slots under tray
    for (i = [0:3]) {
        translate([i * 8 - 12, 0, battery_tray_z_offset - 2])
            cube([3, 15, 3], center = true);
    }
}

// ========================================
// USB-C CUTOUT (TP4057 ON PCB)
// ========================================

module usb_cutout() {
    // Cutout in side wall for USB-C charging port
    rotate([0, 0, usb_cutout_angle])
        translate([outer_diameter/2 - wall_thickness - 1, 0, usb_cutout_center_height])
            rotate([0, 90, 0])
                hull() {
                    cylinder(h = wall_thickness + 2, d = usb_cutout_height);
                    translate([usb_cutout_width - usb_cutout_height, 0, 0])
                        cylinder(h = wall_thickness + 2, d = usb_cutout_height);
                }
}

// ========================================
// VENTILATION
// ========================================

module enhanced_thermal_vents() {
    // 4× Forerunner-style thermal vents
    for (i = [0:3]) {
        angle = i * 90;
        rotate([0, 0, angle])
            translate([15, 0, base_thickness + 8]) {
                // Main vent slot
                cube([thermal_vent_width, thermal_vent_length, 10], center = true);

                // Decorative hexagonal frame
                translate([0, 0, 5])
                    difference() {
                        cube([thermal_vent_width + 2, thermal_vent_length + 2, 0.5], center = true);
                        cube([thermal_vent_width, thermal_vent_length, 1], center = true);
                    }
            }
    }
}

module enhanced_sound_vents() {
    // 6× Forerunner glyph-style sound vents
    for (i = [0:5]) {
        angle = 45 + (i * 10) - 25;
        rotate([0, 0, angle])
            translate([20, 0, base_thickness + 12]) {
                // Angled vent slot
                rotate([0, 5, 0])
                    cube([sound_vent_width, sound_vent_length, 8], center = true);
            }
    }
}

// ========================================
// WIRE CHANNELS
// ========================================

module wire_channels() {
    // Radial channels from PCB center to edge components
    // Channels run underneath/alongside PCB

    // Central vertical channel for LED ring wires
    translate([0, 0, base_thickness])
        cylinder(h = pcb_standoff_height + 5, d = wire_channel_width);

    // Radial channels to USB-C area
    hull() {
        translate([0, 0, base_thickness + 2])
            cylinder(h = wire_channel_depth, d = wire_channel_width);
        translate([outer_diameter/2 - 10, 0, base_thickness + 2])
            cylinder(h = wire_channel_depth, d = wire_channel_width);
    }
}

// ========================================
// DECORATIVE ELEMENTS
// ========================================

module base_decorative_ridges() {
    // Subtle ridges on base exterior
    for (i = [0:base_detail_count-1]) {
        angle = i * 90;
        rotate([0, 0, angle + 45])
            translate([outer_diameter/2 - 2, 0, 1])
                rotate([90, 0, 0])
                    cylinder(h = 15, d = 0.8, center = true);
    }
}

module forerunner_hexagons() {
    // Decorative hexagons around perimeter - BIGGER AND MORE VISIBLE
    for (i = [0:hexagon_detail_count-1]) {
        angle = i * 60;
        rotate([0, 0, angle])
            translate([outer_diameter/2 - 3, 0, total_height/2])
                rotate([90, 0, 0])
                    difference() {
                        cylinder(h = 2.0, d = 8, $fn = 6, center = true);
                        cylinder(h = 2.2, d = 4, $fn = 6, center = true);
                    }
    }
}

// ========================================
// RENDER
// ========================================

bottom_shell_v3_pcb();
