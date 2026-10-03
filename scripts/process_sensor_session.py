"""Kintra raw-to-processed session pipeline; currently ideal mounting only.

No ground truth participates in processing. Initialization assumes the first
sample is stationary and both sensor yaw references are zero. This is suitable
for the sagittal fixture, not an arbitrary 3-D anatomical angle calibration.
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
    if packet.get("quality", {}).get("valid", True) is not True:
        raise ValueError("Invalid IMU quality; interpolation is not supported")
    gyro = tuple(packet["gyro_rad_s"][axis] for axis in ("x", "y", "z"))
    accel = tuple(packet["accel_m_s2"][axis] for axis in ("x", "y", "z"))
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool)
               and math.isfinite(value) for value in gyro + accel):
        raise ValueError("Missing or nonfinite IMU sample; interpolation is not supported")
    return gyro, accel


def check_quaternion(q):
    if not all(math.isfinite(value) for value in q) or not math.isclose(math.hypot(*q), 1.0, abs_tol=1e-10):
        raise ValueError("Quaternion is nonfinite or not normalized")


def finite_difference(values, times):
    """Secant central differences inside; first-order one-sided at boundaries.

    Interior: (v[i+1]-v[i-1])/(t[i+1]-t[i-1]). Apply twice for acceleration.
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
    if "baseline_demo" in raw:
        processed["baseline_demo"] = copy.deepcopy(raw["baseline_demo"])
    processed["processing"] = {
        "stage": "post_sensor_processing", "orientation_filter": "Madgwick 6-DOF",
        "sensor_to_segment_calibration": "synthetic ideal alignment",
        "calibration_transform_wxyz": [1.0, 0.0, 0.0, 0.0],
        "hardware_calibration_requirement": "real hardware requires sensor-to-segment calibration",
        "knee_angle_source": "relative thigh/shank orientation; signed Y pitch",
        "relative_orientation": "conjugate(thigh sensor-to-world) * shank sensor-to-world",
        "knee_derivatives": "finite differences; central interiors, one-sided boundaries; applied twice",
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
            for segment in ("thigh", "shank"):
                packet = row[side]["imu"][segment]
                packet_time = packet.get("timestamp_s", row["timestamp_s"])
                if (not isinstance(packet_time, (int, float)) or isinstance(packet_time, bool)
                        or not math.isfinite(packet_time)
                        or not math.isclose(packet_time, row["timestamp_s"], rel_tol=0, abs_tol=1e-8)):
                    raise ValueError("Unaligned IMU timestamp; clock correction is not supported")
                gyro, accel = calibrate_imu(packet)
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
                "knee": {"flexion_rad": angle, "quality": {"valid": True, "reasons": []}},
                "insole": copy.deepcopy(row[side]["insole"]),
            }
        samples.append(sample)
    times = [row["timestamp_s"] for row in samples]
    for side in ("left", "right"):
        angles = [row[side]["knee"]["flexion_rad"] for row in samples]
        velocity = finite_difference(angles, times)
        acceleration = finite_difference(velocity, times)
        for row, speed, change in zip(samples, velocity, acceleration):
            row[side]["knee"].update(angular_velocity_rad_s=speed, angular_acceleration_rad_s2=change)
    processed["samples"] = samples
    return processed


def validate_processed(raw, processed):
    """Validation-only ground-truth comparison after reconstruction is complete."""
    assert len(processed["samples"]) == len(raw["samples"])
    print("Synthetic ideal fixture — not hardware validation.")
    print("\nKintra raw sensor pipeline validation")
    print("-------------------------------------")
    print(f"Samples: {len(processed['samples'])}")
    print(f"Sampling rate: {processed['sampling']['rate_hz']} Hz")
    for side in ("left", "right"):
        for row in processed["samples"]:
            assert all(math.isfinite(value) for key, value in row[side]["knee"].items() if key != "quality")
            for q in row[side]["orientation"].values():
                assert all(math.isfinite(value) for value in q)
                assert math.isclose(math.hypot(*q), 1.0, abs_tol=1e-10)
        assert all(a[side]["insole"] == b[side]["insole"] for a, b in zip(raw["samples"], processed["samples"]))
        if all("ground_truth" in row for row in raw["samples"]):
            truth = [math.degrees(row["ground_truth"][f"{side}_knee_flexion_rad"]) for row in raw["samples"]]
            reconstructed = [math.degrees(row[side]["knee"]["flexion_rad"]) for row in processed["samples"]]
            errors = [estimate - true for estimate, true in zip(reconstructed, truth)]
            rmse = math.sqrt(sum(error**2 for error in errors) / len(errors))
            assert rmse < 1.0, f"{side} ideal-test RMSE too large: {rmse}"
            print(f"\n{side.capitalize()} knee:")
            print(f"  True peak flexion: {max(truth):.2f} deg")
            print(f"  Reconstructed peak flexion: {max(reconstructed):.2f} deg")
            print(f"  RMSE: {rmse:.3f} deg")
            print(f"  Maximum absolute error: {max(abs(error) for error in errors):.3f} deg")
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
