// TABLE WARS - Forerunner Gaming Puck - Bottom Shell V2
// AESTHETIC VERSION - Proper Forerunner styling

/* [Main Dimensions] */
outer_diameter = 95;
wall_thickness = 3.5;
internal_height = 32;
total_height = 40;
base_thickness = 2.5;

/* [Screw Bosses] */
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

/* [Component Mounts] */
esp32_mount_x = 56;
esp32_mount_y = 28;
esp32_standoff_height = 6;
esp32_standoff_diameter = 5;
m2_hole_diameter = 2.2;

button_tower_width = 20;
button_tower_height = 10;

battery_tray_x = 62;
battery_tray_y = 37;
battery_tray_depth = 9;

motor_pocket_diameter = 12.5;
motor_pocket_depth = 8;
motor_offset_from_center = 30;

buzzer_pocket_diameter = 23;
buzzer_pocket_depth = 4;
buzzer_offset_from_center = 20;

mpu_mount_x = 20;
mpu_mount_y = 15;
mpu_standoff_height = 5;
mpu_offset_from_center = 25;

/* [USB-C Cutout] */
usb_cutout_width = 10;
usb_cutout_height = 5;
usb_cutout_center_height = 8;
usb_cutout_angle = 90;

/* [Wire Channels] */
wire_channel_width = 4;
wire_channel_depth = 3;

/* [Ventilation] */
thermal_vent_width = 3;
thermal_vent_length = 10;
sound_vent_width = 2;
sound_vent_length = 8;

/* [Aesthetics] */
base_detail_count = 4;        // Decorative ridges on base
hexagon_detail_count = 6;     // Forerunner hexagons

/* [Resolution] */
$fn = 120;

// ========================================
// MAIN ASSEMBLY
// ========================================

module bottom_shell_v2() {
    difference() {
        union() {
            // Enhanced shell body with subtle taper
            enhanced_shell_body();

            // Screw bosses with decorative caps
            enhanced_screw_bosses();

            // Component standoffs
            esp32_standoffs();
            button_tower();
            mpu_standoffs();

            // Decorative elements
            base_decorative_ridges();
            forerunner_hexagons();
        }

        // Cutouts
        union() {
            hollow_interior();
            o_ring_groove();
            screw_boss_inserts();

            battery_tray_cutout();
            motor_pocket();
            buzzer_pocket();
            usb_cutout();

            enhanced_thermal_vents();
            enhanced_sound_vents();

            wire_channels();

            esp32_standoff_holes();
            mpu_standoff_holes();
            button_tower_holes();
        }
    }
}

// ========================================
// ENHANCED SHELL BODY
// ========================================

