// V2 conceptual knee / upper-shin sensor. Units: mm. Not hardware-ready.
// X: across the leg / strap direction; Y: along the leg; Z: away from skin.
// The rear is the TOP of a cylinder centered at Z=-body_radius, not a dome.
// Default view separates the cover so the cavity and its locating rim are visible.

// --- Overall housing dimensions (ASSUMPTIONS: unknown electronics) ---
housing_width = 60;
housing_height = 46;
front_z = 12.5;                // Front measured from the rear's CENTER at Z=0.
maximum_housing_depth = 18;    // Includes the rear sag at the housing edges.
housing_corner_radius = 11;
lid_thickness = 1.8;
front_edge_bevel = 0.8;        // Small bevel around the front cover perimeter.

// --- Wall thickness ---
wall_thickness = 2.2;
rear_thickness = 2.4;          // Radial thickness, using concentric cylinders.
minimum_feature_web = 2.4;     // Minimum checked material at slot ends / roots.

// --- Body curvature (ASSUMPTIONS: generic leg, not an anatomical fit) ---
body_radius = 110;             // Larger radius = flatter rear and wings.
wing_reach = 20;               // Extension beyond each side of the housing.
wing_root_overlap = 2;         // Positive overlap with the housing side wall.
wing_height = 34;
wing_thickness = 4.4;          // Radial thickness; wings use the same rear curve.
wing_corner_radius = 5;

// --- Strap dimensions (ASSUMPTIONS: 25 mm elastic, about 2 mm thick) ---
strap_width = 25;
strap_width_allowance = 2;
strap_thickness = 2;
strap_thickness_allowance = 2;
slot_end_web = 6.5;            // Approximate outer-end material beyond the slot.
slot_edge_bevel = 0.6;         // Eases both slot mouths; plan edges are round.

// --- PCB mounting dimensions (ALL placeholder assumptions) ---
pcb_width = 38;
pcb_height = 26;
pcb_thickness = 1.6;
pcb_component_height = 1.8;    // Above PCB; no tall connector/battery modeled.
pcb_hole_spacing_x = 32;
pcb_hole_spacing_y = 20;
post_diameter = 5.4;
post_top_z = 6.2;              // All four tops level despite the curved floor.
post_hole_diameter = 2;        // Blind pilot holes; no fastener specification.
post_hole_floor_skin = 1;      // Material under each pilot hole above inner floor.
component_clearance = 0.8;     // Required vertical gap to cover underside.
internal_edge_clearance = 0.8; // PCB / posts to locating rim.

// --- Lid clearance / locating rim (ASSUMPTIONS: tune after test prints) ---
lid_clearance = 0.4;           // PER SIDE, not total width difference.
lid_lip_depth = 2.4;
lid_lip_thickness = 1.4;
opening_lip_gap = 0.8;
// Slip-in rim locates the cover; retention is deliberately unresolved in V2.

// --- Openings (ASSUMPTIONS: not actual USB-C or LED hardware dimensions) ---
usb_width = 10;
usb_height = 3.4;
usb_corner_radius = 0.6;
usb_center_z = 5.7;            // Centered in X, on the +Y wall between posts.
led_diameter = 3;
led_x = 0;
led_y = -8;                   // Through cover only, above the future PCB.

// --- Display / tessellation ---
view = "separated";           // "separated", "assembled", "base", or "lid".
show_pcb_envelope = false;     // Translucent PREVIEW ONLY; excluded from exports.
display_gap = 12;
curve_segments = 180;         // Finer cylinder mesh keeps the rear smooth.
detail_segments = 48;
epsilon = 0.02;               // Boolean overlap, not a fit clearance.
cut_margin = 1;               // Cutters extend beyond surfaces.
$fn = detail_segments;

