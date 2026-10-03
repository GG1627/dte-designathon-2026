# Sensor processing and personal-baseline integration

The two contributions cover different stages of one pipeline:

```text
synthetic motion and pressure fixtures
  -> generate_raw_sensor_fixture.to_raw_session: ideal IMU emulation
  -> process_sensor_session.process_session: Madgwick angles / relative gyro velocity / acceleration
  -> baseline_simulation.extract_session: quality-aware annotated landing metrics
  -> summarize_session / fit_baseline: session medians, personal median and MAD
  -> compare_evaluations: frozen reference versus separate evaluation
```

`scripts/analyze_session.py` is a parallel diagnostic report over extracted
samples. It additionally reports velocity/acceleration, pressure distribution,
threshold-based contact duration, average loading rate, and bilateral asymmetry.
Its degree/N/N*s summaries are not baseline input files. The baseline extractor
owns the three initial per-metric rad/BW/BW*s results and their rejection policy.

## Run the connected software experiment

From the repository root:

```sh
python -B scripts/run_baseline_demo.py --sensor-pipeline
```

This reuses the existing five-session/six-landing reference generator, emulates
raw IMUs, and processes **both** history and evaluation through the same Madgwick
implementation. The balanced, biased, and dropout inputs remain separate
evaluations. Results replace only the nine named JSON outputs in
`data/baseline_demo/sensor_pipeline/`. Original mock/raw/processed fixtures and
the app's bundled snapshot remain unchanged.

With the default seed, right-knee ROM has a reference median of approximately
0.553751 rad and MAD 0.007067 rad; balanced evaluation is 0.544398 rad, about
1.69% lower. All six baseline metrics are ready. Force and impulse are passed
through the IMU layer, so biased right values remain exactly 10% above balanced
within floating-point tolerance. Dropout still leaves only two valid left-force
events and retains knee comparisons.

The normal `python -B scripts/run_baseline_demo.py` command retains the existing
analytic-angle experiments and refreshes the app snapshot. The app currently
shows those frozen synthetic results; it does not ingest raw IMUs or fit history
on the device. The new command verifies the upstream connection independently.

## Corrected sensor kinematics and controlled fixture

The processor keeps Antonio's angle path: Madgwick thigh/shank orientations,
then signed Y pitch of the relative quaternion. Knee angular velocity is the
calibrated shank gyro Y minus thigh gyro Y; angular acceleration is one central
finite difference of that velocity, with one-sided boundary differences.
The analyzer and baseline layer consume these measurements; neither derives
velocity by differentiating the Madgwick angle. No smoothing is added.

Y subtraction is valid only for the ideal aligned sagittal model. Real 3-D
hardware requires calibrated segment angular velocities transformed into a
common/anatomical frame before extracting the relative flexion component.

Generate the balanced regression fixture explicitly, or retain the default
20-landing fixture with its four programmed phases:

```sh
python3 -B scripts/generate_raw_sensor_fixture.py --scenario balanced
python3 -B scripts/process_sensor_session.py data/raw/mock_balanced_raw.json
python3 -B scripts/analyze_session.py data/processed/mock_balanced_processed.json
python3 -B scripts/generate_raw_sensor_fixture.py
python3 -B scripts/process_sensor_session.py data/raw/mock_training_20_landings_raw.json
python3 -B scripts/analyze_session.py data/processed/mock_training_20_landings_processed.json
python3 -B scripts/generate_raw_sensor_fixture.py --validate-processed data/processed/mock_training_20_landings_processed.json
```

The raw adapter preserves reference-history context and validation-only analytic
truth, while the processor never reads truth for reconstruction. All scenario
logic and phase assertions stay in the generator. The 41-second fixture has
4,100 samples and 20 bilateral events. It exercises baseline-like repeated
motion, symmetric loading increases, reduced flexion, and right-load bias;
it does not establish a personal baseline or a fatigue/injury score.

