# Knee monitoring measurement contract

Status: prototype specification, version 0.1.

## Scope

Combine two IMUs per leg (thigh and shank) with bilateral partner pressure
insoles. Simulated and real sensors must use the same normalized interface.
The prototype reports motion and plantar loading measurements; it does not
estimate internal knee forces, diagnose injuries, or predict injury risk.

## Acquisition requirements

- Identify session, device, side (`left` or `right`), and IMU segment
  (`thigh` or `shank`) on every stream.
- Use SI units at ingestion: seconds, metres, radians, radians/second,
  metres/second squared, pascals, and newtons.
- Preserve device timestamps and sequence numbers. Map each stream onto a
  common monotonic session clock, with recorded offset, drift correction,
  and estimated synchronization uncertainty. Receipt time alone is insufficient.
- Target 100–200 Hz for prototype motion and pressure streams. Record actual
  rate, dropped samples, saturation, calibration status, and timestamp quality.
  These are design targets requiring validation for the selected hardware.
- Preserve original samples. Resampling must flag gaps and must not interpolate
  across gaps longer than two nominal sample periods.
- Record participant mass in kilograms when body-weight normalization is used;
  body weight in newtons is mass × 9.80665.

## Coordinate and calibration contract

Use a right-handed session frame: x forward, y left, z up. Store sensor-to-segment
alignment separately from raw measurements. Quaternions use `[w, x, y, z]` and
rotate sensor-frame vectors into the session frame.

Record a neutral-pose calibration and define knee flexion as positive relative
to that pose. Relative thigh/shank orientation requires a calibrated flexion
axis; quaternion magnitude alone is not a knee flexion angle. Sensor placement,
soft-tissue motion, and alignment remain sources of measurement error.

Insole cells use a foot-local frame: x toward toes, y toward the participant's
left, z upward, origin at heel centre. Record cell centres, effective areas,
side, units, calibration method/date, and validity. Left and right medial/lateral
regions must be explicitly labelled; they cannot share an unqualified y-sign rule.

## Measurements

| Output | Definition | Prerequisites / limits |
| --- | --- | --- |
| Knee flexion | Calibrated flexion component of thigh-to-shank relative orientation, rad | Both aligned IMUs; report calibration quality |
| Angular velocity | Time derivative of filtered knee flexion, rad/s | Record filter and derivative method |
| Angular acceleration | Time derivative of angular velocity, rad/s² | Noise-sensitive; quality gate before reporting |
| Range of motion | Maximum minus minimum knee flexion over a labelled event, rad | Complete event window |
| Plantar normal force | Sum of calibrated cell forces, N; pressure cells contribute pressure × effective area | An estimate of plantar normal loading; equivalence to vertical ground-reaction force requires validation |
| Peak force | Maximum plantar normal force during contact, N and optionally BW | Complete contact; calibrated force |
| Loading rate | Maximum positive derivative of filtered force between contact onset and peak, N/s and optionally BW/s | Record filter; sample-rate-sensitive |
| Impulse | Integral of force over contact using actual sample times, N·s | Complete contact; gaps invalidate result |
| Contact time | Contact offset minus onset, s | Configured force threshold and hysteresis |
| Pressure distribution | Valid cell pressures or labelled regional forces | Preserve sensor geometry and spatial coverage |
| Centre of pressure | Force-weighted cell centre, m | Full valid coverage and force above contact threshold |
| Medial/lateral loading | Each labelled region's force divided by total valid force | Explicit region membership; adequate coverage |

Body-weight-normalized force is force / body weight. Use `null` for unavailable
outputs, with a reason; never substitute zero for missing data. Partial cell
coverage must be flagged and must not silently yield a full-foot estimate.

## Event and derived features

Contact detection uses configurable onset/offset thresholds, hysteresis, and
minimum duration. Store the configuration with each result; thresholds are
prototype settings, not universal clinical cutoffs.

- Bilateral asymmetry: `100 × (right − left) / ((right + left) / 2)` for paired,
  nonnegative metrics. Positive means right greater than left. Return `null`
  when the denominator is zero or pairing is invalid. Retain signed and absolute
  values. Pair simultaneous landing contacts or corresponding gait cycles,
  according to the labelled activity.
- Landing features: knee flexion at force peak, peak force, loading rate,
  impulse, and contact time, linked to a common event timestamp. Suppress
  cross-sensor features when synchronization uncertainty exceeds the configured
  tolerance; record that tolerance.
- Movement variability: summarize a named metric over repeated comparable
  events, reporting event count and dispersion. Require at least three valid
  events for a prototype summary; do not compare mixed activities.
- Time to stabilization: deferred until a signal, reference band, required
  dwell time, and observation window are defined and validated. Do not emit a
  fabricated value for incomplete observation.
- Fatigue-related drift: report change from an explicit baseline during
  comparable tasks as descriptive drift. Sensor drift and altered technique
  can produce changes; no causal fatigue claim is made.
- Cumulative mechanical exposure: report summed contact impulse and contact
  count over a stated window, with data coverage. This is external loading
  exposure, not internal joint dose or tissue damage.

## Implementation boundary

Step 2 defines versioned session metadata, IMU samples, insole samples, and
feature results. Each feature result carries units, event/window bounds,
processing configuration, source identifiers, and quality/rejection reasons.
Partner adapters convert native data into that contract; the biomechanics
pipeline consumes only normalized samples. Simulation fixtures are explicitly
labelled synthetic and cannot be presented as measured participant data.

## Acceptance checks for subsequent code

1. Known static and rotating synthetic segment orientations produce expected
   calibrated knee angles and derivatives.
2. A known pressure map produces expected summed force and centre of pressure;
   mirrored foot regions retain correct medial/lateral labels.
3. A synthetic force pulse yields expected peak, contact duration, and impulse.
4. Timestamp offsets, dropped samples, invalid calibration, and incomplete
   coverage reject affected outputs with explicit reasons.
5. Asymmetry handles equal sides, side reversal, and zero denominators.

Hardware accuracy and interpretation must be assessed separately against
appropriate reference measurements before claiming validated performance.
