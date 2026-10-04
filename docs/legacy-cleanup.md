# Focused legacy compatibility cleanup

The three historical command names remain supported. They preserve useful
annotated-window reports and legacy processed-data shapes, but no longer own
independent measurement or orientation algorithms.

| Responsibility | Authoritative module |
| --- | --- |
| IMU input/time validation and filtering | `signal_preprocessing.py` |
| Orientation filter equations | `madgwick.py` |
| Measured static/functional calibration | `sensor_to_segment_calibration.py` |
| Aligned flexion, gyro velocity and one finite difference | `aligned_kinematics.py` |
| Observed contact predicate, contacts and event pairing | `biomechanical_events.py` |
| Knee summaries, plantar impulse, loading rate and pressure | `event_biomechanics.py` |
| Absolute/signed asymmetry and gated bilateral comparison | `bilateral_comparison.py` |
| Canonical orchestration | `kintra_pipeline.py` |

## Retained adapters

- `analyze_session.py`: CLI presentation and compatibility exports. The existing
  JSON `analysis_version=0.2.0` and inclusive annotation contract are retained.
  `legacy_session_report.py` selects annotated windows, invokes canonical metric
  functions, and projects canonical comparisons into the old JSON field names.
  It does not own pressure, force, impulse, derivative, or asymmetry equations.
- `process_sensor_session.py`: validates through canonical preprocessing and
  calls canonical reconstruction separately for each side, then projects the
  result into the historical processed schema. An explicit identity transform
  is allowed only for marked ideal synthetic fixtures. Optional per-side measured
  `calibration_records` use the existing static/functional PCA implementation.
  Unique synthetic truth checks/presentation are in `synthetic_sensor_validation.py`;
  truth is never passed into reconstruction. Insole packets remain unchanged.
- `analyze_knee_kinematics.py`: balanced-fixture CLI and canonical helper aliases.
  No knee-summary or asymmetry equations remain in this file.

Canonical code no longer imports these legacy files. Existing generators,
sensor-baseline/activity demos and compatibility tests retain the adapter imports
because they consume annotated metadata or the older processed schema. Scientific
baseline-summary coverage now imports the authoritative knee-summary function.
No tests were removed.

## Compatibility boundaries

Canonical contact reports keep their existing complete contact windows; annotated
reports retain their original full annotated windows. Impulse scope therefore
remains explicit. Shared measurement equations are used in both, while canonical
contact timing and loading-rate corrections retain their existing policy.
The annotated report is a diagnostic projection of pre-extracted measurements;
it does not substitute for the four-calibration/context gate on runtime bilateral
knee comparison.

The old processor's 1% timestamp-interval tolerance is retired. Its adapter now
uses canonical continuous-clock checks at 1e-8 seconds, without resampling or
interpolation. The `processing.timestamp_processing` description records this
change. Identity calibration is restricted to explicitly synthetic ideal input;
real or non-ideal inputs require actual calibration records. Scientific equations
are unchanged. Balanced ideal-fixture samples and synchronization metadata match
the pre-cleanup processor exactly.

The sensor CLI now uses the canonical pipeline dependencies. Use the existing
environment documented in `modular-pipeline.md`. The annotated and knee-only
report CLIs retain their standard-library-only dependency path.

## Run without overwriting historical fixtures

```sh
python scripts/process_sensor_session.py data/raw/mock_balanced_raw.json \
  --output data/baseline_demo/cleanup/balanced_processed.json
python scripts/analyze_session.py data/mock/balanced.json \
  --output data/baseline_demo/cleanup/balanced_analysis.json
python scripts/analyze_knee_kinematics.py
python scripts/run_kintra_pipeline_demo.py
python scripts/run_bilateral_pipeline_demo.py
python -m pytest -q
```

`--output` is optional; omitted destinations retain historical CLI behavior.
Virtual-environment ignore rules preserve the user's directories on disk.
Stopping tracking an already indexed environment requires an index change;
ignore rules alone do not untrack existing files.

Baseline-learning internals, generator consolidation, activity models, DTW,
EWMA, reliability/MDC, ACT/VERIFY and app wiring remain outside this cleanup.
