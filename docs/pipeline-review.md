# Pipeline review — October 4, 2026

Reviewed merge commit `ad939ac`. Production algorithms were left unchanged.

The architecture is reasonable for an offline, restricted sagittal-motion prototype. It is **not yet correct across its intended operating conditions**, and this review does not establish real sensor accuracy or athlete validity. Five reproducible findings need attention before treating the outputs as trustworthy measurements outside the existing fixtures.

## Findings

### 1. High priority: stationary initialization can invent movement

Location: `scripts/aligned_kinematics.py:41`.

Initialization runs 200 filter updates from the identity quaternion, with the configured gain and nominal timestep. It never checks that the initial tilt estimate converged. For a stationary, ideal 60° shank orientation with zero gyro, the first knee estimate is **22.432°**, the estimate at one second is **32.947°**, and the final estimate is **59.970°**. These samples are marked valid despite the apparent movement being initialization error. This input satisfies the stated stationary-start assumption and stays below the documented 90° limit.

This can distort early ROM, velocity-versus-angle consistency, waveform shape, and movement features. Initialize roll/pitch directly from a verified stationary gravity observation, or require convergence before releasing valid samples. Preserve the explicit yaw assumption; gravity cannot establish heading. Add a regression with stationary starts at several supported angles, including 60°.

### 2. High priority for broader knee use: the angle representation folds above 90°

Location: `scripts/madgwick.py:66`, called by `scripts/aligned_kinematics.py:58`.

The helper returns Z-Y-X Euler pitch using `asin`, whose output is restricted to ±90°. An exact pure-Y quaternion representing **100° returns 80°**, and **120° returns 60°**. This is a documented model limitation, rather than an incorrect implementation of Euler pitch. However, the runtime marks resulting samples valid and does not prevent unsupported motion from entering subsequent metrics.

The current representation cannot support unrestricted knee flexion or general 3D joint angles. For a genuinely sagittal model, use an explicitly defined signed hinge-angle extraction and continuity policy that covers the required range. For broader 3D movement, define the anatomical joint coordinate system and validate it independently. Until then, make the operating restriction enforceable and visible to consumers; do not infer that an already folded pitch value proves the input stayed below 90°.

### 3. High priority: incomplete opposite-foot impulses enter personal history

Locations: `scripts/event_biomechanics.py:192` and `scripts/contextual_reference.py:57`.

The per-knee event worker summarizes **both feet inside the monitored knee's own-foot contact window**. When the left contact is shifted 80 ms relative to the right, the independent left-foot worker reports **374.678 N·s**, but the right-knee record reports a cropped left impulse of **364.241 N·s**. Its loading quality correctly says `valid=false`, with `contact_crosses_window_boundary`.

The reference adapter nevertheless accepts all three cropped left impulses because it checks only whether their numbers are finite. Thus an explicitly invalid measurement becomes eligible reference data. The separate bilateral plantar comparison uses each foot's own contacts and remains correct in this experiment; the defect is in the scalar-history path.

Compute each loading metric over its own foot's complete contact, with explicit event association, and require metric-specific quality when converting events into scalar history. Reject unavailable/truncated measurements and retain their reasons and actual accepted event IDs. Add the asynchronous-contact case to the regression suite.

### 4. High priority for hardware history: file hashes split comparable sessions

Locations: `scripts/hardware_session_adapter.py:249`, `scripts/kintra_pipeline.py:186`, and `scripts/contextual_reference.py:34`.

The hardware adapter puts the CSV's `source_sha256` inside `acquisition_context`. That entire context becomes part of the sensor configuration fingerprint. A different recording therefore produces a different reference group even when participant, sensors, activity, processing, and acquisition conditions match.

With five controlled records and different file hashes, fitting produces **25 distributions with one eligible session each**. With a common compatibility context, the same records produce **five distributions with five eligible sessions each**. The hardware caller does not currently supply a fitted reference, but its emitted records would fail to accumulate compatible history if used for that purpose. Waveform grouping and EWMA compatibility share this context problem.

Keep recording hashes and file paths as provenance. Fingerprint stable acquisition conditions such as placement protocol, footwear, surface, and sensor setup; exclude per-recording identity. Add a test showing that different recording hashes remain compatible while a meaningful protocol change does not.

### 5. Medium priority: the hardware timestamp bridge changes physical time

Location: `scripts/hardware_session_adapter.py:179`.

The adapter accepts measured timing within its engineering gates, then replaces analysis timestamps with `sequence / 100`. This is disclosed, but it is a measurement approximation: the original microseconds are retained only as provenance, while fusion, differentiation, contact durations, and frequency-based features use the replacement coordinate.

