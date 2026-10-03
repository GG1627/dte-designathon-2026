"""Kintra raw-to-processed session pipeline; currently ideal mounting only.

No ground truth participates in processing. Initialization assumes the first
sample is stationary and both sensor yaw references are zero. This is suitable
for the sagittal fixture, not an arbitrary 3-D anatomical angle calibration.
Velocity uses calibrated shank gyro Y minus thigh gyro Y only for this ideal
aligned sagittal model. Real 3-D hardware requires transforming both segment
angular velocities into a common/anatomical frame before taking the component.
"""
import argparse
import copy
import json
import math
from pathlib import Path

from madgwick import MadgwickIMU, quaternion_relative, relative_flexion_y_rad

ROOT = Path(__file__).resolve().parents[1]
BETA = 0.1
INITIAL_TILT_ITERATIONS = 200


def validate_timestamps(data):
    samples = data["samples"]
    rate = data["sampling"]["rate_hz"]
    if not math.isfinite(rate) or rate <= 0 or len(samples) < 3:
        raise ValueError("Positive sampling rate and at least three samples required")
    nominal_dt = 1 / rate
    intervals = []
    for i, row in enumerate(samples):
        if not math.isfinite(row["timestamp_s"]) or type(row["sequence"]) is not int:
            raise ValueError("Invalid timestamp or sequence number")
        if i:
            previous = samples[i - 1]
            dt = row["timestamp_s"] - previous["timestamp_s"]
            if dt <= 0 or row["sequence"] <= previous["sequence"]:
                raise ValueError("Timestamps and sequence numbers must strictly increase")
            if row["sequence"] != previous["sequence"] + 1 or not math.isclose(dt, nominal_dt, rel_tol=0.01, abs_tol=1e-9):
                raise ValueError("Missing sample or unexpected sampling interval; no interpolation")
            intervals.append(dt)
    return {
        "validation": "PASS", "expected_interval_s": nominal_dt,
        "observed_min_interval_s": min(intervals), "observed_max_interval_s": max(intervals),
        "resampling": "none", "sequence_gaps": 0,
        "clock": data["sampling"]["clock"],
        "synchronization_uncertainty_s": data["sampling"].get("synchronization_uncertainty_s"),
        "synchronization_basis": "input clock metadata; sample timing checked, cross-device offset not independently measured",
    }


def calibrate_imu(packet):
    """Explicit identity sensor-to-segment stage; no corrections for ideal mounting."""
    gyro = tuple(packet["gyro_rad_s"][axis] for axis in ("x", "y", "z"))
    accel = tuple(packet["accel_m_s2"][axis] for axis in ("x", "y", "z"))
    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in gyro + accel):
        raise ValueError("Missing or nonfinite IMU sample; interpolation is not supported")
    return gyro, accel


def check_quaternion(q):
    if not all(math.isfinite(value) for value in q) or not math.isclose(math.hypot(*q), 1.0, abs_tol=1e-10):
        raise ValueError("Quaternion is nonfinite or not normalized")


def finite_difference(values, times):
    """Secant central differences inside; first-order one-sided at boundaries.

    Interior: (v[i+1]-v[i-1])/(t[i+1]-t[i-1]). Applied once to gyro velocity.
    No smoothing or interpolation; derivative noise is not suppressed here.
    """
    return [
        (values[min(i + 1, len(values) - 1)] - values[max(i - 1, 0)])
        / (times[min(i + 1, len(times) - 1)] - times[max(i - 1, 0)])
        for i in range(len(values))
    ]


