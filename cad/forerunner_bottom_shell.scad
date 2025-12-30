// TABLE WARS - Forerunner Gaming Puck - Bottom Shell
// Generated CAD file - all dimensions from ENCLOSURE_SPEC.md v2.0
// Use OpenSCAD to render and export to STL

/* [Main Dimensions] */
outer_diameter = 95;          // mm
wall_thickness = 3.5;         // mm
internal_height = 32;         // mm
total_height = 40;            // mm
base_thickness = 2.5;         // mm

/* [Screw Bosses - M3] */
num_screw_bosses = 6;
screw_boss_diameter = 7;      // mm
screw_boss_height = 35;       // Total height to top rim
m3_insert_diameter = 4.2;     // mm (for M3×4mm brass insert)
m3_insert_depth = 5;          // mm
screw_positions_radius = 40;  // mm from center

/* [O-Ring Groove] */
o_ring_groove_width = 2;      // mm
o_ring_groove_depth = 2;      // mm
o_ring_groove_id = 89;        // mm (90mm O-ring - 1mm clearance)

/* [Alignment Features] */
alignment_lip_height = 3;     // mm
alignment_lip_width = 2;      // mm

/* [Component Mounts - ESP32] */
esp32_mount_x = 56;           // mm spacing
esp32_mount_y = 28;           // mm spacing
esp32_standoff_height = 6;    // mm from base
esp32_standoff_diameter = 5;  // mm
m2_hole_diameter = 2.2;       // mm (for M2 screws)

/* [Component Mounts - Button] */
button_tower_width = 20;      // mm
button_tower_height = 10;     // mm from base

/* [Component Mounts - Battery] */
battery_tray_x = 62;          // mm
battery_tray_y = 37;          // mm
battery_tray_depth = 9;       // mm
battery_tray_floor_thickness = 2; // mm

/* [Component Mounts - Motor] */
motor_pocket_diameter = 12.5; // mm
motor_pocket_depth = 8;       // mm
motor_offset_from_center = 30; // mm

/* [Component Mounts - Buzzer] */
buzzer_pocket_diameter = 23;  // mm
buzzer_pocket_depth = 4;      // mm
buzzer_offset_from_center = 20; // mm

/* [Component Mounts - MPU6050] */
mpu_mount_x = 20;             // mm spacing
mpu_mount_y = 15;             // mm spacing
mpu_standoff_height = 5;      // mm from base
mpu_offset_from_center = 25;  // mm

/* [USB-C Cutout - TP4057] */
usb_cutout_width = 10;        // mm
usb_cutout_height = 5;        // mm
usb_cutout_center_height = 8; // mm from base
usb_cutout_angle = 90;        // degrees (position around rim)

/* [Wire Channels] */
wire_channel_width = 4;       // mm
wire_channel_depth = 3;       // mm

/* [Ventilation] */
thermal_vent_width = 3;       // mm
thermal_vent_length = 10;     // mm
sound_vent_width = 2;         // mm
sound_vent_length = 8;        // mm

/* [Zip-Tie Anchors] */
zip_tie_post_diameter = 2;    // mm
zip_tie_post_height = 4;      // mm

/* [Resolution] */
$fn = 100; // Circle resolution - increase for smoother output

// ========================================
// MAIN ASSEMBLY
// ========================================

module bottom_shell() {
    difference() {
        union() {
            // Main shell body
            main_shell_body();

            // Screw bosses
            screw_bosses();

            // Component standoffs and mounts
            esp32_standoffs();
            button_tower();
            mpu_standoffs();

            // Zip-tie anchor posts
            zip_tie_anchors();
        }

        // Hollowing and features
        union() {
            // Hollow interior
            hollow_interior();

            // O-ring groove
            o_ring_groove();

            // Brass insert holes in screw bosses
            screw_boss_inserts();

            // Component pockets
            battery_tray_cutout();
            motor_pocket();
            buzzer_pocket();

            // USB-C cutout
            usb_cutout();

            // Ventilation vents
            thermal_vents();
            sound_vents();

            // Wire routing channels
            wire_channels();

            // M2 holes in standoffs
            esp32_standoff_holes();
            mpu_standoff_holes();
            button_tower_holes();
        }
    }
}

// ========================================
// SHELL BODY
// ========================================

