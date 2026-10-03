"""TEST ONLY: emulate ideal Kintra IMUs and balanced smart-insole packets."""
import copy
import json
import math
from pathlib import Path

from generate_mock_data import session

OUTPUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "mock_balanced_raw.json"


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
    return data


def to_raw_session(source):
    """Emulate ideal IMUs from synthetic extracted motion, retaining session context.

    This is a software test round-trip, not recovery of real raw measurements.
    Insole packets (including missing readings) pass through unchanged.
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
            raw["ground_truth"][f"{side}_knee_flexion_rad"] = angle
        raw_samples.append(raw)
    data["samples"] = raw_samples
    return data


def main():
    data = generate_fixture()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    print("Synthetic ideal raw sensor fixture — not hardware validation.")
    print(f"Generated {len(data['samples'])} samples at {data['sampling']['rate_hz']} Hz")
    print(f"Saved {OUTPUT}")


if __name__ == "__main__":
    main()
