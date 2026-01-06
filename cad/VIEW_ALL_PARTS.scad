// Simple viewer for all STL files
$fn = 100;

// Bottom shell - Black
color([0.1, 0.1, 0.1, 1.0])
    import("bottom_shell_petg.stl");

// Top shell - Translucent Blue
color([0.3, 0.5, 0.8, 0.7])
    import("top_shell_petg.stl");

// Button cap - Translucent Blue
translate([0, 0, 44])
    color([0.3, 0.5, 0.8, 0.85])
        import("button_cap_petg.stl");

// Bumper ring - Black
translate([0, 0, 24])
    color([0.05, 0.05, 0.05, 1.0])
        import("bumper_ring_tpu.stl");

// Motor sock - Black (positioned below for visibility)
translate([0, 0, 0])
    color([0.05, 0.05, 0.05, 1.0])
        import("motor_sock_tpu.stl");
