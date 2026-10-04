# V2 knee sensor module — conceptual prototype

Open `cad/prototypes/v2_knee_sensor_module.scad` in OpenSCAD. Units are millimeters. V1 is preserved. This is a geometry experiment, not a manufacturing-ready or medical device design.

## 1. Major design decisions

- **Coordinate system:** X runs across the leg and along the strap, Y runs along the leg, and positive Z points away from the skin. The rear center is Z=0.
- **Central housing:** a 60 × 46 mm rounded footprint with an 11 mm corner radius. Its front reaches Z=12.5. The curved rear drops approximately 4.17 mm at X=±30, making the maximum central housing depth approximately **16.67 mm**, including the cover. `front_z` alone is not the total depth.
- **Body-facing shape:** the upper surface of a cylinder of radius 110 mm forms a concave cradle when viewed from underneath. The curvature is across X only, not along Y. The inner floor uses a concentric cylinder with radius 112.4 mm, preserving 2.4 mm radial floor thickness rather than cutting a flat cavity through a curved rear.
- **Integral wings:** each extends 20 mm past the housing, giving a 100 mm total span. Their rears share the housing's cylinder, with 4.4 mm radial thickness. A 2 mm root overlap joins each wing to the housing's 2.2 mm side wall; the root stays outside the electronics cavity. Rounded roots narrow toward the housing but retain positive solid overlap.
- **Strap slots:** two capsule openings provide approximately 27 mm along Y and 4 mm across their local tangent. Each cutter follows the local radial direction. Both mouths have approximately 0.6 mm bevels, and the ends are semicircular. These are rounded slot outlines with beveled mouths, not full 3D fillets. Conservatively checked material around the rounded outer wing corners exceeds 2.4 mm; the nominal Y-end web after beveling is 2.9 mm.
- **Cover:** a 1.8 mm plate rests on the wall tops at Z=10.7. Its front perimeter has a 0.8 mm bevel. A hollow 1.4 mm thick rim extends 2.4 mm into the cavity, with **0.4 mm clearance per side**. The rim locates the cover without occupying the PCB's central space. The cover is removable, but has no positive retention yet.
- **Mounts:** four 5.4 mm posts at X=±16, Y=±10 have level tops at Z=6.2. Their bottoms penetrate the curved floor to join it. Blind 2 mm pilot holes stop at least 1 mm above the highest local inner-floor surface. No holes pierce the body-facing rear.
- **Openings:** a rounded rectangular charging aperture is centered on the +Y wall between the post columns. A 3 mm LED aperture passes through the cover at X=0, Y=-8. The charging opening is below the locating rim.

## 2. Important assumptions

All hardware and fit dimensions below are placeholders; no PCB, sensor, battery, strap, connector, screw, or anatomical fit has been selected.

| Group | Assumed values / meaning |
| --- | --- |
| Housing | 60 mm wide, 46 mm tall; front Z=12.5; central depth limit 18 mm; 11 mm plan corner radius |
| Shell | 2.2 mm side walls, 2.4 mm radial rear, 1.8 mm cover; 0.8 mm cover perimeter bevel |
| Anatomy | 110 mm cylindrical body radius; no compound knee shape, padding, clothing allowance, or joint motion modeled |
| Wings | 20 mm reach per side, 34 mm along Y, 4.4 mm radial thickness, 5 mm plan corner radius, 2 mm root overlap |
| Strap | 25 mm width, 2 mm thickness, plus 2 mm allowance in each slot dimension; approximate 6.5 mm outer web before tilt effects; 0.6 mm mouth bevel |
| Structural margins | 2.4 mm minimum checked slot web; geometric plausibility only, with no specified tension/load or material strength |
| PCB | 38 × 26 mm rectangular board, 1.6 mm thick; centered, with 32 × 20 mm mounting-hole spacing |
| Components | 1.8 mm height above the PCB; no underside components, tall connector, battery, wires, or sensor orientation modeled |
| Posts | 5.4 mm diameter; top Z=6.2; 2 mm blind pilot holes; 1 mm skin above the inner floor under holes; no selected screw or thread engagement |
| Internal margins | 0.8 mm minimum PCB/post-to-rim clearance; 0.8 mm minimum component-to-cover clearance |
| Cover fit | 0.4 mm clearance on each mating side, 2.4 mm rim insertion depth, 1.4 mm rim thickness; no gasket, latch, screws, or friction-retention guarantee |
| Charging | 10 × 3.4 mm opening, 0.6 mm corner radius, center Z=5.7 on +Y wall; not a USB-C specification or validated cable-plug envelope |
| Charging layout | Assumes an off-board charging connector/daughterboard in the space beyond the main PCB's +Y edge, linked by wires/flex. The opening does not establish a connector location on the main PCB; this must be redesigned if charging is on that PCB. |
| LED | 3 mm aperture at (0, -8) in the cover; assumes a future aligned indicator/light pipe, not a fitted or sealed LED |
| Printing | No process or material chosen. Clearance, pilot holes, supports, shrinkage, and surface finish need print trials. |