A constructed continuous **95.238 Hz** recording passes every adapter gate. Its movement lasts **3.1395 s**, but analysis sees **2.99 s**. A gyro ramp with true acceleration **0.1 rad/s²** is differentiated as **0.105 rad/s²**, a 5% error from time normalization alone. This experiment isolates timing arithmetic; it is not a full hardware accuracy estimate.

Use measured intervals for orientation integration and derivatives. Where uniform sampling is required for filtering or FFT features, choose and record an explicit resampling policy, or reject timing outside a justified approximation bound. Retaining actual timestamps does not by itself make downstream calculations use them.

## What is conceptually sound

- **Sensor fusion and mounting calibration:** the quaternion product order and Madgwick gradient equations are consistent with the declared convention. Separate sensor-to-segment calibration and fusion of rotated measured vectors are appropriate for the restricted model. Gravity-only heading, upright calibration, directed functional sweeps, and sagittal motion remain assumptions. The original [Madgwick report](https://x-io.co.uk/downloads/madgwick_internal_report.pdf) supports the fusion method and explains why accelerometer-only orientation references cannot establish heading. [Favre et al.](https://www.sciencedirect.com/science/article/abs/pii/S0021929009003649) provide functional calibration precedent, but their validated anatomical protocol is not equivalent to this prototype's static/PCA construction.
- **Movement recognition:** `StandardScaler + SVC` uses training-only scaling; temporal emissions use group cross-validation, and Viterbi is implemented as genuine log-space dynamic programming. Model suggestions remain separate from athlete confirmation. The manufactured training classes and engineered HMM bout transitions demonstrate integration, not generalization to athletes. There is no validated out-of-domain rejection.
- **Personal references:** session-first medians give sessions equal weight, references stay fixed, and participant/side/activity/movement/processing compatibility is checked. These are defensible descriptive design choices. Three events and five sessions are software sufficiency rules, not scientifically established counts.
- **Waveforms and trends:** z-normalized DTW measures shape while scalar metrics retain magnitude; EWMA summarizes chronological session values without silently updating the reference. Neither provides established normal/abnormal or injury thresholds. Unrestricted warping and event-weighted medoid selection are disclosed limitations.
- **Reliability and interpretation:** synthetic MAD is not promoted into SEM/MDC, and supplied reliability evidence must match metric, units, and context. This distinction is consistent with [Hopkins' measurement reliability discussion](https://pubmed.ncbi.nlm.nih.gov/10907753/). ACT/VERIFY remain explicit placeholders.
- **Missing channels and source information:** the bilateral worker preserves the usable knee when the other side fails and does not manufacture opposite-knee measurements. Insoles can be analyzed independently of knee calibration. Offline zero-phase filtering is correctly labeled non-causal, consistent with [SciPy's documented forward/backward filter](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.signal.sosfiltfilt.html).

## Validation still needed

The real-knee/mock-insole demonstration cannot establish actual landing timing or loading. Mock contact times are programmed independently of real movement; even an accurately measured angle selected by those windows is not a validated real landing metric. Check continuous knee motion separately, and retain the synthetic timing dependency when presenting event results.

Before hardware claims, compare against independent reference measurements across the required flexion range, different stationary start poses, remounting, gyro bias, dynamic acceleration, timing variation, and the expected off-plane movements. Validate contact boundaries and plantar measurements against a suitable independent reference when physical insoles exist. Assess repeated-measurement error for the actual metric and aggregation method before interpreting changes against MDC.

Train and evaluate movement recognition on real, independently grouped recordings, including transitions and unfamiliar movements. Measure classifier and temporal-model performance separately. Prototype success rates cannot substitute for this evaluation.

The app currently consumes frozen legacy snapshots; the canonical bilateral runtime contract is not fully connected to it. Passing frontend checks does not demonstrate live end-to-end ingestion.

## Reproduction and scope

Verification: all **235 existing tests passed** on this review run. The independent observation script reproduced all five findings. The test environment emitted an existing pandas/numexpr version warning; it did not fail any test. Windows sandbox permissions required running pytest with access to its temporary folders.

Run the added observation script:

```sh
python -B scripts/audit_pipeline_edge_cases.py
```

It prints all five experiments and writes ignored JSON to `data/baseline_demo/pipeline_review/findings.json`. Its CSV input is constructed locally and removed afterward. It does not modify production algorithms, fixtures, or fitted references. The hash experiment clones controlled measurements to isolate compatibility; it does not represent independent human acquisitions.

Reviewed the canonical single/bilateral orchestration, signal validation/filtering, fusion/calibration, contacts/metrics, SVM/HMM/windowing, confirmation, scalar/waveform references, EWMA, MDC gate, and CSV bridge. Existing tests are valuable but emphasize ideal, low-angle, synchronized synthetic measurements. Passing them does not cover the five counterexamples above. No new physical acquisition, lab comparison, or real-athlete evaluation was performed.
