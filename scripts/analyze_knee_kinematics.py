"""Summarize knee kinematics within balanced mock landing annotations."""
import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "mock" / "balanced.json"


# Backward-compatible aliases; no equations are owned by this CLI.
from event_biomechanics import summarize_knee
from bilateral_comparison import asymmetry_percent, comparison


def main():
    data = json.loads(DATA_PATH.read_text())
    print("Knee kinematics — balanced mock data (synthetic)")
    print("Landing windows include both start and end timestamps.")
    for landing in data["annotations"]:
        if landing["type"] != "synthetic_landing_window":
            continue
        start, end = landing["start_s"], landing["end_s"]
        samples = [sample for sample in data["samples"]
                   if start <= sample["timestamp_s"] <= end]
        print(f"\n{landing['event_id']} | {start:.2f}–{end:.2f} s | {len(samples)} samples")
        if not samples:
            print("  No samples in this window.")
            continue
        metrics = {}
        for side in ("left", "right"):
            result = summarize_knee(samples, side)
            metrics[side] = result
            print(f"  {side.capitalize()} knee:")
            print(f"    Minimum angle:                  {result['minimum_deg']:.2f} deg")
            print(f"    Maximum angle:                  {result['maximum_deg']:.2f} deg")
            print(f"    ROM:                            {result['rom_deg']:.2f} deg")
            print(f"    Peak absolute angular velocity: {result['peak_abs_velocity_deg_s']:.2f} deg/s")
            print(f"    Peak absolute acceleration:     {result['peak_abs_acceleration_deg_s2']:.2f} deg/s^2")


        left, right = metrics["left"], metrics["right"]
        comparisons = (
            ("ROM asymmetry", asymmetry_percent(left["rom_deg"], right["rom_deg"]), "%"),
            ("Peak flexion difference", comparison(left["maximum_deg"], right["maximum_deg"], False)["absolute_difference"], "deg"),
            ("Peak angular velocity asymmetry", asymmetry_percent(
                left["peak_abs_velocity_deg_s"], right["peak_abs_velocity_deg_s"]), "%"),
            ("Peak angular acceleration asymmetry", asymmetry_percent(
                left["peak_abs_acceleration_deg_s2"], right["peak_abs_acceleration_deg_s2"]), "%"),
        )
        print("\n  Bilateral comparison:")
        for label, value, unit in comparisons:
            displayed = f"{value:.2f} {unit}" if value is not None else "N/A (zero denominator)"
            print(f"    {label + ':':<38} {displayed}")


if __name__ == "__main__":
    main()