`display_gap=12`, `epsilon=0.02`, `cut_margin=1`, and the tessellation counts are display/modeling controls, not hardware requirements. Curve tessellation approximates the concentric surfaces; radial thickness is nominal rather than an exact distance everywhere on the polygon mesh.

## 3. Dimensions likely to change with real electronics

1. PCB footprint, mounting-hole spacing, pilot-hole diameter, post height, and fastening method.
2. `front_z`, `pcb_component_height`, and cavity volume after choosing the battery, sensors, charging hardware, and wiring.
3. Charging opening size and position, connector mount/support, and plug insertion clearance.
4. LED location, light pipe, or an actual button mechanism.
5. Body radius, wing reach, root shape, and strap slot dimensions after fit and strap trials.
6. Wall thickness, lid clearance, lip depth, and retention after choosing a print process and material.

## 4. Geometry checks and current limitations

### Checks performed on the default dimensions

- OpenSCAD's full CGAL render succeeded and reported a simple 3D solid.
- The exported separated mesh contains exactly **two connected components**, with positive volumes and every mesh edge incident to exactly two triangles. This confirms that the base, wings, and four posts form one connected closed component, and the cover forms the other.
- A Boolean intersection of the assembled cover and base was empty: no volumetric interference. Contact at the wall seating surface is intentional.
- A Boolean intersection of the assembled cover and the PCB/component envelope was empty. Envelope top Z=9.6 leaves **1.1 mm** to the cover underside at Z=10.7. The rim descends to Z=8.3 but lies outside the board footprint.
- Rounded-rectangle distance checks include corner geometry when checking posts and PCB against the rim; independent X/Y bounds alone would miss corner collisions.
- The USB opening extends from Z=4.0 to Z=7.4. It sits at least 1.6 mm above the highest inner floor and 0.9 mm below the rim. Its X footprint stays between the post columns.
- Slot cuts stay outside the central cavity. Conservative slot checks account for radial tilt, mouth bevels, and the wing's rounded outer corners.
- Top/interior and rear views were inspected. The rear and wings follow the same curve; post tops are level and the cover has a real hollow locating rim.

Assertions reject several unsafe parameter combinations. They are geometry guardrails, not a universal validator for every possible edit or proof of mechanical strength. Rerender and inspect after changing parameters.

### Weaknesses / limitations

- **No positive cover retention:** the rim locates but does not lock. This version is suitable for inspection; wearable use requires screws or a tested latch.
- **No load validation:** strap web and root sizes are plausible starting points only. Stress concentration, layer direction, fatigue, impact, and strap wear remain untested.
- **Limited anatomical fit:** a rigid cylinder cannot capture a knee's compound surface, motion, or differences between people. No comfort or skin-contact performance is established.
- **Rear edges:** plan corners and slot mouths are softened, but rear-to-side and wing-to-housing transitions do not have true rolling fillets. Further comfort rounding and possibly padding are needed.
- **Printing orientation:** the curved rear is not a flat build-plate surface, and the downward cover rim means the cover may need to be flipped for printing. Supports/orientation are not resolved.
- **Open housing:** no water/sweat seal, gasket, strain relief, charging-port protection, LED lens, or electrical isolation design.
- **Incomplete electronics:** the translucent envelope is only a board plus a uniform component-height allowance. Battery, connector daughterboard, cables, and tall components need their own keep-outs and mounts.
- **Bounding depth:** the 18 mm limit applies to the central housing. The wings wrap downward to approximately Z=-12.04, so the full assembled module's world-axis bounding depth is about 24.54 mm. That is curvature across the wider span, not a 24.54 mm thick wing.
- **Fit clearance:** 0.4 mm per side is a starting assumption; it does not guarantee printed fit or holding force. Hole diameters are not fastener specifications.

## 5. Changes for V3

Select actual electronics first and model their mounting pattern and separate component/cable/plug keep-outs. Add a battery cradle and a supported charging connector. Add positive cover retention with separate bosses or tabs, preserving PCB and port clearances, and consider a gasket land. Fit the rear shape using measured leg/strap geometry and explore padding or compliant wings. Add rear/root fillets, test slot wear and strap tension on printed samples, then tune tolerances and printing orientation.

## Inspecting and experimenting

Start with `view="separated"` (default), then try `"assembled"`, `"base"`, or `"lid"`. Rotate the cover to see its underside rim. `show_pcb_envelope=true` adds a translucent clearance envelope during F5 preview only. F6 renders the actual parts without the envelope; a separated export contains two parts.

Change `body_radius` first to explore fit, then housing width/height, `wing_reach`, and strap dimensions. Adjust PCB dimensions/spacing together with post and component heights. Parameter assertions explain several invalid combinations, including edits that exceed the central depth limit. Preserve this version for future comparisons.
