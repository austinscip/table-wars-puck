// TABLE WARS - Full Assembly Visualization
// Shows how the puck looks when fully assembled

/* [Display Options] */
show_top_shell = true;
show_bottom_shell = true;
show_button_cap = true;
show_bumper_ring = true;
exploded_view = false;     // Set to true for exploded assembly
explosion_distance = 20;   // mm

/* [Colors] */
top_shell_color = [0.5, 0.7, 1.0, 0.6];      // Translucent blue
bottom_shell_color = [0.3, 0.3, 0.3, 1.0];   // Dark gray
button_cap_color = [0.5, 0.7, 1.0, 0.8];     // Blue
bumper_color = [0.1, 0.1, 0.1, 1.0];         // Black TPU
led_ring_color = [1.0, 1.0, 0.0, 0.8];       // Yellow (LED glow)

/* [Component Visualization] */
show_led_ring = true;
show_internal_components = true;
show_battery = true;
show_esp32 = true;

$fn = 80;

// ========================================
// ASSEMBLY
// ========================================

module full_assembly() {
    // Bottom shell
    if (show_bottom_shell) {
        color(bottom_shell_color)
            import("forerunner_bottom_shell_v2.stl");
    }

    // Top shell (raised if exploded)
    if (show_top_shell) {
        translate([0, 0, exploded_view ? explosion_distance : 0])
            color(top_shell_color)
                import("forerunner_top_shell_v2.stl");
    }

    // Button cap (centered, at top)
    if (show_button_cap) {
        translate([0, 0, exploded_view ? 40 + explosion_distance + 5 : 40])
            color(button_cap_color)
                import("button_glyph_cap_v2.stl");
    }

    // Bumper ring (around equator)
    if (show_bumper_ring) {
        translate([0, 0, 24])  // Seam height
            color(bumper_color)
                import("bumper_ring_tpu.stl");
    }

    // Internal components (representations)
    if (show_internal_components && !exploded_view) {
        internal_components();
    }
}

// ========================================
// INTERNAL COMPONENTS (VISUALIZATION)
// ========================================

module internal_components() {
    // LED Ring (in top shell)
    if (show_led_ring) {
        translate([0, 0, 28])  // Near top interior
            color(led_ring_color, 0.9)
                difference() {
                    cylinder(h = 2, d = 60);
                    cylinder(h = 3, d = 50);
                }
    }

    // ESP32 DevKitC representation
    if (show_esp32) {
        translate([0, 0, 9])
            color([0.0, 0.3, 0.0], 0.9)  // Green PCB
                cube([56, 28, 1], center = true);

        // USB connector
        translate([28, 0, 9])
            color([0.8, 0.8, 0.8], 0.9)  // Silver
                cube([8, 8, 3], center = true);

        // Components on top
        translate([0, 0, 10])
            color([0.1, 0.1, 0.1], 0.9)  // Black
                cube([50, 20, 12], center = true);
    }

    // Battery representation
    if (show_battery) {
        translate([0, 0, 26])
            color([0.2, 0.2, 0.8], 0.7)  // Blue LiPo
                cube([60, 35, 8], center = true);
    }

    // MPU6050 (offset from center - THE PROBLEM!)
    translate([25, 0, 8])
        color([0.5, 0.0, 0.5], 0.9)  // Purple
            cube([20, 15, 2], center = true);

    // Motor (coin shape)
    translate([0, -30, 6])
        color([0.7, 0.7, 0.7], 0.9)  // Silver
            cylinder(h = 3, d = 10);

    // Buzzer
    translate([14, 14, 6])
        color([0.0, 0.0, 0.0], 0.9)  // Black
            cylinder(h = 4, d = 12);

    // Button tower (center)
    translate([0, 0, 8])
        color([0.8, 0.8, 0.8], 0.7)  // Light gray
            cylinder(h = 10, d = 20);
}

// ========================================
// ANNOTATIONS (FOR DOCUMENTATION)
// ========================================

module add_labels() {
    // Add text labels pointing to components
    // (OpenSCAD text() requires font, simplified here)

    // LED Ring label
    if (show_led_ring) {
        translate([35, 0, 28])
            color([1, 1, 1])
                cube([2, 20, 1], center = true);  // Pointer line
    }
}

// ========================================
// CROSS-SECTION VIEW
// ========================================

module cross_section_view() {
    difference() {
        full_assembly();

        // Cut away half to show interior
        translate([50, 0, 0])
            cube([100, 200, 100], center = true);
    }

    // Add labels in cross-section
    if (show_internal_components) {
        // Component labels would go here
    }
}

// ========================================
// RENDER
// ========================================

// Choose view mode:
// 1. Full assembly
full_assembly();

// 2. Exploded view (uncomment this, comment above)
// exploded_view = true;
// full_assembly();

// 3. Cross-section (uncomment this, comment above)
// cross_section_view();


// ========================================
// INSTRUCTIONS
// ========================================

/*
HOW TO USE:

1. NORMAL ASSEMBLED VIEW:
   - Keep as-is above
   - Renders: Top + bottom shells together
   - Shows button cap, bumper ring
   - Shows internal components (semi-transparent)

2. EXPLODED VIEW:
   - Change: exploded_view = true; (at top)
   - OR uncomment the exploded section above
   - Shows: Components separated vertically

3. CROSS-SECTION:
   - Uncomment: cross_section_view();
   - Comment out: full_assembly();
   - Shows: Interior visible (half cut away)

4. COMPONENT VISIBILITY:
   - Toggle at top:
     show_led_ring = true/false;
     show_battery = true/false;
     show_esp32 = true/false;
   - Shows/hides internal parts

5. EXPORT:
   - Render (F6)
   - File → Export → Export as STL
   - Save as: assembled_puck.stl

COLOR CODES:
- Blue translucent: Top shell
- Dark gray: Bottom shell
- Black: TPU bumper
- Yellow: LED ring (glowing)
- Green: ESP32 PCB
- Blue: LiPo battery
- Purple: MPU6050 sensor
- Silver: Motor, USB connectors
*/
