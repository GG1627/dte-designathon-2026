# ESP32 hardware session bridge

`hardware_session_adapter.py` converts the existing real SD CSV to the existing raw session schema. No scientific algorithm, ESP32 firmware or website is changed. Bluetooth delivery is irrelevant to offline SD analysis.

## Commands

From the repository root, with the dependencies in `requirements-pipeline.txt` available:

```sh
python3 scripts/hardware_session_adapter.py session_0001.csv --side right --inspect
python3 scripts/hardware_session_adapter.py session_0001.csv --side right --participant-id YOUR_ATHLETE_ID --output data/hardware/session_0001.json
python3 scripts/hardware_session_adapter.py session_0001.csv --side right --participant-id YOUR_ATHLETE_ID --output data/hardware/session_0001.json --run-pipeline
```

`--side left` selects the left knee. The actual participant identity is required for pipeline execution, never invented. Conversion with no participant ID leaves it null. `--inspect` writes nothing unless `--output` is explicitly given. Exit status 2 means refusal or dependency/input failure. Invalid-but-parseable recordings may still be exported for inspection, with the refusal reasons; `--run-pipeline` never processes them. A malformed CSV fails before conversion.

Optional explicit designathon merge:

```sh
python3 scripts/hardware_session_adapter.py session_0001.csv --side right --participant-id YOUR_ATHLETE_ID --demo-insoles --mass-kg YOUR_MEASURED_MASS --output data/hardware/session_0001_demo.json --run-pipeline
```

This separate helper calls the existing deterministic insole generator at movement-relative times, aligned to the canonical movement timestamps. Both foot streams are `source=synthetic_demo`; their force patterns use the existing demo generator parameters, not measured foot loading. Opposite-knee motion is never produced. The real knee stays `source=hardware`, `synthetic=false`; the mixed session additionally declares `contains_synthetic_measurements=true`.

## CSV and canonical schema

Consumes `sequence`, `timestamp_us_actual`, `phase`, `ble_connected`; all six SI accel/gyro channels for thigh and shank; and both `valid`/`i2c_ok` flags. Metadata lines beginning with `#` are retained. The three debug angle columns are ignored, including during calibration and validation.

Existing raw schema version `0.1.0`:

- `session_id`, `synthetic=false`, `participant`, `sampling`, `sources`, `annotations=[]`, `samples`.
- Each movement sample has `timestamp_s`, `timestamp_us_actual`, `sequence`, and only the selected side's `imu.thigh` and `imu.shank`.
- Each packet has `timestamp_s`, `accel_m_s2.{x,y,z}`, `gyro_rad_s.{x,y,z}`, `quality.{valid,reasons}`, plus explicit `source=hardware`, `synthetic=false`, `sensor_id` provenance.
- Stable source IDs: `kintra_demo_thigh_imu`, `kintra_demo_shank_imu`.
- Additional associated acquisition metadata: `provenance`, `hardware_acquisition`, `calibration_records`, and, on successful measured calibration, `calibration_result`.
- Calibration records use the existing exact contract: `{thigh: {static_accel: Nx3, positive_flexion_gyro: Nx3}, shank: {...}}`.

Only after all hardware timing, validity and existing calibration gates pass, movement `timestamp_s` (including IMU packet timestamps) is `(sequence - first_movement_sequence) / 100.0`. Original integer microseconds remain in each sample’s `timestamp_us_actual`; actual duration is in `sampling.actual_duration_s`, and actual rate/jitter remain in acquisition timing diagnostics. Failed gates retain actual timestamp seconds, without constructing a uniform timeline. No signal resampling, renumbering, interpolation or debug-angle substitution. The source CSV path/hash is retained. Sensor reads are sequential: frame timestamps do not prove simultaneous acquisition; cross-device offset uncertainty remains unknown.

## Fail-closed rules

Prototype engineering acquisition criteria (not clinical, MDC, SEM or empirical sensor accuracy claims):

