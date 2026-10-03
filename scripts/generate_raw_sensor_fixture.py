"""TEST ONLY: emulate ideal Kintra IMUs and controlled smart-insole packets."""
import argparse
import copy
import json
import math
from pathlib import Path

from generate_mock_data import insole, knee, session

OUTPUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "mock_training_20_landings_raw.json"


def imu_packet(angle, angular_velocity):
    """Sensor-to-world +Y rotation; specific force is opposite physical gravity.

    X forward, Y left, Z up. Inverse rotation of world +g Z gives local accel.
    """
    g = 9.80665
    return {
        "accel_m_s2": {"x": -g * math.sin(angle), "y": 0.0, "z": g * math.cos(angle)},
        "gyro_rad_s": {"x": 0.0, "y": angular_velocity, "z": 0.0},
    }


def generate_fixture():
    # Reuse the existing deterministic generator in memory; never rewrite mocks.
    data = to_raw_session(session("balanced"))
    data["session_id"] = "mock_balanced_raw_001"
    assert len(data["samples"]) == 600
    return data


def to_raw_session(source):
    """TEST ONLY: ideal IMU emulation, retaining baseline context and insole faults.

    This synthetic round-trip is not recovery of real raw measurements.
    """
    if source.get("synthetic") is not True:
        raise ValueError("Ideal IMU emulation requires explicitly synthetic input")
    data = copy.deepcopy(source)
    data["processing"] = {
        "stage": "raw_sensor_fixture", "synthetic": True,
        "imu_model": "ideal gravity specific force plus analytic angular velocity",
        "coordinates": "X forward, Y left, Z up; positive flexion about +Y",
        "gravity": "physical gravity -Z; stationary accelerometer specific force +Z",
        "noise": "none", "bias": "none", "translational_acceleration": "none",
        "sensor_to_segment_alignment": "ideal",
        "timestamp_model": "perfect synchronized synthetic clock",
        "initialization_assumption": "initial sample is stationary; common yaw is zero",
    }
    raw_samples = []
    for sample in data["samples"]:
        raw = {"sequence": sample["sequence"], "timestamp_s": sample["timestamp_s"],
               "ground_truth": {}}
        for side in ("left", "right"):
            motion = sample[side]["knee"]
            if motion.get("quality", {}).get("valid") is not True:
                raise ValueError("Cannot emulate valid IMUs from invalid knee motion")
            angle = motion["flexion_rad"]
            raw[side] = {
                "imu": {"thigh": imu_packet(0.0, 0.0),
                        "shank": imu_packet(angle, motion["angular_velocity_rad_s"])},
                "insole": sample[side]["insole"],
            }
            # Analytic measurements retained only for post-processing validation.
            for key in ("flexion_rad", "angular_velocity_rad_s", "angular_acceleration_rad_s2"):
                raw["ground_truth"][f"{side}_knee_{key}"] = motion[key]
        raw_samples.append(raw)
    data["samples"] = raw_samples
    return data


def training_events():
    events = []
    for number in range(1, 21):
        flexion_scale = left_force_scale = right_force_scale = 1.0
        if number <= 5:
            phase = "baseline"
        elif number <= 10:
            phase = "higher_loading"
            left_force_scale = right_force_scale = 1.0 + 0.02 * (number - 5)
        elif number <= 15:
            phase = "reduced_flexion"
            flexion_scale = 1.0 - 0.05 * (number - 11)
        else:
            phase = "right_load_bias"
            right_force_scale = 1.0 + (0.02, 0.05, 0.08, 0.11, 0.14)[number - 16]
        events.append({
            "event_id": f"landing_{number}", "phase": phase,
            "start_s": float(2 * number - 1), "end_s": 2 * number - 1 + 0.6,
            "programmed": {"left_flexion_scale": flexion_scale, "right_flexion_scale": flexion_scale,
                           "left_force_scale": left_force_scale, "right_force_scale": right_force_scale},
        })
    return events