The balanced regression expects left/right peak velocities of 128.045361 and
121.306132 deg/s, and peak accelerations of 1171.030965 and 1109.397756 deg/s².
Repeated velocity/acceleration ranges remain at floating-point precision.
`tests/test_kinematic_regression.py` protects these values, ground-truth
independence, and the training phases in addition to Gael's integration tests.

## Integration corrections

- The baseline configuration fingerprint accepts either the original `filter`
  metadata or Madgwick's `orientation_filter` / `derivative_filter` fields.
  Missing an original field no longer crashes extraction. Processing metadata
  still participates in compatibility checks: analytic-angle and Madgwick
  contexts are rejected when mixed, including force metrics conservatively.
- Ideal IMU conversion accepts arbitrary synthetic session lengths, preserving
  roles, chronology, seeds and configuration in `baseline_demo`.
  The processor carries this metadata forward without using waveform ground
  truth to reconstruct angles. Invalid source knee motion cannot become valid
  emulated IMUs. Pressure/dropout packets pass through unchanged.
- The processor rejects explicitly invalid IMU quality, boolean measurements,
  and declared per-IMU timestamps that differ from the common frame by more than
  1e-8 s. Existing packets without per-IMU timestamps retain their documented
  shared-clock assumption. This is rejection, not clock synchronization.
- The session analyzer uses the baseline's continuity/boundary checks and
  shared pressure-force reconstruction tolerances (relative 1e-12, absolute
  1e-10 N). It rejects negative force and misaligned per-signal timestamps.
  Its `analysis_version` is now 0.2.0; four committed diagnostic reports were
  refreshed. Legacy absolute asymmetry fields remain available; the new
  `bilateral.signed_asymmetry_percent` group preserves direction per the
  measurement specification. Force vocabulary no longer implies validated
  ground-reaction force equivalence.
- Generated Python bytecode was removed and ignored. It is not portable source
  code and is unnecessary for reproduction.

## Remaining limits and ownership

The raw fixture emulates gravity and analytic angular velocity: no translation,
bias, noise, skin motion or placement errors. Insoles are already calibrated
measurements, not raw ADC values. Madgwick currently assumes ideal alignment,
stationary initialization, common zero yaw, and sagittal signed Y pitch limited
to +/-90 degrees. It implements no general anatomical neutral-pose calibration.
Gyro-derived velocity is unfiltered; its finite-difference acceleration can have boundary artifacts and will require a justified noise policy for real sensors.
These are software demonstrations, not sensor or medical validation.

The processor requires a complete session and aborts on an IMU/frame fault;
the baseline extractor rejects individual annotated events/metrics. That stricter
upstream policy is intentional for now. The processor accepts interval jitter
within 1%, while baseline eligibility requires the configured tighter continuity
tolerance; passing upstream validation alone does not guarantee metric acceptance.

The analyzer's kinematics group requires valid angle **and derivatives**, while
baseline ROM only needs angle. Its loading-group quality also includes contact
timing issues that are irrelevant to annotated-window peak/impulse. Keep those
group flags out of baseline fitting. Threshold contact summaries are not a full
hysteresis-based contact detector, and average loading rate is not maximum dF/dt.

Antonio's processing functions should own IMU fusion/calibration. The baseline
module should own per-metric extraction, history eligibility and comparison.
Keep the broader analyzer for diagnostics; avoid building a second baseline
learner from its report JSON. The next integration step is a quality-preserving
adapter for real hardware, followed by comparable reference recordings through
that adapter. Real calibration, synchronization and general 3-D motion remain
separate work.

Verify with `python -B -m unittest discover -s tests -v` and
`python -B scripts/test_madgwick_knee.py`. Cross-pipeline tests cover context
separation, ground-truth independence, IMU faults, shared metric agreement,
signed asymmetry and dropout. Tiny differences when regenerating committed
fixtures (observed about 8.4e-13 in knee derivatives) are floating-point effects,
not evidence of incompatible schema.
