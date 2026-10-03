// Basic electronics enclosure experiment. All dimensions are in millimeters.
// Concept only: no actual PCB, connector, or fastener has been selected.

// --- Main dimensions ---
outer_length = 60;
outer_width = 40;
outer_height = 15;             // Total height with the lid assembled.
wall_thickness = 2;
floor_thickness = 2;           // ASSUMPTION: same thickness as the walls.
corner_radius = 4;             // ASSUMPTION: exterior corner radius in plan view.
lid_thickness = 2;             // ASSUMPTION: flat removable top plate.

// --- Lid fit: a small locating rim slips inside the base ---
lid_lip_height = 2;            // ASSUMPTION: depth of the locating rim.
lid_lip_thickness = 1.2;       // ASSUMPTION: thickness of the rim.
lid_clearance = 0.25;          // ASSUMPTION: gap on EACH side; tune for printing.
// The lid rests on the walls. No latch or lid screws in this first experiment.

// --- Four placeholder PCB mounting posts ---
post_diameter = 5;             // ASSUMPTION: simple cylindrical posts.
post_height = 6;               // ASSUMPTION: measured upward from the floor.
post_hole_diameter = 2;        // ASSUMPTION: pilot holes; not a specified screw fit.
post_inset = 5;                // ASSUMPTION: post center to each inner wall.
// Holes stop at the floor, so they do not pierce the bottom of the enclosure.

// --- Placeholder USB-C opening, centered on the +Y side ---
port_width = 10;               // ASSUMPTION: rectangular clearance, not a USB-C spec.
port_height = 4;
port_center_height = 7;        // ASSUMPTION: center measured from outside bottom.

// --- Display settings ---
show_lid = true;
lid_separated = true;          // Set false to see the assembled 60 x 40 x 15 box.
lid_display_gap = 8;           // Space between parts when displayed side by side.
$fn = 48;                     // Smoothness of circles and rounded corners.
epsilon = 0.01;                // Tiny overlap to make Boolean cuts reliable.

// Derived dimensions update automatically when you change the variables above.
base_height = outer_height - lid_thickness;
inner_length = outer_length - 2 * wall_thickness;
inner_width = outer_width - 2 * wall_thickness;
inner_radius = corner_radius - wall_thickness;
lip_length = inner_length - 2 * lid_clearance;
lip_width = inner_width - 2 * lid_clearance;
lip_radius = inner_radius - lid_clearance;
post_x = inner_length / 2 - post_inset;
post_y = inner_width / 2 - post_inset;

// Keep the simple geometry in a sensible range while experimenting.
assert(corner_radius > wall_thickness + lid_clearance,
       "Increase corner_radius, or reduce wall_thickness / lid_clearance.");
assert(lip_radius > lid_lip_thickness,
       "The lid rim needs a larger corner radius or a thinner lip.");
assert(base_height > floor_thickness + post_height + lid_lip_height,
       "Increase outer_height or reduce the floor, posts, or lid lip.");
assert(port_center_height - port_height / 2 > floor_thickness &&
       port_center_height + port_height / 2 < base_height,
       "Keep the port opening above the floor and below the top edge.");

// A rounded rectangle made by joining four circles, then extruding upward.
// X is length, Y is width, and Z is height. Corners are rounded in plan view;
// the top and bottom edges remain square to keep this first model simple.
module rounded_prism(length, width, height, radius) {
    linear_extrude(height = height)
        hull()
            for (x = [-1, 1], y = [-1, 1])
                translate([x * (length / 2 - radius),
                           y * (width / 2 - radius)])
                    circle(r = radius);
}

// --- Base: subtract a cavity and a side opening from the outer shell ---
module enclosure_base() {
    union() {
        difference() {
            rounded_prism(outer_length, outer_width, base_height, corner_radius);

            // Cut through the top, leaving the floor and 2 mm side walls.
            translate([0, 0, floor_thickness])
                rounded_prism(inner_length, inner_width,
                              base_height - floor_thickness + epsilon,
                              inner_radius);

            // Cut a rectangle through only the +Y wall.
            translate([-port_width / 2,
                       outer_width / 2 - wall_thickness - epsilon,
                       port_center_height - port_height / 2])
                cube([port_width, wall_thickness + 2 * epsilon, port_height]);
        }

        // Four posts join the floor. Each has a simple blind pilot hole.
        for (x = [-post_x, post_x], y = [-post_y, post_y])
            translate([x, y, floor_thickness - epsilon])
                difference() {
                    cylinder(h = post_height + epsilon, d = post_diameter);
                    translate([0, 0, epsilon])
                        cylinder(h = post_height + epsilon,
                                 d = post_hole_diameter);
                }
    }
}

// --- Lid: flat top plate plus a hollow locating rim underneath ---
// Local Z=0 is the underside of the plate; the rim extends downward.
module enclosure_lid() {
    union() {
        rounded_prism(outer_length, outer_width, lid_thickness, corner_radius);
        translate([0, 0, -lid_lip_height])
            difference() {
                rounded_prism(lip_length, lip_width,
                              lid_lip_height + epsilon, lip_radius);
                translate([0, 0, -epsilon])
                    rounded_prism(lip_length - 2 * lid_lip_thickness,
                                  lip_width - 2 * lid_lip_thickness,
                                  lid_lip_height + 3 * epsilon,
                                  lip_radius - lid_lip_thickness);
            }
    }
}

// --- Preview: show both parts beside each other, or assembled ---
enclosure_base();
if (show_lid)
    translate(lid_separated
              ? [0, outer_width + lid_display_gap, lid_lip_height]
              : [0, 0, base_height])
        enclosure_lid();