def training_motion(t, side, events):
    """Use the shared Gaussian motion model with the programmed amplitudes."""
    landings = [{
        "start_s": event["start_s"], "flexion_offset_s": {"left": 0.25, "right": 0.25},
        "flexion_sigma_s": 0.18,
        "flexion_amplitude_rad": {
            segment_side: math.radians(38 if segment_side == "left" else 36)
            * event["programmed"][f"{segment_side}_flexion_scale"]
            for segment_side in ("left", "right")
        },
    } for event in events]
    return {key: value for key, value in knee(t, side, landings).items() if key != "quality"}


def generate_training_fixture():
    # Existing balanced fixture creation remains available; reuse metadata only.
    data = generate_fixture()
    events = training_events()
    rate, duration = 100, 41
    data.update(session_id="mock_training_20_landings_raw_001",
                activity="bilateral_landing_series", scenario="training_20_landings")
    data["sampling"].update(rate_hz=rate, duration_s=duration)
    data["phases"] = [
        {"name": name, "landings": list(range(first, first + 5))}
        for name, first in (("baseline", 1), ("higher_loading", 6),
                            ("reduced_flexion", 11), ("right_load_bias", 16))
    ]
    data["annotations"] = [
        {"event_id": event["event_id"], "type": "synthetic_landing_window",
         "start_s": event["start_s"], "end_s": event["end_s"]}
        for event in events
    ]
    for event in events:
        event["expected"] = {}
        for side in ("left", "right"):
            event["expected"][f"{side}_peak_flexion_rad"] = training_motion(event["start_s"] + 0.25, side, events)["flexion_rad"]
            event["expected"][f"{side}_peak_force_n"] = insole(
                1.3, side, data["insole_geometry"][side], event["programmed"][f"{side}_force_scale"], False
            )["plantar_normal_force_n"]
    data["ground_truth"] = {"events": events, "purpose": "validation only; never used in sensor processing"}
    samples = []
    for sequence in range(rate * duration):
        t = sequence / rate
        contact = next((event for event in events if event["start_s"] <= t <= event["end_s"]), None)
        row = {"sequence": sequence, "timestamp_s": t, "ground_truth": {}}
        for side in ("left", "right"):
            motion = training_motion(t, side, events)
            # Map this contact to the existing model's first contact at 1.0 s.
            local_time = t - contact["start_s"] + 1.0 if contact else -1.0
            force_scale = contact["programmed"][f"{side}_force_scale"] if contact else 1.0
            row[side] = {
                "imu": {"thigh": imu_packet(0.0, 0.0),
                        "shank": imu_packet(motion["flexion_rad"], motion["angular_velocity_rad_s"])},
                "insole": insole(local_time, side, data["insole_geometry"][side], force_scale, False),
            }
            for key, value in motion.items():
                row["ground_truth"][f"{side}_knee_{key}"] = value
        samples.append(row)
    data["samples"] = samples
    assert len(data["annotations"]) == 20
    assert len(samples) == rate * duration == 4100
    assert all(b["timestamp_s"] > a["timestamp_s"] for a, b in zip(samples, samples[1:]))
    assert all(math.isfinite(value) for row in samples for side in ("left", "right")
               for packet in row[side]["imu"].values() for vector in packet.values() for value in vector.values())
    return data