// --- Derived geometry: do not normally edit these ---
base_top = front_z - lid_thickness;
inner_width = housing_width - 2 * wall_thickness;
inner_height = housing_height - 2 * wall_thickness;
inner_radius = housing_corner_radius - wall_thickness;
lip_width = inner_width - 2 * lid_clearance;
lip_height = inner_height - 2 * lid_clearance;
lip_radius = inner_radius - lid_clearance;
rim_inside_width = lip_width - 2 * lid_lip_thickness;
rim_inside_height = lip_height - 2 * lid_lip_thickness;
rim_inside_radius = lip_radius - lid_lip_thickness;
wing_outer_x = housing_width / 2 + wing_reach;
wing_root_x = housing_width / 2 - wing_root_overlap;
wing_width = wing_outer_x - wing_root_x;
wing_center_x = (wing_outer_x + wing_root_x) / 2;
slot_length = strap_width + strap_width_allowance;
slot_width = strap_thickness + strap_thickness_allowance;
slot_center_x = wing_outer_x - slot_end_web - slot_width / 2;
slot_angle = asin(slot_center_x / body_radius);
post_r = post_diameter / 2;
post_x = pcb_hole_spacing_x / 2;
post_y = pcb_hole_spacing_y / 2;
rear_min_z = sqrt(body_radius * body_radius - wing_outer_x * wing_outer_x)
             - body_radius;
blank_bottom = rear_min_z - cut_margin;
blank_height = front_z - blank_bottom + cut_margin;
pcb_top_z = post_top_z + pcb_thickness + pcb_component_height;

function rear_z(x, radial_offset = 0) =
    sqrt(pow(body_radius + radial_offset, 2) - x * x) - body_radius;

// Signed distance to a rounded rectangle: negative means inside.
// Useful for checking corners, where separate X/Y checks are insufficient.
function rounded_distance(x, y, w, h, r) =
    let(qx = abs(x) - (w / 2 - r), qy = abs(y) - (h / 2 - r))
    sqrt(pow(max(qx, 0), 2) + pow(max(qy, 0), 2))
    + min(max(qx, qy), 0) - r;

// --- Parameter checks: reject impossible combinations rather than hiding them ---
assert(body_radius > wing_outer_x, "Body radius must exceed full half-span.");
assert(front_z - rear_z(housing_width / 2) <= maximum_housing_depth,
       "Housing exceeds depth limit; flatten curvature or lower front_z.");
assert(housing_corner_radius < min(housing_width, housing_height) / 2 &&
       rim_inside_radius > 0, "Invalid housing / rim corner radii.");
assert(front_edge_bevel > 0 && front_edge_bevel < lid_thickness,
       "Cover bevel must fit within lid thickness.");
assert(wall_thickness >= 2 && rear_thickness >= 2 &&
       lid_clearance >= 0.3 && lid_clearance <= 0.5,
       "Use sensible shell thicknesses and 0.3-0.5 mm mating clearance.");
assert(wing_root_overlap > 0 && wing_root_overlap < wall_thickness,
       "Wings must overlap side walls without entering the electronics cavity.");
assert(wing_corner_radius < min(wing_width, wing_height) / 2 &&
       wing_thickness >= rear_thickness,
       "Invalid wing corner radius or thickness.");
assert(rounded_distance(wing_root_x, wing_height / 2 - wing_corner_radius,
                        housing_width, housing_height, housing_corner_radius) < 0,
       "Rounded wing roots must overlap the housing footprint.");
assert((wing_height - slot_length) / 2 - slot_edge_bevel >= minimum_feature_web,
       "Too little wing material at the slot ends.");
assert(slot_end_web - slot_edge_bevel >= minimum_feature_web &&
       slot_center_x - slot_width / 2 - slot_edge_bevel - wing_root_x
       >= minimum_feature_web && 2 * slot_edge_bevel < wing_thickness,
       "Slot bevels leave too little wing material.");
// Conservative slot bounds include its radial tilt and both mouth bevels.
assert(rounded_distance(
           (body_radius + wing_thickness) * sin(slot_angle)
           + (slot_width / 2 + slot_edge_bevel + epsilon) * cos(slot_angle)
           - wing_center_x,
           slot_length / 2 + slot_edge_bevel + epsilon,
           wing_width, wing_height, wing_corner_radius)
       <= -minimum_feature_web,
       "Tilted slot approaches the rounded outer wing corner too closely.");