module enhanced_shell_body() {
    difference() {
        // Outer cylinder with subtle taper at top
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
// ENHANCED SCREW BOSSES
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
// COMPONENT MOUNTS
// ========================================

module esp32_standoffs() {
    positions = [
        [esp32_mount_x/2, esp32_mount_y/2],
        [-esp32_mount_x/2, esp32_mount_y/2],
        [esp32_mount_x/2, -esp32_mount_y/2],
        [-esp32_mount_x/2, -esp32_mount_y/2]
    ];

    for (pos = positions) {
        translate([pos[0], pos[1], base_thickness])
            cylinder(h = esp32_standoff_height, d = esp32_standoff_diameter);
    }
}

module esp32_standoff_holes() {
    positions = [
        [esp32_mount_x/2, esp32_mount_y/2],
        [-esp32_mount_x/2, esp32_mount_y/2],
        [esp32_mount_x/2, -esp32_mount_y/2],
        [-esp32_mount_x/2, -esp32_mount_y/2]
    ];

    for (pos = positions) {
        translate([pos[0], pos[1], base_thickness])
            cylinder(h = esp32_standoff_height + 1, d = m2_hole_diameter);
    }
}

module button_tower() {
    translate([0, 0, base_thickness])
        difference() {
            cylinder(h = button_tower_height, d = button_tower_width);
            translate([0, 0, 1])
                cylinder(h = button_tower_height, d = button_tower_width - 4);
        }
}

module button_tower_holes() {
    translate([button_tower_width/4, 0, base_thickness + button_tower_height - 1])
        cylinder(h = 3, d = m2_hole_diameter);
    translate([-button_tower_width/4, 0, base_thickness + button_tower_height - 1])
        cylinder(h = 3, d = m2_hole_diameter);
}

module mpu_standoffs() {
    translate([mpu_offset_from_center, 0, base_thickness]) {
        positions = [
            [mpu_mount_x/2, mpu_mount_y/2],
            [-mpu_mount_x/2, -mpu_mount_y/2]
        ];

        for (pos = positions) {
            translate([pos[0], pos[1], 0])
                cylinder(h = mpu_standoff_height, d = esp32_standoff_diameter);
        }
    }
}

module mpu_standoff_holes() {
    translate([mpu_offset_from_center, 0, base_thickness]) {
        positions = [
            [mpu_mount_x/2, mpu_mount_y/2],
            [-mpu_mount_x/2, -mpu_mount_y/2]
        ];

        for (pos = positions) {
            translate([pos[0], pos[1], 0])
                cylinder(h = mpu_standoff_height + 1, d = m2_hole_diameter);
        }
    }
}

module battery_tray_cutout() {
    tray_z = base_thickness + esp32_standoff_height + 18;

    translate([0, 0, tray_z])
        cube([battery_tray_x, battery_tray_y, battery_tray_depth + 1], center = true);

    // Ventilation slots
    for (i = [0:3]) {
        translate([i * 8 - 12, 0, tray_z - 2])
            cube([3, 15, 3], center = true);
    }
}

module motor_pocket() {
    angle = -90;
    translate([
        motor_offset_from_center * cos(angle),
        motor_offset_from_center * sin(angle),
        base_thickness
    ])
        cylinder(h = motor_pocket_depth + 1, d = motor_pocket_diameter);
}

module buzzer_pocket() {
    angle = 45;
    translate([
        buzzer_offset_from_center * cos(angle),
        buzzer_offset_from_center * sin(angle),
        base_thickness
    ])
        cylinder(h = buzzer_pocket_depth + 1, d = buzzer_pocket_diameter);
}

// ========================================
// USB-C CUTOUT
// ========================================

module usb_cutout() {
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
// ENHANCED VENTILATION
// ========================================

module enhanced_thermal_vents() {
    // 4× Forerunner-style thermal vents
    for (i = [0:3]) {
        angle = i * 90;
        rotate([0, 0, angle])
            translate([15, 0, base_thickness + 2]) {
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
    buzzer_angle = 45;
    for (i = [0:5]) {
        angle = buzzer_angle + (i * 10) - 25;
        rotate([0, 0, angle])
            translate([buzzer_offset_from_center, 0, base_thickness + 10]) {
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
    // Central channel upward
    translate([0, 0, base_thickness + button_tower_height])
        cylinder(h = 20, d = wire_channel_width);

    // To motor
    hull() {
        translate([0, 0, base_thickness + esp32_standoff_height])
            cylinder(h = wire_channel_depth, d = wire_channel_width);
        translate([motor_offset_from_center * cos(-90), motor_offset_from_center * sin(-90), base_thickness])
            cylinder(h = wire_channel_depth, d = wire_channel_width);
    }

    // To buzzer
    hull() {
        translate([0, 0, base_thickness + esp32_standoff_height])
            cylinder(h = wire_channel_depth, d = wire_channel_width);
        translate([buzzer_offset_from_center * cos(45), buzzer_offset_from_center * sin(45), base_thickness])
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
    // Decorative hexagons around perimeter
    for (i = [0:hexagon_detail_count-1]) {
        angle = i * 60;
        rotate([0, 0, angle])
            translate([outer_diameter/2 - 3, 0, total_height/2])
                rotate([90, 0, 0])
                    difference() {
                        cylinder(h = 0.6, d = 4, $fn = 6, center = true);
                        cylinder(h = 0.8, d = 2, $fn = 6, center = true);
                    }
    }
}

// ========================================
// RENDER
// ========================================

bottom_shell_v2();
