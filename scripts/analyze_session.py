"""Compatibility CLI for annotated mock landings; canonical modules own metrics."""
import argparse
import json
from pathlib import Path

from legacy_session_report import analyze_annotated_session as analyze_session
from event_biomechanics import summarize_side, valid_number, unavailable, CONTACT_THRESHOLD_N, KINEMATIC_KEYS, LOADING_KEYS, PRESSURE_KEYS
from bilateral_comparison import comparison

ROOT = Path(__file__).resolve().parents[1]


def compare(left, right, key, difference=False):
    """Legacy scalar projection of the canonical comparison utility."""
    return comparison(left[key], right[key])['absolute_difference' if difference else 'asymmetry_percent']


def print_metrics(metrics):
    for key, value in metrics.items():
        if key == "quality":
            if value["reasons"]:
                print(f"      Quality: {', '.join(value['reasons'])}")
            continue
        label = {
            "minimum_deg": "Minimum knee flexion (deg)",
            "maximum_deg": "Peak knee flexion (deg)",
            "rom_deg": "ROM (deg)",
            "peak_abs_velocity_deg_s": "Peak absolute angular velocity (deg/s)",
            "peak_abs_acceleration_deg_s2": "Peak absolute angular acceleration (deg/s^2)",
            "peak_plantar_normal_force_n": "Peak plantar normal force (N)",
            "peak_force_bw": "Peak force (BW)",
            "contact_time_s": "Contact time (s)",
            "impulse_n_s": "Impulse (N*s)",
            "average_loading_rate_n_s": "Average loading rate (N/s)",
            "mean_medial_fraction": "Mean medial loading fraction (0-1)",
            "mean_lateral_fraction": "Mean lateral loading fraction (0-1)",
            "cop_at_peak_force_m": "COP at peak force",
            "rom_asymmetry_percent": "ROM asymmetry (%)",
            "peak_flexion_difference_deg": "Peak flexion difference (deg)",
            "peak_angular_velocity_asymmetry_percent": "Peak angular velocity asymmetry (%)",
            "peak_angular_acceleration_asymmetry_percent": "Peak angular acceleration asymmetry (%)",
            "peak_force_asymmetry_percent": "Peak force asymmetry (%)",
            "impulse_asymmetry_percent": "Impulse asymmetry (%)",
        }[key]
        if value is None:
            displayed = "unavailable"
        elif isinstance(value, dict):
            displayed = f"x={value['x_m']:.4f} m, y={value['y_m']:.4f} m"
        else:
            displayed = f"{value:.2f}"
        print(f"      {label}: {displayed}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_path", type=Path, help="Path to a mock session JSON file")
    parser.add_argument("--output", type=Path, help="Optional report destination")
    args = parser.parse_args()
    input_path = args.session_path
    output_path = args.output or ROOT / "data" / "derived" / f"{input_path.stem}_analysis.json"
    try:
        data = json.loads(input_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        parser.error(f"Cannot read session JSON: {error}")
    analysis = analyze_session(data, source_file=input_path.as_posix())
    print(f"Kintra session analysis: {analysis['session_id']} (synthetic={analysis['synthetic']})")
    print("External plantar normal force; contact threshold >20 N.")
    print("Impulse: full landing window. Loading rate: average onset-to-peak dF/dt.")
    for event in analysis["events"]:
        print(f"\n{event['event_id']} | {event['start_s']:.2f}–{event['end_s']:.2f} s")
        for side in ("left", "right", "bilateral"):
            print(f"  {side.capitalize()}:")
            for group, metrics in event[side].items():
                print(f"    {group.capitalize()}:")
                print_metrics(metrics)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(analysis, indent=2, allow_nan=False) + "\n")
    print(f"\nSaved {output_path}")


if __name__ == "__main__":
    main()
