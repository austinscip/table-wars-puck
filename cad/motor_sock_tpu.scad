// TABLE WARS - Motor Sock (TPU 95A)
// Friction-fit holder for vibration motor

/* [Dimensions] */
outer_diameter = 12;      // mm
inner_diameter = 10.2;    // mm (tight fit on 10mm motor)
height = 8;               // mm
wall_thickness = 0.8;     // mm (calculated: (12-10.2)/2 = 0.9mm)

/* [Resolution] */
$fn = 100;

module motor_sock() {
    difference() {
        // Outer cylinder
        cylinder(h = height, d = outer_diameter);

        // Inner cavity (open top)
        translate([0, 0, -1])
            cylinder(h = height + 1, d = inner_diameter);
    }
}

motor_sock();
