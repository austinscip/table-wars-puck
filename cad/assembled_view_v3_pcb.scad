// TABLE WARS - Full Assembly V3 - CUSTOM PCB VERSION
// Shows professional PCB-based design with centered MPU6050

/* [Display Options] */
show_top_shell = true;
show_bottom_shell = true;
show_button_cap = true;
show_bumper_ring = true;
show_pcb = true;
exploded_view = false;
explosion_distance = 25;

/* [Colors] */
top_shell_color = [0.4, 0.6, 0.9, 0.6];      // Translucent blue - show details
bottom_shell_color = [0.15, 0.15, 0.15, 1.0]; // Dark gray/black
button_cap_color = [0.5, 0.7, 1.0, 0.85];
bumper_color = [0.05, 0.05, 0.05, 1.0];      // Black
pcb_color = [0.0, 0.5, 0.0, 0.4];            // Green PCB - transparent
led_ring_color = [1.0, 1.0, 0.0, 0.9];
component_color = [0.1, 0.1, 0.1, 0.5];

$fn = 100;

// ========================================
// ASSEMBLY
// ========================================

module full_assembly_v3() {
    // Bottom shell (import PROMINENT version to show hexagons)
    if (show_bottom_shell) {
        color(bottom_shell_color)
            import("forerunner_bottom_shell_v3_pcb_PROMINENT.stl");
    }

    // Top shell (import SCAD directly to show prominent details)
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

    // Bumper ring
    if (show_bumper_ring) {
        translate([0, 0, 24])
            color(bumper_color)
                import("bumper_ring_tpu.stl");
    }

    // Custom PCB with components
    if (show_pcb && !exploded_view) {
        custom_pcb_assembly();
    }
}

// ========================================
// CUSTOM PCB ASSEMBLY
// ========================================

module custom_pcb_assembly() {
    pcb_z = 2.5 + 6;  // Base + standoff height

    // Main PCB (89mm circular)
    translate([0, 0, pcb_z])
        color(pcb_color)
            difference() {
                cylinder(h = 1.6, d = 89);  // Standard PCB thickness

                // Center hole for button/MPU access
                cylinder(h = 2, d = 15);

                // Mounting holes
                for (i = [0:5]) {
                    rotate([0, 0, i * 60])
                        translate([38, 0, 0])
                            cylinder(h = 2, d = 2.7);
                }
            }

    // Components on PCB

    // MPU6050 - CENTERED! (The key improvement) - small chip at center
    translate([0, 0, pcb_z + 1.6])
        color([0.2, 0.2, 0.2], 0.6) {
            cube([8, 6, 1], center = true);
        }

    // ESP32 chip (not module!)
    translate([20, 10, pcb_z + 1.6])
        color(component_color)
            cube([10, 10, 1], center = true);

    // TP4057 charger IC
    translate([25, -8, pcb_z + 1.6])
        color(component_color)
            cube([4, 4, 0.8], center = true);

    // MT3608 boost converter
    translate([-20, -8, pcb_z + 1.6])
        color(component_color)
            cube([5, 5, 1.5], center = true);

    // Motor (small)
    translate([0, -22, pcb_z + 1.6])
        color([0.6, 0.6, 0.6])
            cylinder(h = 2, d = 6);

    // Buzzer (small)
    translate([15, -15, pcb_z + 1.6])
        color(component_color)
            cylinder(h = 1.5, d = 8);

    // Battery above PCB (smaller, more transparent so LEDs visible)
    translate([0, 0, pcb_z + 12])
        color([0.2, 0.2, 0.8], 0.2)
            cube([50, 30, 6], center = true);

    // LED ring (16 individual WS2812B LEDs in circle) - BRIGHT AND VISIBLE
    for (i = [0:15]) {
        angle = i * (360 / 16);
        rotate([0, 0, angle])
            translate([29, 0, pcb_z + 22])
                color([1, 0.6, 0, 1.0]) {
                    // LED body
                    cube([5, 5, 2], center = true);
                    // Glow effect
                    translate([0, 0, 1])
                        color([1, 1, 0, 0.3])
                            cube([7, 7, 1], center = true);
                }
    }

    // Tactile button on PCB (center) - extends through top shell
    translate([0, 0, pcb_z + 1.6])
        color([0.8, 0.8, 0.8]) {
            // Button base
            cylinder(h = 5, d = 6);
            // Button stem (goes through PCB hole and top shell)
            translate([0, 0, 5])
                cylinder(h = 25, d = 3.5);
            // Button top (contacts button cap)
            translate([0, 0, 30])
                cylinder(h = 2, d = 5);
        }
}

// ========================================
// CROSS-SECTION VIEW
// ========================================

module cross_section_view() {
    difference() {
        full_assembly_v3();

        // Cut away half
        translate([50, 0, 0])
            cube([100, 200, 100], center = true);
    }

    // Add annotation labels
    if (show_pcb) {
        pcb_z = 8.5;

        // MPU6050 CENTERED label
        translate([-45, 0, pcb_z + 2])
            color([1, 0, 0])
                rotate([0, 0, 0])
                    linear_extrude(0.5)
                        text("MPU CENTERED!", size = 3, halign = "left");

        // PCB label
        translate([-45, 0, pcb_z])
            color([0, 1, 0])
                linear_extrude(0.5)
                    text("Custom PCB (89mm)", size = 2.5, halign = "left");
    }
}

// ========================================
// RENDER
// ========================================

// Normal assembled view
full_assembly_v3();

// Exploded view (uncomment to use)
// exploded_view = true;
// full_assembly_v3();

// Cross-section (uncomment to use)
// cross_section_view();

/*
INSTRUCTIONS:

NORMAL VIEW (current):
- Shows complete puck assembly
- Custom PCB visible through translucent top
- MPU6050 at EXACT CENTER (purple component)

EXPLODED VIEW:
- Set: exploded_view = true; (line 10)
- Shows components separated vertically

CROSS-SECTION:
- Uncomment: cross_section_view();
- Comment: full_assembly_v3();
- Shows interior with labels

KEY IMPROVEMENTS V3:
✓ Custom 89mm circular PCB
✓ MPU6050 CENTERED (no offset!)
✓ Professional component layout
✓ Matches Sid's technical spec
✓ Battery clearance fixed (lowered 3mm)
✓ Optimized for precision + shake/tap games

COMPARE TO V2:
- V2: MPU offset 25mm (amateur)
- V3: MPU centered (professional)
*/
