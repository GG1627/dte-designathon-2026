# Reproducible personal-baseline simulation

This standard-library Python demonstration follows:

```text
five synthetic reference sessions
  -> annotated landing metrics
  -> per-session medians
  -> frozen personal median / MAD
  -> separate evaluation fixtures
```

The Python learner exports a frozen result snapshot for the mobile app. It uses no database, machine learning, contact detection, or composite health/readiness score. Synthetic differences do not validate real sensors, medical outcomes, injury prediction, or fatigue inference.

## Run and inspect

From the repository root, with Python 3.9 or newer:

```sh
python3 -B scripts/run_baseline_demo.py
```

On Windows, `python -B scripts/run_baseline_demo.py` is equivalent. `-B` avoids creating Python bytecode caches. No packages or network access are needed.

Detailed generated JSON lives in `data/baseline_demo/` and is ignored by Git:

| Output | Contents |
| --- | --- |
| `reference_001.json` through `reference_005.json` | Complete post-extraction reference streams, metadata, and synthetic waveform ground truth |
| `reference_metrics.json` | Reference event results, accepted/rejected reasons, sources, processing context, and session summaries |
| `baseline.json` | Six independently fitted side/metric distributions, readiness, contributing sessions/events, session medians, MAD, and exclusions |
| `evaluations.json` | Original-fixture event results and session summaries plus comparisons against the frozen reference |
| `manifest.json` | Seed, rules, reference/evaluation IDs, output names, and SHA-256 checksums of the original fixtures |
| `challenge_sessions.json` | Seven held-out noisy/faulted evaluation streams, with explicit synthetic assumptions |
| `experiments.json` | Three participant patterns, references fitted at 3/5/10/20 sessions, evaluation event quality and comparisons |
| `app_snapshot.json` | Result-only export for the app, without raw sample streams or event metric arrays |

Rerunning replaces only these twelve named outputs and `rn-app/src/data/baseline-results.json`, a tracked compact copy of the app snapshot. It does not delete other files or regenerate `data/mock/`. Reference streams use the existing compact JSON convention; result files are indented. Generation is deterministic for the same seed and Python/platform math implementation; tiny floating-point differences across platforms are possible.

Optional demo controls:

```sh
python3 -B scripts/run_baseline_demo.py --seed 20261003 --min-valid-events 3 --min-reference-sessions 5
```

These minimum counts are software demonstration choices, not validated clinical requirements. Raising the reference minimum above five intentionally produces insufficient-history results. Changing a seed explicitly replaces the generated history and its baseline.

## Schema extension and compatibility

The original `schema_version="0.1.0"` frames and SI units remain unchanged. New history adds a namespaced `baseline_demo` object with its own extension version `1.0.0`:

- `role`: `reference` or `evaluation`.
- `joint`: `knee`.
- `recorded_at` and `chronological_index`: explicit synthetic ordering, not actual recording dates.
- `configuration_id`: `mock_ideal_bilateral_knee_insole_v1`.
- `generation_seed` and `generator_version`.
- `synthetic_ordering=true`.
- Reference-only `waveforms`: generation parameters, treated as synthetic ground truth. Extraction never reads them.

Reference dates start September 1, 2026 (the 20-session experiment ends September 20), before all evaluation dates. Each reference has a unique session ID (`mock_reference_001` ... `005` for the default profile; other profiles append their participant ID) and seed (default master seed plus zero-based session index). Each lasts 12 seconds at 100 Hz, with six landings starting at 1, 3, 5, 7, 9, and 11 seconds. `participant_parameters` records the invented force/flexion pattern used by generation.

The unchanged legacy fixtures have no role/configuration/date metadata. The runner copies them in memory and explicitly assigns evaluation role, October 3 synthetic ordering, the assumed ideal configuration, and a named legacy generator version. `generation_seed=null` means their original generation was deterministic without a random seed. No metadata is written back to the fixtures. This adapter assignment is an assumption, not evidence of historical device calibration.

Compatibility requires participant, knee joint, side, activity, configuration ID, metric, and processing version/signature to match. A configuration fingerprint also checks the original schema, sampling rate/clock, extraction/calibration/filter metadata, source IDs, and insole geometry. A matching configuration label alone cannot override a geometry or processing mismatch. Compatibility is deliberately conservative for this initial mock-only workflow.

Challenge streams may add `timestamp_s` to an individual knee or insole measurement. When present it must align with the shared frame within the configured timestamp tolerance; otherwise only dependent metrics are rejected. This demonstrates rejection of unaligned input, not synchronization or clock correction. Descriptive text after a semicolon in `processing.filter` is excluded from the configuration signature; its method name still participates. Challenge seed and expected behavior are metadata only and never control extraction validity.

## Synthetic variation

