# Serial website handoff

Build a standalone React/Vite website in a new `web-app/` folder. The mobile
feedback work is ongoing in `rn-app/`; treat that folder as read-only while the
mobile session is active. Do not commit unrelated mobile changes. Read the root
AGENTS.md and keep changes scoped to the website and its documentation.

Match the mobile app's Home, Trends, Joints, and Live navigation, dark palette,
orange accent, blue thigh/comparison color, typography hierarchy, and feedback
cards. The Live flow is Start set -> Finish set -> Review, with tappable evidence
details. Inspect the final mobile screens again after the mobile session finishes;
copying a stale snapshot will not keep the website aligned automatically.

Reuse the dependency-free contracts/calculations from
`rn-app/src/data/live-simulation.ts` and `rn-app/src/data/knee-feedback.ts` where
practical. Avoid forking their algorithms. Native components cannot be imported
directly into an ordinary Vite DOM app; build the web presentation separately.
If the mobile session is updating these contracts, wait or coordinate rather than
editing the same files. Import shared TypeScript directly or propose a small
shared package after both flows work; do not restructure the repo preemptively.

The supplied HTML viewer uses Web Serial at 115200 baud, newline-delimited JSON,
and skips `#` metadata lines. Expected viewer fields:

```json
{"t": 50, "thigh": {"ax":0,"ay":0,"az":1,"gx":0,"gy":0,"gz":0}, "shank": {"ax":0,"ay":0,"az":1,"gx":0,"gy":0,"gz":0}}
```

The HTML treats `t` as milliseconds, accelerometer values as g, and gyro values as
degrees/s. Firmware has not been supplied, so confirm those assumptions on the
actual device. A hardware decoder should convert to `LiveSample` SI units:
`accelMS2`, `gyroRadS`, `timestampMs`, `sequence`, segment `valid`, and display
`angleDeg`, with `source: 'hardware'`. Preserve raw timestamps and source fields.
The viewer's complementary-filter angle is a debug estimate, not a validated
anatomical angle. Sequence/validity fields missing from the wire cannot be claimed
to be measured hardware quality. Preserve packet errors and interrupted data.

Use browser feature detection and a user-triggered connection request. Web Serial
needs a supported desktop browser and a secure context (localhost or HTTPS).
Handle partial/multiple lines, malformed or oversized packets, sensor errors,
disconnects, reader cancellation/release, port closure, and reconnects. Do not add
Bluetooth. There is no physical ESP32 available to the coding session: label mock
transport checks as software tests, and retain a physical serial acceptance check.

Keep simulated and hardware sources visibly separate. The current knee-feedback
engine deliberately blocks hardware exercise interpretation until calibration,
angle estimation, and segmentation are validated. Hardware inspection/recording
can still work. The website should never relabel real serial packets as simulated
to bypass that gate. Existing Python pipeline findings are documented in
`docs/pipeline-review.md`; the display contract alone is not a canonical session.

Coordination: report new files and shared-contract needs to the user. Keep website
commits separate. Recheck the mobile changes before claiming UI parity.

Mobile flow update: Get started now always opens the four illustrated guide
slides. Home has a compact setup entry before completion. Setup Continue advances
immediately, with optional demo timers; afterward Home leads with a change within
a six-bend set: the first three cover 85 degrees and the last three cover 65.
Show early/late leg schematics and rep markers, ask whether the change was planned,
and adapt the next step to the answer. The optional tired check-in is self-reported,
not inferred from angles. The 85-degree earlier-set reference stays in details.
The dependency-free example data is `rn-app/src/data/home-bend-demo.ts`. Detailed
evidence is behind a tap. Re-read the mobile Home/setup files to mirror the final
presentation; these walkthrough examples remain separate from saved Live sets.
