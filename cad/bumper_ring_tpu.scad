// TABLE WARS - Equator Bumper Ring (TPU 95A)
// Friction-fits into groove around shell seam

/* [Dimensions] */
inner_diameter = 95;      // mm (matches shell diameter)
cross_section = 2;        // mm (square profile: 2×2mm)

/* [Resolution] */
$fn = 200; // Higher resolution for smooth ring

module bumper_ring() {
    // Torus-like ring with square cross-section
    rotate_extrude(convexity = 10)
        translate([inner_diameter/2, 0, 0])
            square([cross_section, cross_section], center = true);
}

bumper_ring();