def validate_training_output(processed_path):
    """Scenario assertions belong to the test generator, not production processing."""
    from analyze_session import analyze_session
    from process_sensor_session import process_session

    raw = json.loads(OUTPUT.read_text())
    processed = json.loads(processed_path.read_text())
    without_truth = copy.deepcopy(raw)
    without_truth.pop("ground_truth")
    for row in without_truth["samples"]:
        row.pop("ground_truth")
    assert json.loads(json.dumps(process_session(without_truth))) == processed
    assert len(processed["samples"]) == 4100
    for row in processed["samples"]:
        for side in ("left", "right"):
            assert all(math.isfinite(value) for key, value in row[side]["knee"].items() if key != "quality")
            assert all(math.isclose(math.hypot(*q), 1.0, abs_tol=1e-10)
                       for q in row[side]["orientation"].values())
    events = analyze_session(processed, source_file=str(processed_path))["events"]
    assert len(events) == 20
    specifications = raw["ground_truth"]["events"]
    for event, specification in zip(events, specifications):
        assert event["event_id"] == specification["event_id"]
        for side in ("left", "right"):
            assert math.isclose(event[side]["loading"]["peak_plantar_normal_force_n"], specification["expected"][f"{side}_peak_force_n"], rel_tol=1e-12)
            assert abs(event[side]["kinematics"]["maximum_deg"] - math.degrees(specification["expected"][f"{side}_peak_flexion_rad"])) < 0.2
    def values(group, side, category, key):
        return [event[side][category][key] for event in group]
    def increasing(numbers):
        return all(b > a for a, b in zip(numbers, numbers[1:]))
    def decreasing(numbers):
        return all(b < a for a, b in zip(numbers, numbers[1:]))
    for side in ("left", "right"):
        baseline = values(events[:5], side, "kinematics", "maximum_deg")
        assert max(baseline) - min(baseline) < 0.2
        force = values(events[:5], side, "loading", "peak_force_bw")
        assert max(force) - min(force) < 1e-12
        unchanged_angle = values(events[5:10], side, "kinematics", "maximum_deg")
        assert max(unchanged_angle) - min(unchanged_angle) < 0.2
        for key in ("peak_force_bw", "impulse_n_s", "average_loading_rate_n_s"):
            assert increasing(values(events[5:10], side, "loading", key))
        for key in ("maximum_deg", "rom_deg", "peak_abs_velocity_deg_s", "peak_abs_acceleration_deg_s2"):
            assert decreasing(values(events[10:15], side, "kinematics", key))
        assert all(math.isclose(value, 1.7) for value in values(events[10:15], side, "loading", "peak_force_bw"))
        assert all(abs(value - baseline[0]) < 0.2 for value in values(events[15:], side, "kinematics", "maximum_deg"))
    assert all(abs(event["bilateral"]["loading"]["peak_force_asymmetry_percent"]) < 1e-10 for event in events[:15])
    assert all(math.isclose(value, 1.7) for value in values(events[15:], "left", "loading", "peak_force_bw"))
    assert increasing(values(events[15:], "right", "loading", "peak_force_bw"))
    assert increasing([event["bilateral"]["loading"]["peak_force_asymmetry_percent"] for event in events[15:]])
    print("Synthetic programmed trend validation — not hardware validation.")
    print("landing | phase           | left flex deg | right flex deg | left BW | right BW | force asym %")
    previous_phase = None
    for event, specification in zip(events, specifications):
        phase = specification["phase"]
        if phase != previous_phase:
            print(f"\n{phase.upper()}")
            previous_phase = phase
        print(f"{event['event_id']:10} | {phase:15} | "
              f"{event['left']['kinematics']['maximum_deg']:13.6f} | "
              f"{event['right']['kinematics']['maximum_deg']:14.6f} | "
              f"{event['left']['loading']['peak_force_bw']:7.3f} | "
              f"{event['right']['loading']['peak_force_bw']:8.3f} | "
              f"{event['bilateral']['loading']['peak_force_asymmetry_percent']:12.6f}")
    print("\nPASS: all phase trends, finite signals, normalized quaternions, and ground-truth independence.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("balanced", "training_20_landings"),
                        default="training_20_landings", help="Fixture to generate; existing training default retained")
    parser.add_argument("--validate-processed", type=Path, help="Validate the generated training fixture after processing")
    args = parser.parse_args()
    if args.validate_processed:
        validate_training_output(args.validate_processed)
        return
    data = generate_fixture() if args.scenario == "balanced" else generate_training_fixture()
    output = OUTPUT.with_name("mock_balanced_raw.json") if args.scenario == "balanced" else OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    assert len(json.loads(output.read_text())["samples"]) == len(data["samples"])
    print("Synthetic ideal raw sensor fixture — not hardware validation.")
    print(f"Generated {len(data['samples'])} samples at {data['sampling']['rate_hz']} Hz; "
          f"{len(data['annotations'])} landings, {data['sampling']['duration_s']} seconds")
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