assert(rounded_distance(post_x, post_y, rim_inside_width, rim_inside_height,
                        rim_inside_radius) + post_r + internal_edge_clearance < 0,
       "Posts collide with the wall or lid rim.");
assert(rounded_distance(pcb_width / 2, pcb_height / 2,
                        rim_inside_width, rim_inside_height, rim_inside_radius)
       + internal_edge_clearance < 0, "PCB envelope collides with the lid rim.");
assert(post_x + post_r <= pcb_width / 2 && post_y + post_r <= pcb_height / 2 &&
       post_hole_diameter < post_diameter && post_x > post_r && post_y > post_r,
       "Posts must be distinct and support the placeholder PCB.");
assert(post_top_z > rear_z(max(post_x - post_r, 0), rear_thickness)
                         + post_hole_floor_skin + epsilon &&
       pcb_top_z + component_clearance <= base_top,
       "Posts or components do not fit beneath the cover.");
assert(usb_center_z - usb_height / 2 >= rear_thickness + opening_lip_gap &&
       usb_center_z + usb_height / 2 + opening_lip_gap <= base_top - lid_lip_depth,
       "USB opening collides with floor or locating rim.");
assert(usb_width / 2 + post_r + internal_edge_clearance < post_x &&
       usb_width / 2 < housing_width / 2 - housing_corner_radius &&
       usb_corner_radius < min(usb_width, usb_height) / 2,
       "USB opening is too wide or too close to mounting posts / corners.");
assert(rounded_distance(led_x, led_y, rim_inside_width, rim_inside_height,
                        rim_inside_radius) + led_diameter / 2 < 0,
       "LED opening collides with the cover rim.");
assert(view == "separated" || view == "assembled" || view == "base" || view == "lid",
       "Unknown view setting.");

// Rounded 2D outlines are reused for shell, cavity, lid, wings, and slots.
module rounded_outline(w, h, r) {
    hull()
        for (x = [-1, 1], y = [-1, 1])
            translate([x * (w / 2 - r), y * (h / 2 - r)]) circle(r = r);
}
module prism(w, h, r, bottom, height) {
    translate([0, 0, bottom])
        linear_extrude(height = height) rounded_outline(w, h, r);
}

// Cylinder axis runs along Y. Two concentric radii give a constant radial floor.
module body_cylinder(radial_offset = 0) {
    // Restrict the cylinder cutter to the working region around the parts.
    intersection() {
        translate([-wing_outer_x - cut_margin, -housing_height / 2 - cut_margin,
                   blank_bottom - cut_margin])
            cube([2 * (wing_outer_x + cut_margin),
                  housing_height + 2 * cut_margin, blank_height + 2 * cut_margin]);
        translate([0, 0, -body_radius]) rotate([90, 0, 0])
            cylinder(r = body_radius + radial_offset,
                     h = housing_height + 2 * cut_margin, center = true,
                     $fn = curve_segments);
    }
}

// The cavity is ONLY inside the central housing and ABOVE the curved inner floor.
module cavity() {
    difference() {
        prism(inner_width, inner_height, inner_radius, blank_bottom, blank_height);
        body_cylinder(rear_thickness);
    }
}

// Wing shell follows the same concentric-cylinder construction as the rear.
module wing(side) {
    difference() {
        intersection() {
            translate([side * wing_center_x, 0, 0])
                prism(wing_width, wing_height, wing_corner_radius,
                      blank_bottom, blank_height);
            body_cylinder(wing_thickness);
        }
        body_cylinder();
    }
}