- Strictly increasing hardware timestamps and sequences, with zero skipped sequences. Duplicate/reversed sequences and timestamps fail.
- Effective rate between 95 and 105 Hz, inclusive. Rate is `(N-1)/elapsed_seconds`.
- Interval jitter is `abs(actual_interval_us - 10000)`. Mean absolute jitter at most 500 us; maximum at most 2000 us. Thus individual intervals must remain between 8000 and 12000 us.
- Any invalid/nonfinite channel, false validity flag or bad I2C flag rejects the session. Invalid measurements remain null/invalid, never repaired; finite readings with a false flag remain measured values with invalid quality.
- Entire-session timing and signal gates include idle/calibration rows, a conservative prototype policy. Movement must also satisfy the existing canonical validator.

**Canonical timestamp bridge:** Entire-session and movement timing gates must both pass, with valid sensors and successful existing calibration. The uniform sequence-based analysis coordinate uses `sampling.rate_hz=100.0` and duration `(last_sequence - first_sequence) / 100.0`. The existing canonical validator is then applied unchanged, including its `1e-8` second interval tolerance. Actual ESP32 times are preserved separately; this coordinate does not repair a gap or fabricate measurements.

## Calibration and movement

Phase 1 supplies measured static acceleration arrays for each segment; phase 2 supplies measured positive-flexion gyro arrays for each segment. Each calibration phase requires at least 200 samples spanning at least 1.99 seconds: a prototype two-second collection minimum, not scientific sufficiency. The existing `calibrate_pair` performs all PCA/sign/axis validation. Insufficient, invalid, unexcited or ambiguous calibration yields `calibration_required`. Both segment pods must provide an excited, signed positive sweep; a completely fixed thigh fails the existing calibration. ZERO is not used.

The existing calibration assumes an upright static pose whose segment long axis is world +Z, then designated positive flexion. The existing orientation initialization assumes the first movement sample is stationary and both segments share a zero-yaw reference. Those model limitations are preserved, not proven valid by this adapter.

Only phase 3 becomes canonical movement samples. No calibration/idle sample enters movement features. Multiple separated movement blocks retain their gaps and fail the canonical continuous-sequence requirement.

## Existing pipeline integration

`--run-pipeline` first requires adapter readiness and an explicit participant identity. It invokes `kintra_pipeline.run_pipeline`, passing measured calibration arrays, explicit hardware sensor descriptors, the selected knee side, and no implicit scientific filtering. The existing `imu_pair_only` profile is used when feet are unavailable.

The existing sensor descriptor container's supported `bilateral_knees_plus_insoles` mode permits absent sensors; it is used with exactly one hardware knee and both feet absent for the IMU-only case. This mode name does not manufacture bilateral data. For the optional explicit demo merge, the existing `single_knee_plus_mock_insoles` mode is used.

Pipeline output is written to `<output-stem>_pipeline.json`. Existing reconstructed flexion, velocity and acceleration are retained in `pipeline.knees.<side>.kinematics.samples`; `knee_summary` calls the existing `summarize_knee`. `existing_activity_features` calls the existing feature extractor on those already-reconstructed samples. It does not overwrite pipeline stages that require a trained model.

No SVM/HMM model or personal reference is invented/trained from this session. Classification, temporal smoothing and references remain unavailable when their required existing models/context/history are not supplied. There are no clinical interpretations or empirical reliability claims.

## Real files inspected

`Downloads/session_0001.csv`: 220 rows, 2.211 s, 99.050 Hz; no sequence gaps; four invalid thigh rows; max interval 20004 us, max jitter 10004 us.

`Downloads/session_0003.csv`: 1387 rows, 13.933 s, 99.476 Hz; no sequence gaps; eight invalid thigh rows; max interval 24001 us, max jitter 14001 us.

Both contain phase 0 exclusively, with no STATIC, FLEXION or MOVEMENT sections. Both return `invalid_hardware_acquisition`, with explicit missing-calibration/movement reasons. Neither was run through the pipeline. Successful adapter/pipeline tests use constructed CSV cases and are software verification only, not real hardware validation.