`scripts/generate_mock_data.py` now accepts optional landing parameters and recording duration. Its default three-scenario behavior is preserved. Shared code generates the analytic knee derivatives, pressure map, COP, and regional fractions; the simulation does not duplicate those implementations. The analysis script's inclusive-window convention is retained, while ROM is calculated directly in radians after quality checks.

Each reference uses bounded pseudo-random session factors and per-event/per-side factors:

| Feature | Session variation | Event variation |
| --- | --- | --- |
| Force amplitude | multiplier 0.965–1.035 | per-side multiplier 0.975–1.025 |
| Flexion amplitude | multiplier 0.97–1.03 | per-side multiplier 0.975–1.025 |
| Pulse duration | additive ±0.025 s | additive ±0.025 s, rounded to 0.01 s |
| Flexion timing relative to force window | additive ±0.015 s | per-side additive ±0.01 s |

Nominal force remains 1.7 BW per foot. Nominal flexion pulses remain 38° left and 36° right above an 8° rest angle; they are stored in radians. Pulse duration is 0.55–0.65 s. Flexion center offset starts at `duration * 0.25 / 0.6`, and Gaussian sigma scales as `0.18 * duration / 0.6`; analytic first and second derivatives use those same parameters.

These bounds are invented software demonstration variation, not clinical normal ranges. There is no measurement noise, synchronization error, placement drift, or calibration failure in the generated reference history. Pressure-to-force consistency and the illustrative 55% medial / 45% lateral map are maintained. References are not derived from biased or dropout fixtures.

## Metrics and quality policy

All three event metrics use `synthetic_annotation_window`, inclusive endpoints, and actual timestamps:

| Metric | Calculation | Unit |
| --- | --- | --- |
| `knee_rom_rad` | maximum minus minimum valid flexion | rad |
| `peak_plantar_normal_force_bw` | maximum valid plantar normal force / `(mass_kg * 9.80665)` | BW |
| `landing_window_impulse_bw_s` | trapezoidal force integral over the annotated window / body weight | BW*s |

These are annotated-window metrics, not contact-detector outputs. The extractor uses the declared windows, not waveform/scenario ground truth.

- Annotation boundaries must be covered by samples. This first version expects grid-aligned endpoints, as in all generated/existing fixtures.
- Timestamps must be finite and strictly increasing. An ordering error or nonfinite timestamp rejects all windows conservatively rather than sorting or silently dropping the problem.
- Within each window, sequence numbers must be consecutive, and every interval must match the nominal period within absolute tolerance **1e-8 s**. Missing boundaries or discontinuities reject all three metrics for that window. Integration still uses actual intervals, never frame count times nominal period.
- A missing/nonfinite flexion value or invalid knee quality rejects that side's ROM. Unused derivative values are not inputs to these three metrics.
- Missing, negative, nonfinite, or invalid-quality insole measurements reject both that side's peak force and impulse. Under this conservative policy, an observed peak is not certified when part of the window is missing.
- Full valid pressure-cell coverage and positive finite areas are required. Pressure × area must reconstruct aggregate force within **relative tolerance 1e-12 or absolute tolerance 1e-10 N**, matching the shared generator checks. Material disagreements produce `inconsistent_pressure_force`; no field is silently repaired.
- Valid low-force samples remain usable even when COP or regional fractions are null. Those fields are not inputs to these metrics.
- Invalid participant mass rejects BW-normalized force metrics without suppressing knee ROM.
- No interpolation and no missing-to-zero substitution occur. Accepted/rejected event results preserve explicit reasons and source IDs.

`sensor_dropout.json` therefore has three valid knee events per side and three valid right-insole events, but only two valid left-insole events. The valid first and third left-force events remain in JSON; their session comparison is unavailable under the default three-event minimum.

## Learning and comparison

1. For each reference side/metric, take the median across valid events, requiring at least three.
2. Group by compatible context and take the median across eligible reference-session medians. Every session has equal weight regardless of event count.
3. Require five eligible sessions independently for each metric; otherwise status is `insufficient_reference_history` and fitted median/MAD are null.
4. MAD is the median absolute deviation of the eligible session medians from their median. It is not event-level MAD or an inferred biological variability measure.
5. Freeze the fitted object. Duplicate session IDs, role mistakes, and reference/evaluation overlap raise errors. Evaluation never updates reference statistics.
6. Require at least three valid evaluation events per side/metric before computing its session median and comparison.

Outputs retain session/event counts, contributing IDs, exclusions, units, configuration and method versions. Comparisons use:

```text
difference = evaluation session median - baseline median
percent difference = 100 * difference / baseline median
robust standardized difference = 0.67448975 * difference / MAD
```