// Slot is a capsule, aimed along the local radial direction, with beveled mouths.
// The tangent-plane bevel approximates the curved surface (not a true fillet).
module strap_slot(side) {
    translate([side * (body_radius + wing_thickness / 2) * sin(slot_angle), 0,
               -body_radius + (body_radius + wing_thickness / 2) * cos(slot_angle)])
        rotate([0, side * slot_angle, 0]) {
            prism(slot_width, slot_length, slot_width / 2,
                  -wing_thickness / 2 - cut_margin, wing_thickness + 2 * cut_margin);
            for (mouth = [-1, 1])
                hull() {
                    prism(slot_width, slot_length, slot_width / 2,
                          mouth * (wing_thickness / 2 - slot_edge_bevel), epsilon);
                    prism(slot_width + 2 * (slot_edge_bevel + cut_margin),
                          slot_length + 2 * (slot_edge_bevel + cut_margin),
                          slot_width / 2 + slot_edge_bevel + cut_margin,
                          mouth * (wing_thickness / 2 + cut_margin), epsilon);
                }
        }
}

module usb_cut() {
    // Rotate a rounded rectangle into the X/Z plane, cutting only the +Y wall.
    translate([0, housing_height / 2 + cut_margin, usb_center_z])
        rotate([90, 0, 0]) linear_extrude(height = wall_thickness + 2 * cut_margin)
            rounded_outline(usb_width, usb_height, usb_corner_radius);
}

module mounting_posts() {
    // Start each cylinder inside the floor at its lowest footprint elevation.
    // Pilot holes stop ABOVE the highest inner-floor point under that post.
    post_bottom = rear_z(post_x + post_r, rear_thickness) - epsilon;
    hole_bottom = rear_z(max(post_x - post_r, 0), rear_thickness)
                  + post_hole_floor_skin;
    for (x = [-post_x, post_x], y = [-post_y, post_y])
        translate([x, y, 0]) difference() {
            translate([0, 0, post_bottom])
                cylinder(d = post_diameter, h = post_top_z - post_bottom);
            translate([0, 0, hole_bottom])
                cylinder(d = post_hole_diameter, h = post_top_z - hole_bottom + epsilon);
        }
}

module enclosure_base() {
    union() {
        difference() {
            union() {
                difference() {
                    prism(housing_width, housing_height, housing_corner_radius,
                          blank_bottom, base_top - blank_bottom);
                    body_cylinder();
                }
                for (side = [-1, 1]) wing(side);
            }
            cavity();
            usb_cut();
            for (side = [-1, 1]) strap_slot(side);
        }
        mounting_posts();
    }
}

// Lid coordinates: Z=0 is its underside; hollow rim extends down into the base.
module enclosure_lid() {
    difference() {
        union() {
            prism(housing_width, housing_height, housing_corner_radius,
                  0, lid_thickness - front_edge_bevel);
            // A lofted bevel softens the front perimeter without heavy Minkowski.
            hull() {
                prism(housing_width, housing_height, housing_corner_radius,
                      lid_thickness - front_edge_bevel - epsilon, epsilon);
                prism(housing_width - 2 * front_edge_bevel,
                      housing_height - 2 * front_edge_bevel,
                      housing_corner_radius - front_edge_bevel,
                      lid_thickness - epsilon, epsilon);
            }
            difference() {
                prism(lip_width, lip_height, lip_radius,
                      -lid_lip_depth, lid_lip_depth + epsilon);
                prism(rim_inside_width, rim_inside_height, rim_inside_radius,
                      -lid_lip_depth - epsilon, lid_lip_depth + 3 * epsilon);
            }
        }
        translate([led_x, led_y, -epsilon])
            cylinder(d = led_diameter, h = lid_thickness + 2 * epsilon);
    }
}

// Pink envelope is a clearance aid, not real electronics or exported geometry.
module pcb_envelope() {
    color([0.9, 0.3, 0.5, 0.35])
        translate([-pcb_width / 2, -pcb_height / 2, post_top_z])
            cube([pcb_width, pcb_height, pcb_thickness + pcb_component_height]);
}

if (view != "lid") {
    color([0.45, 0.65, 0.8]) enclosure_base();
    if ($preview && show_pcb_envelope) pcb_envelope();
}
if (view != "base")
    color([0.8, 0.85, 0.9])
        translate(view == "assembled" ? [0, 0, base_top]
                  : [0, housing_height + display_gap, lid_lip_depth])
            enclosure_lid();