module main_shell_body() {
    difference() {
        // Outer cylinder
        cylinder(h = total_height, d = outer_diameter);

        // Remove top to create open shell
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
// SCREW BOSSES
// ========================================

module screw_bosses() {
    for (i = [0:num_screw_bosses-1]) {
        angle = i * (360 / num_screw_bosses);
        rotate([0, 0, angle])
            translate([screw_positions_radius, 0, 0])
                cylinder(h = screw_boss_height, d = screw_boss_diameter);
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
// ESP32 STANDOFFS
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

// ========================================
// BUTTON TOWER (CENTER)
// ========================================

module button_tower() {
    translate([0, 0, base_thickness])
        difference() {
            cube([button_tower_width, button_tower_width, button_tower_height], center = true);
            // Hollow for wiring
            translate([0, 0, 1])
                cube([button_tower_width - 4, button_tower_width - 4, button_tower_height], center = true);
        }
}

module button_tower_holes() {
    // Two M2 holes on top surface for button PCB
    translate([button_tower_width/4, 0, base_thickness + button_tower_height - 1])
        cylinder(h = 3, d = m2_hole_diameter);
    translate([-button_tower_width/4, 0, base_thickness + button_tower_height - 1])
        cylinder(h = 3, d = m2_hole_diameter);
}

// ========================================
// MPU6050 STANDOFFS
// ========================================

module mpu_standoffs() {
    // Position MPU6050 offset from center
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

// ========================================
// BATTERY TRAY
// ========================================

module battery_tray_cutout() {
    // Above ESP32, recessed pocket
    tray_z = base_thickness + esp32_standoff_height + 15 + 3; // 3mm clearance above ESP32

    translate([0, 0, tray_z])
        cube([battery_tray_x, battery_tray_y, battery_tray_depth + 1], center = true);

    // Ventilation slots under tray
    for (i = [0:3]) {
        translate([i * 8 - 12, 0, tray_z - battery_tray_floor_thickness])
            cube([3, 15, battery_tray_floor_thickness + 1], center = true);
    }
}

// ========================================
// MOTOR POCKET
// ========================================

module motor_pocket() {
    // Position near edge, opposite MPU6050
    angle = -90; // Opposite side from MPU
    translate([
        motor_offset_from_center * cos(angle),
        motor_offset_from_center * sin(angle),
        base_thickness
    ])
        cylinder(h = motor_pocket_depth + 1, d = motor_pocket_diameter);
}

// ========================================
// BUZZER POCKET
// ========================================

module buzzer_pocket() {
    angle = 45; // Different position
    translate([
        buzzer_offset_from_center * cos(angle),
        buzzer_offset_from_center * sin(angle),
        base_thickness
    ])
        cylinder(h = buzzer_pocket_depth + 1, d = buzzer_pocket_diameter);
}

// ========================================
// USB-C CUTOUT (TP4057)
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

module thermal_vents() {
    // 4× thermal vents near ESP32, 90° spacing
    for (i = [0:3]) {
        angle = i * 90;
        rotate([0, 0, angle])
            translate([15, 0, base_thickness + 2])
                cube([thermal_vent_width, thermal_vent_length, 10], center = true);
    }
}

module sound_vents() {
    // 6× sound vents above buzzer
    buzzer_angle = 45;
    for (i = [0:5]) {
        angle = buzzer_angle + (i * 10) - 25;
        rotate([0, 0, angle])
            translate([buzzer_offset_from_center, 0, base_thickness + 10])
                cube([sound_vent_width, sound_vent_length, 8], center = true);
    }
}

// ========================================
// WIRE CHANNELS
// ========================================

module wire_channels() {
    // Star pattern from ESP32 to all components
    // Simplified - main channels only

    // Channel to LED ring (center upward)
    translate([0, 0, base_thickness + button_tower_height])
        cylinder(h = 20, d = wire_channel_width);

    // Channel from ESP32 to motor
    hull() {
        translate([0, 0, base_thickness + esp32_standoff_height])
            cylinder(h = wire_channel_depth, d = wire_channel_width);
        translate([motor_offset_from_center * cos(-90), motor_offset_from_center * sin(-90), base_thickness])
            cylinder(h = wire_channel_depth, d = wire_channel_width);
    }

    // Channel from ESP32 to buzzer
    hull() {
        translate([0, 0, base_thickness + esp32_standoff_height])
            cylinder(h = wire_channel_depth, d = wire_channel_width);
        translate([buzzer_offset_from_center * cos(45), buzzer_offset_from_center * sin(45), base_thickness])
            cylinder(h = wire_channel_depth, d = wire_channel_width);
    }
}

// ========================================
// ZIP-TIE ANCHORS
// ========================================

module zip_tie_anchors() {
    // 6× anchor posts at key locations
    positions = [
        [0, 35, 20],          // Near LED ring path
        [20, 15, 10],         // Near ESP32
        [-20, 15, 10],        // Near ESP32
        [0, -30, 8],          // Near battery
        [motor_offset_from_center * cos(-90), motor_offset_from_center * sin(-90), 8], // Near motor
        [buzzer_offset_from_center * cos(45), buzzer_offset_from_center * sin(45), 8]  // Near buzzer
    ];

    for (pos = positions) {
        translate([pos[0], pos[1], pos[2]])
            cylinder(h = zip_tie_post_height, d = zip_tie_post_diameter);
    }
}

// ========================================
// RENDER
// ========================================

bottom_shell();