def process_session(raw):
    timing = validate_timestamps(raw)
    if raw["processing"].get("sensor_to_segment_alignment") != "ideal":
        raise ValueError("Only explicitly ideal mounting is supported; real hardware needs calibration")
    # Whitelist metadata; ground-truth validation fields are never accessed here.
    processed = {key: copy.deepcopy(raw[key]) for key in (
        "schema_version", "session_id", "activity", "synthetic", "participant",
        "sampling", "sources", "insole_geometry", "annotations",
    )}
    for key in ("scenario", "phases"):
        if key in raw:
            processed[key] = copy.deepcopy(raw[key])
    processed["processing"] = {
        "stage": "post_sensor_processing", "orientation_filter": "Madgwick 6-DOF",
        "sensor_to_segment_calibration": "synthetic ideal alignment",
        "calibration_transform_wxyz": [1.0, 0.0, 0.0, 0.0],
        "hardware_calibration_requirement": "real hardware requires sensor-to-segment calibration",
        "knee_angle_source": "relative thigh/shank Madgwick orientation; signed Y pitch",
        "knee_angular_velocity_source": "relative thigh/shank gyroscope Y-axis; ideal aligned sagittal model",
        "knee_angular_acceleration_source": "finite difference of gyro-derived knee angular velocity",
        "velocity_frame_requirement": "real 3D hardware requires calibrated common/anatomical frame transformation",
        "relative_orientation": "conjugate(thigh sensor-to-world) * shank sensor-to-world",
        "knee_derivatives": "velocity from calibrated gyro Y difference; acceleration from central interiors, one-sided boundaries",
        "derivative_filter": "none",
        "timestamp_processing": "strict monotonic timestamps/sequences; interval tolerance 1%; no interpolation",
        "filter_beta": BETA,
        "orientation_initialization": "200 zero-gyro gradient iterations using first accelerometer sample; assumes stationary initial pose and common zero yaw",
        "initialization_iterations": INITIAL_TILT_ITERATIONS,
        "insole_processing": "device/API measurements passed through unchanged",
    }
    processed["synchronization"] = timing
    filters = {(side, segment): MadgwickIMU(beta=BETA)
               for side in ("left", "right") for segment in ("thigh", "shank")}
    nominal_dt = timing["expected_interval_s"]
    # Acquire tilt using only the initial measured acceleration. These iterations
    # initialize the state; they are not new samples or elapsed session time.
    for (side, segment), orientation in filters.items():
        _, accel = calibrate_imu(raw["samples"][0][side]["imu"][segment])
        if math.hypot(*accel) < 1e-12:
            raise ValueError("Initial tilt requires nonzero accelerometer magnitude")
        for _ in range(INITIAL_TILT_ITERATIONS):
            orientation.update(0.0, 0.0, 0.0, *accel, nominal_dt)
        check_quaternion(orientation.quaternion)
    samples = []
    for i, row in enumerate(raw["samples"]):
        sample = {"sequence": row["sequence"], "timestamp_s": row["timestamp_s"]}
        dt = row["timestamp_s"] - raw["samples"][i - 1]["timestamp_s"] if i else None
        for side in ("left", "right"):
            orientations = {}
            calibrated_gyros = {}
            for segment in ("thigh", "shank"):
                gyro, accel = calibrate_imu(row[side]["imu"][segment])
                calibrated_gyros[segment] = gyro
                orientation = filters[side, segment]
                if i:
                    orientation.update(*gyro, *accel, dt)
                check_quaternion(orientation.quaternion)
                orientations[f"{segment}_wxyz"] = orientation.quaternion
            relative = quaternion_relative(orientations["thigh_wxyz"], orientations["shank_wxyz"])
            check_quaternion(relative)
            angle = relative_flexion_y_rad(relative)
            if not math.isfinite(angle):
                raise ValueError("Nonfinite reconstructed knee flexion")
            orientations["relative_wxyz"] = relative
            sample[side] = {
                "orientation": orientations,
                "knee": {
                    "flexion_rad": angle,
                    "angular_velocity_rad_s": calibrated_gyros["shank"][1] - calibrated_gyros["thigh"][1],
                    "quality": {"valid": True, "reasons": []},
                },
                "insole": copy.deepcopy(row[side]["insole"]),
            }
        samples.append(sample)
    times = [row["timestamp_s"] for row in samples]
    for side in ("left", "right"):
        velocity = [row[side]["knee"]["angular_velocity_rad_s"] for row in samples]
        acceleration = finite_difference(velocity, times)
        for row, change in zip(samples, acceleration):
            row[side]["knee"]["angular_acceleration_rad_s2"] = change
    processed["samples"] = samples
    return processed


