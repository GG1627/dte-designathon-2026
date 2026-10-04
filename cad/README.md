# CAD Workspace

This folder contains experimental CAD models for our designathon project.

## Goal

We are exploring the physical design of a wearable joint-monitoring device. The long-term product concept is a wearable system that helps monitor joint movement and injury-risk-related motion using sensors such as IMUs.

The purpose of this CAD workspace is currently **exploration and prototyping**, not final manufacturing.

We want to use Codex to experiment with physical form factors and learn what dimensions, mechanical constraints, and design decisions are needed to turn the concept into a realistic wearable product.

## Current Stage

We are very early in the physical design process.

At this stage:

- Final electronics dimensions are not known.
- Final sensors are not selected.
- Final battery dimensions are not known.
- Final strap dimensions are not known.
- Final enclosure dimensions are not known.
- Exact placement on the body has not been finalized.
- Models are conceptual prototypes only.

Codex may make reasonable placeholder assumptions when necessary, but every assumed dimension should be clearly labeled as an assumption.

Do not treat guessed dimensions as finalized engineering requirements.

## Initial CAD Tool

Initial prototypes should be created using **OpenSCAD**.

Prefer `.scad` source files so the geometry remains:

- readable
- editable
- parametric
- easy to iterate on
- suitable for version control

Important dimensions should be defined as named variables near the top of the file instead of being hard-coded throughout the geometry.

Example:

```scad
housing_width = 50;
housing_length = 70;
wall_thickness = 2;
corner_radius = 5;
```

## Initial Design Direction

The first physical concept should explore a wearable sensor module that could eventually attach around or near a joint such as the knee.

Possible components include:

- central electronics housing
- sensor enclosure
- removable lid
- strap mounting slots
- curved or contoured body-facing surface
- rounded external edges
- openings for charging or buttons
- mounting structures for internal electronics

The first models do not need to include all of these features.

Start simple and increase complexity incrementally.

## Design Priorities

When generating CAD concepts, prioritize:

1. Clear and understandable geometry.
2. Parametric dimensions.
3. Realistic mechanical relationships.
4. Comfortable rounded exterior surfaces.
5. Reasonable wall thicknesses.
6. Space for future electronics.
7. Easy iteration.
8. Geometry that could plausibly be 3D printed.

Avoid unnecessary decorative complexity during early prototypes.

## Assumptions

If information is missing, Codex may use reasonable placeholder values.

Any major assumptions should either:

- be documented in comments inside the `.scad` file, or
- be added to an accompanying notes file.

For example:

```scad
// ASSUMPTION: Placeholder width until PCB dimensions are known.
housing_width = 50;
```

## File Organization

Use descriptive filenames and preserve major iterations rather than constantly overwriting older concepts.

Example:

```text
cad/
├── README.md
├── prototypes/
│   ├── v1_basic_enclosure.scad
│   ├── v2_strap_mount.scad
│   └── v3_joint_module.scad
└── exports/
```

Create folders if needed.

## Current Objective

The immediate objective is simply to confirm that our AI-assisted CAD workflow works.

The first prototype should therefore be intentionally simple.

A good first experiment is a small parametric electronics enclosure containing:

- rounded rectangular housing
- hollow interior
- removable lid
- basic mounting posts
- one external opening
- editable dimensions

The resulting `.scad` file should be easy to open and inspect in OpenSCAD.

Do not attempt to design the final wearable during the first experiment.