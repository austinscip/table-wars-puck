// TABLE WARS - Product View - WITH LEDs GLOWING
// Shows what the puck looks like when LEDs are ON

/* [Display Options] */
show_top_shell = true;
show_bottom_shell = true;
show_button_cap = true;
show_bumper_ring = true;
show_leds = true;
exploded_view = false;
explosion_distance = 25;

/* [Colors - REALISTIC WITH GLOW] */
top_shell_color = [0.3, 0.5, 0.8, 0.7];      // Translucent blue - lets LED light through
bottom_shell_color = [0.1, 0.1, 0.1, 1.0];   // Solid black PETG
button_cap_color = [0.3, 0.5, 0.8, 0.85];    // Translucent blue
bumper_color = [0.05, 0.05, 0.05, 1.0];      // Black TPU

$fn = 100;

// ========================================
// PRODUCT ASSEMBLY - WITH LED GLOW
// ========================================

module product_view_leds_on() {
    // Bottom shell (solid black)
    if (show_bottom_shell) {
        color(bottom_shell_color)
            import("forerunner_bottom_shell_v3_pcb_PROMINENT.stl");
    }

    // LED ring (16 individual LEDs GLOWING)
    if (show_leds) {
        led_height = 30;  // Height from base where LEDs sit

        for (i = [0:15]) {
            angle = i * (360 / 16);
            rotate([0, 0, angle])
                translate([29, 0, led_height]) {
                    // LED body (orange/amber when on) - realistic WS2812B size
                    color([1, 0.5, 0, 1.0])
                        cube([5, 5, 1.5], center = true);

                    // GLOW effect (subtle, no overlap)
                    translate([0, 0, 0.75])
                        color([1, 0.7, 0.1, 0.5])
                            cube([7, 7, 2], center = true);

                    // Soft glow upward (very transparent)
                    translate([0, 0, 2])
                        color([1, 0.8, 0.3, 0.2])
                            cube([9, 9, 4], center = true);
                }
        }
    }

    // Top shell (MORE translucent to show LED glow)
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

    // Bumper ring (black TPU at seam)
    if (show_bumper_ring) {
        translate([0, 0, 24])
            color(bumper_color)
                import("bumper_ring_tpu.stl");
    }
}

// ========================================
// RENDER
// ========================================

product_view_leds_on();

/*
INSTRUCTIONS:

This shows the puck WITH LEDs POWERED ON:

LED LOCATION:
- 16 LEDs in a circle at 60mm diameter
- Positioned 30mm from base (inside top area)
- Under the translucent blue dome
- Light shines UP and OUT through the dome material

WHAT YOU SEE:
- Orange/amber LED glow visible through translucent dome
- Glowing ring effect around perimeter
- Light diffuses through the dome creating halo effect
- Forerunner aesthetic: "energy ring" appearance

WHEN LEDS ARE OFF:
- See assembled_PRODUCT_VIEW.scad
- Dome looks solid translucent blue
- No glow visible

WHEN LEDS ARE ON (this file):
- Dome glows from inside
- 16-point ring of light visible
- Creates futuristic energy containment look

Press F5 to render and see the LED glow effect!
*/