def validate_processed(raw, processed):
    """Validation-only ground-truth comparison after reconstruction is complete."""
    assert len(processed["samples"]) == len(raw["samples"])
    if raw["processing"]["stage"] == "raw_sensor_fixture":
        assert len(processed["samples"]) == round(raw["sampling"]["rate_hz"] * raw["sampling"]["duration_s"])
    print("Synthetic ideal fixture — not hardware validation.")
    print("\nKintra kinematic reconstruction validation")
    print("-------------------------------------------")
    print(f"Samples: {len(processed['samples'])}")
    print(f"Sampling rate: {processed['sampling']['rate_hz']} Hz")
    signals = (
        ("flexion_rad", "Flexion", "deg", False, 1.0),
        ("angular_velocity_rad_s", "Angular velocity", "deg/s", True, 1e-9),
        ("angular_acceleration_rad_s2", "Angular acceleration", "deg/s^2", True, 5.0),
    )
    has_truth = all("ground_truth" in row for row in raw["samples"])
    for side in ("left", "right"):
        for row in processed["samples"]:
            assert all(math.isfinite(value) for key, value in row[side]["knee"].items() if key != "quality")
            for q in row[side]["orientation"].values():
                assert all(math.isfinite(value) for value in q)
                assert math.isclose(math.hypot(*q), 1.0, abs_tol=1e-10)
        assert all(a[side]["insole"] == b[side]["insole"] for a, b in zip(raw["samples"], processed["samples"]))
        if has_truth:
            print(f"\n{side.upper()} KNEE")
            for key, label, units, absolute_peak, rmse_limit in signals:
                truth = [math.degrees(row["ground_truth"][f"{side}_knee_{key}"]) for row in raw["samples"]]
                estimates = [math.degrees(row[side]["knee"][key]) for row in processed["samples"]]
                errors = [estimate - true for estimate, true in zip(estimates, truth)]
                rmse = math.sqrt(sum(error**2 for error in errors) / len(errors))
                assert rmse < rmse_limit, f"{side} {label} ideal-test RMSE too large: {rmse}"
                true_peak = max(abs(value) for value in truth) if absolute_peak else max(truth)
                peak = max(abs(value) for value in estimates) if absolute_peak else max(estimates)
                peak_label = "peak absolute" if absolute_peak else "peak"
                print(f"\n{label}:")
                print(f"  RMSE: {rmse:.6f} {units}")
                print(f"  Max absolute error: {max(abs(error) for error in errors):.6f} {units}")
                print(f"  True {peak_label}: {true_peak:.6f} {units}")
                print(f"  Reconstructed {peak_label}: {peak:.6f} {units}")

    repeated = {side: [] for side in ("left", "right")}
    print("\nPer-landing kinematic comparison")
    for annotation in raw["annotations"]:
        if annotation["type"] != "synthetic_landing_window":
            continue
        indices = [i for i, row in enumerate(processed["samples"])
                   if annotation["start_s"] <= row["timestamp_s"] <= annotation["end_s"]]
        if not indices:
            continue
        print(f"\n{annotation['event_id']}")
        for side in ("left", "right"):
            metrics = {}
            print(f"  {side.capitalize()}:")
            for key, label, units, absolute_peak, _ in signals:
                values = [math.degrees(processed["samples"][i][side]["knee"][key]) for i in indices]
                peak = max(abs(value) for value in values) if absolute_peak else max(values)
                metrics[label] = peak
                if key == "flexion_rad":
                    metrics["ROM"] = max(values) - min(values)
                if has_truth:
                    truth = [math.degrees(raw["samples"][i]["ground_truth"][f"{side}_knee_{key}"]) for i in indices]
                    true_peak = max(abs(value) for value in truth) if absolute_peak else max(truth)
                    print(f"    {label} peak: true={true_peak:.6f}, estimated={peak:.6f} {units}")
                else:
                    print(f"    {label} peak: estimated={peak:.6f} {units}")
            repeated[side].append(metrics)
    print("\nAnnotated landing metric ranges")
    print("Ranges describe all annotated events; programmed changes are not reconstruction errors.")
    for side, events in repeated.items():
        print(f"\n{side.capitalize()}:")
        for label, units in (("Flexion", "deg"), ("ROM", "deg"),
                             ("Angular velocity", "deg/s"), ("Angular acceleration", "deg/s^2")):
            if events:
                values = [event[label] for event in events]
                print(f"  {label} range: {max(values) - min(values):.12g} {units}")
    print("\nTimestamp validation: PASS")
    print("Quaternion validation: PASS")
    print("Processed schema: PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_path", type=Path)
    args = parser.parse_args()
    raw = json.loads(args.session_path.read_text())
    processed = process_session(raw)
    validate_processed(raw, processed)
    stem = args.session_path.stem
    stem = stem[:-4] if stem.endswith("_raw") else stem
    output = ROOT / "data" / "processed" / f"{stem}_processed.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(processed, indent=2, allow_nan=False) + "\n")
    assert json.loads(output.read_text()) == json.loads(json.dumps(processed))
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