A zero reference makes percent difference null with `zero_reference`. MAD at or below `max(1e-12, 1e-12 * abs(reference_median))` is numerically degenerate: standardized difference is null with `zero_or_degenerate_mad`. No tiny denominator is substituted. The signed physical-unit difference remains available when these normalized comparisons are undefined.

Insufficient events, unavailable history, and incompatible context make comparison values null with explicit reasons. Metric status can be `partial` when a physical difference is valid but a normalized comparison is undefined.

## Example with the default seed

Right peak-force reference-session medians are approximately **1.635578, 1.662179, 1.658888, 1.681679, and 1.666302 BW**. Their median is **1.662179 BW**, and MAD is **0.004123 BW**.

- Balanced evaluation median: **1.700000 BW**, approximately **+2.28%** relative to the learned reference.
- Right-biased evaluation median: **1.870000 BW**, approximately **+12.50%** relative to that reference.
- Direct fixture-to-fixture comparison is still exactly **+10%** for right peak force and impulse, within floating-point tolerance. The learned-reference difference need not be 10%.

With only five sessions, dispersion estimates are fragile. Very small synthetic MAD can create large standardized differences; this is descriptive arithmetic, not a calibrated threshold or injury probability. Force amplitude and impulse remain related, and no composite score is produced. Real recordings would require additional adapters, calibration/fit validation, quality scenarios, and a justified reference-history policy.

## Tests

```sh
python3 -B -m unittest discover -s tests -v
```

Checks cover known original-fixture ROM/force/impulse, direct 10% bias, equal session weighting, seeded variation and analytic derivatives, pressure/COP consistency, fixture preservation, deterministic reruns, frozen/separate history, feature-specific dropout, missing frames/quality/pressure faults, timestamp integration, zero/degenerate MAD, zero references, insufficient counts, and incompatible contexts. They validate the software demonstration only.

## Participant, quality, and stability experiments

All profiles currently weigh 75 kg to isolate their different usual movement/loading patterns. Athlete A uses 1.7 BW nominal force on both feet and 38/36 degree flexion amplitudes. Athlete B scales right force by 1.12 and uses 32/40 degree amplitudes. Athlete C scales both forces by 0.88 and uses 30/28 degree amplitudes. Each has a separately identified 20-session history; histories share random perturbations for controlled comparison, not because they are independent sampled people.

The same held-out measurement traces are replayed under each profile's context. B/C replays are explicitly counterfactual, not recordings from those participants. This shows why an identical measurement can differ from different personal references without asserting one person is healthier.

Seven additional challenges supplement the three unchanged fixtures:

- Seeded pressure noise (cell multipliers 0.99–1.01) and a 0.2 degree, 5 Hz angle perturbation with consistent analytic derivatives; aggregate force, COP, and fractions are recomputed from pressure.
- Left insole clock displaced 30 ms: left force/impulse rejected, knees retained.
- Left knee offset 4 degrees with failed alignment quality: ROM rejected, insole retained. A constant angle offset alone would not change ROM; the explicit quality failure is essential.
- Left pressure/force scaled 1.08 with failed calibration quality: left force/impulse rejected, knees retained.
- Missing left insole readings at the second landing onset: that side's force event rejected.
- Missing shared frame at second landing onset: that event rejected for both sides/signals.
- Both pressure/force scaled 1.08 without quality warnings: consistent signals remain accepted. The learner cannot distinguish actual loading changes from undetected calibration drift.

Reference fits at 3/5/10/20 sessions use chronological prefixes; each fit is frozen while evaluations run. Three sessions are intentionally insufficient under default rules. Inspect changing medians and MAD rather than interpreting stabilization as proof of accuracy. These challenges are controlled examples, not a realistic model of every hardware failure.

## App consumption

For the upstream raw-IMU/Madgwick connection, run
`python -B scripts/run_baseline_demo.py --sensor-pipeline`. This processes both
references and evaluations consistently, writes separate outputs, and leaves
the app snapshot intact. See [pipeline integration](pipeline-integration.md)
for responsibilities, compatibility fixes and remaining sensor limitations.

After running the Python command, start the existing app with `cd rn-app` then `npx expo start` (or `npx expo start --web --port 8085`). Trends and the monitored knee detail show the generated landing reference. Select participant, side, evaluation challenge, and history size; open **History & quality** for contributing session medians, stability, rejected events, and descriptive standardized differences.

The app imports `src/data/baseline-results.json` through `learned-baselines.ts`; it displays Python results rather than implementing a second learner. Angles convert to degrees only for display. There is no live ingestion, persistent user history, or automatic background learning. Running/walking demo charts retain their sample data but show no learned activity reference, because a bilateral-landing baseline is incompatible with those activities. Regenerate the snapshot after changing learner rules or synthetic generation.
