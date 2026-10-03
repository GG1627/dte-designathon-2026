# Shared sensor data

Start UI algorithm development with the fixtures in `mock/`. These model data
**after** sensor alignment, clock synchronization, knee-angle extraction, and
insole pressure calibration. They are synthetic, noise-free inputs, not recorded
raw sensor streams or validated athlete measurements.

## Fixtures

Each JSON file is a complete 6-second session at 100 Hz (600 bilateral frames).

| File | Scenario | Intended use |
| --- | --- | --- |
| `mock/balanced.json` | Three bilateral landings with equal left/right force | Charts, contact detection, peak force, impulse, ROM |
| `mock/right_load_bias.json` | Same landings; right force is 10% greater | Paired event asymmetry; the specified symmetric-denominator formula gives about +9.52% |
| `mock/sensor_dropout.json` | Balanced session; left insole missing from 3.10 to 3.25 s, end exclusive | Gap handling; reject the affected contact's complete impulse and bilateral comparison |

The six-cell pressure map is an illustrative spatial fixture. The simulated
landing windows are ground-truth annotations, not detected contact boundaries.
The knee response is the same across the three scenarios, so algorithm behavior
can be compared while changing one input condition.

## Format: version 0.1.0

Top-level metadata includes session ID, synthetic flag, activity, participant
mass, sampling/clock information, processing assumptions, source IDs, and insole
geometry. `samples` contains ordered frames:

```text
sample
  sequence                    zero-based frame index
  timestamp_s                 seconds from session start
  left / right
    knee
      flexion_rad
      angular_velocity_rad_s
      angular_acceleration_rad_s2
      quality                 valid and reasons
    insole
      plantar_normal_force_n
      cell_pressures_pa       same order as insole_geometry[side]
      cop_m                   {x_m, y_m}, or null
      medial_fraction         fraction 0–1, or null
      lateral_fraction        fraction 0–1, or null
      quality                 valid and reasons
```

Knee flexion is positive. Insole x points toward toes, y toward the participant's
left, with origin at heel centre. Each cell declares its area, location, and
medial/lateral region; region labels reverse across feet. Pressure × cell area
sums to plantar normal force. This input is not labelled vertical ground-reaction
force. Convert radians to degrees only for display. Normalize force by
`participant.mass_kg * 9.80665` when displaying body-weight units.

Below 20 N, force/pressure remain valid but COP and regional fractions are null
with `below_contact_threshold`. During dropout, the entire insole measurement
is invalid and missing values are null with `sensor_dropout`. The knee remains
valid. Do not convert missing values to zero or silently bridge the gap.
Synchronization and calibration are idealized here; zero uncertainty is a mock
assumption, not a requirement for future devices.

## Regenerate and check

From the repository root, run:

```sh
python3 scripts/generate_mock_data.py
```

No packages are required. Generation checks timestamps, frame counts, finite
motion values, pressure-to-force consistency, COP, regional fractions, the
right-side scaling, and dropout values/count. Output is deterministic.

## Next algorithm layer

Consume the shared frames to detect contacts and compute event-level peak force,
loading rate, impulse, contact time, ROM, flexion at peak force, and paired
asymmetry using `docs/measurement-spec.md`. Keep calculation results separate
from input fixtures. Results should carry event bounds, units, configuration,
source IDs, and quality/rejection reasons. Additional fixtures will be needed
for noisy signals, timing errors, and calibration failures.

Real sensor recordings should use a separate directory and the same consumer
interface once adapters exist. Keep identifiable participant data out of Git.

## Personal-baseline demonstration

Run `python3 -B scripts/run_baseline_demo.py` from the repository root (`python` on
Windows). It generates five separate reference sessions with six landings each,
extracts quality-aware annotated-window metrics, learns session-median/MAD
baselines, and evaluates the three unchanged fixtures above. It also tests three
participant patterns, seven additional quality challenges, and histories of
3/5/10/20 sessions. Inspect generated JSON in `data/baseline_demo/`; reruns replace
only the demo's named outputs and its tracked result snapshot at
`rn-app/src/data/baseline-results.json`. The app displays these frozen landing
results separately from running/walking demo history; it does not learn live.
See [the baseline demo documentation](../docs/baseline-demo.md) for schema
extensions, statistical/quality rules, limitations, and focused tests.

## Raw IMU and processed-session experiment

`raw/mock_balanced_raw.json` contains ideal synthetic thigh/shank accelerometer
and gyro packets plus already-calibrated insole data. Ground truth is explicitly
validation-only. `processed/mock_balanced_processed.json` contains estimated
orientations, knee angles and finite-difference derivatives. `derived/` contains
diagnostic session reports, not inputs to the baseline fitter.

Run `python -B scripts/run_baseline_demo.py --sensor-pipeline` to route reference
history and held-out fixtures through ideal IMU emulation and Madgwick together.
Results go to `baseline_demo/sensor_pipeline/`; original fixtures and the app
snapshot are preserved. Analytic and Madgwick contexts cannot share a reference.
See [pipeline integration](../docs/pipeline-integration.md) for exact conventions,
quality policies, report version 0.2.0, commands and limitations.
