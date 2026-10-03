"""Analyze Kintra mock landings without interpolating sensor data."""
import argparse
import json
import math
from pathlib import Path
from statistics import mean

from analyze_knee_kinematics import asymmetry_percent, summarize_knee
from baseline_simulation import Rules, window_reasons
from generate_mock_data import reconstructed_force, PRESSURE_FORCE_REL_TOL, PRESSURE_FORCE_ABS_TOL_N

ROOT = Path(__file__).resolve().parents[1]
CONTACT_THRESHOLD_N = 20.0
KINEMATIC_KEYS = (
    "minimum_deg", "maximum_deg", "rom_deg",
    "peak_abs_velocity_deg_s", "peak_abs_acceleration_deg_s2",
)
LOADING_KEYS = (
    "peak_plantar_normal_force_n", "peak_force_bw", "contact_time_s",
    "impulse_n_s", "average_loading_rate_n_s",
)
PRESSURE_KEYS = ("mean_medial_fraction", "mean_lateral_fraction", "cop_at_peak_force_m")


def unavailable(keys, reasons):
    return {**dict.fromkeys(keys), "quality": {"valid": False, "reasons": reasons}}


def valid_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def summarize_side(samples, side, body_weight_n, window_reasons, cells):
    motion = [sample[side]["knee"] for sample in samples]
    feet = [sample[side]["insole"] for sample in samples]
    knee_reasons = list(window_reasons)
    if any(not row["quality"]["valid"] or not all(valid_number(row[key]) for key in (
        "flexion_rad", "angular_velocity_rad_s", "angular_acceleration_rad_s2"
    )) for row in motion):
        knee_reasons.append("invalid_knee_samples")
    if any(not valid_number(row.get("timestamp_s", sample["timestamp_s"]))
           or abs(row.get("timestamp_s", sample["timestamp_s"]) - sample["timestamp_s"]) > 1e-8
           for sample, row in zip(samples, motion)):
        knee_reasons.append("unaligned_knee_timestamp")
    kinematics = (unavailable(KINEMATIC_KEYS, knee_reasons) if knee_reasons else {
        **summarize_knee(samples, side), "quality": {"valid": True, "reasons": []},
    })
    force_reasons = list(window_reasons)
    for sample, row in zip(samples, feet):
        force = row["plantar_normal_force_n"]
        if not row["quality"]["valid"] or not valid_number(force) or force < 0:
            force_reasons.extend(row["quality"]["reasons"] or ["invalid_insole_samples"])
        packet_time = row.get("timestamp_s", sample["timestamp_s"])
        if not valid_number(packet_time) or abs(packet_time - sample["timestamp_s"]) > 1e-8:
            force_reasons.append("unaligned_insole_timestamp")
        if row["quality"]["valid"]:
            try:
                reconstructed = reconstructed_force(row.get("cell_pressures_pa"), cells)
                if valid_number(force) and not math.isclose(reconstructed, force,
                        rel_tol=PRESSURE_FORCE_REL_TOL, abs_tol=PRESSURE_FORCE_ABS_TOL_N):
                    force_reasons.append("inconsistent_pressure_force")
            except ValueError as error:
                force_reasons.append(str(error))
    if force_reasons:
        reasons = sorted(set(force_reasons))
        return {"kinematics": kinematics, "loading": unavailable(LOADING_KEYS, reasons),
                "pressure": unavailable(PRESSURE_KEYS, reasons)}

    times = [sample["timestamp_s"] for sample in samples]
    forces = [row["plantar_normal_force_n"] for row in feet]
    peak_index = max(range(len(forces)), key=forces.__getitem__)
    peak = forces[peak_index]
    contacts = [i for i, force in enumerate(forces) if force > CONTACT_THRESHOLD_N]
    # Integrate the entire annotated window, including sub-threshold forces.
    impulse = sum((forces[i] + forces[i + 1]) / 2 * (times[i + 1] - times[i])
                  for i in range(len(samples) - 1))
    contact_time = 0.0
    loading_rate = None
    reasons = []
    if contacts:
        onset = contacts[0]
        # Each above-threshold sample starts a contact interval to the next sample.
        contact_time = sum(times[i + 1] - times[i] for i in contacts if i + 1 < len(times))
        if onset == 0 or contacts[-1] == len(times) - 1:
            contact_time = None
            reasons.append("contact_crosses_window_boundary")
        elif contacts != list(range(onset, contacts[-1] + 1)):
            reasons.append("multiple_contacts_in_window")
        elif times[peak_index] > times[onset]:
            loading_rate = (peak - forces[onset]) / (times[peak_index] - times[onset])
        else:
            reasons.append("zero_time_to_peak")
    else:
        reasons.append("no_contact")
    normalized_peak = peak / body_weight_n if body_weight_n is not None else None
    if body_weight_n is None:
        reasons.append("invalid_participant_mass")
    loading = dict(zip(LOADING_KEYS, (peak, normalized_peak, contact_time, impulse, loading_rate)))
    loading["quality"] = {"valid": not reasons, "reasons": reasons}

    pressure = dict.fromkeys(PRESSURE_KEYS)
    pressure_reasons = []
    for region in ("medial", "lateral"):
        values = [feet[i][f"{region}_fraction"] for i in contacts]
        if values and all(valid_number(value) and 0 <= value <= 1 for value in values):
            pressure[f"mean_{region}_fraction"] = mean(values)
        else:
            pressure_reasons.append(f"unavailable_{region}_fractions")
    cop = feet[peak_index]["cop_m"]
    if contacts and cop is not None and all(valid_number(cop[key]) for key in ("x_m", "y_m")):
        pressure["cop_at_peak_force_m"] = cop
    else:
        pressure_reasons.append("unavailable_cop_at_peak")
    pressure["quality"] = {"valid": not pressure_reasons, "reasons": pressure_reasons}
    return {"kinematics": kinematics, "loading": loading, "pressure": pressure}


def compare(left, right, key, difference=False):
    a, b = left[key], right[key]
    if a is None or b is None:
        return None
    return abs(a - b) if difference else asymmetry_percent(a, b)


def analyze_session(data, source_file=None):
    mass = data["participant"]["mass_kg"]
    body_weight = mass * 9.80665 if valid_number(mass) and mass > 0 else None
    analysis = {
        "analysis_version": "0.2.0", "session_id": data["session_id"],
        "activity": data["activity"], "synthetic": data["synthetic"],
        "source_file": source_file,
        "definitions": {
            "window": "inclusive start and end; sampled extrema",
            "force": "external plantar normal force; not validated ground-reaction or internal knee force",
            "body_weight_n": body_weight,
            "contact_threshold_n": CONTACT_THRESHOLD_N,
            "contact_time": "sum of sample intervals above threshold; no crossing interpolation",
            "impulse": "trapezoidal integration over the full annotated window, N*s",
            "loading_rate": "average dF/dt from first above-threshold sample to peak, N/s",
            "pressure_means": "arithmetic means over valid above-threshold contact samples",
            "asymmetry": "abs(left-right) / ((left+right)/2) * 100; null if denominator is zero",
            "signed_asymmetry": "100 * (right-left) / ((left+right)/2); positive means right greater",
            "missing_data": "no interpolation; incomplete signals yield null metrics with reasons",
        },
        "events": [],
    }
    stream_reasons = set()
    times = [row.get("timestamp_s") for row in data["samples"]]
    if any(not valid_number(t) for t in times):
        stream_reasons.add("invalid_timestamp")
    finite_times = [t for t in times if valid_number(t)]
    if any(b <= a for a, b in zip(finite_times, finite_times[1:])):
        stream_reasons.add("non_monotonic_timestamps")
    for annotation in data["annotations"]:
        if annotation["type"] != "synthetic_landing_window":
            continue
        start, end = annotation["start_s"], annotation["end_s"]
        samples = [row for row in data["samples"] if valid_number(row.get("timestamp_s"))
                   and valid_number(start) and valid_number(end) and start <= row["timestamp_s"] <= end]
        reasons = sorted(window_reasons(samples, start, end, data["sampling"]["rate_hz"],
                                        Rules(), stream_reasons))
        event = {"event_id": annotation["event_id"], "start_s": start, "end_s": end,
                 "sample_count": len(samples)}
        for side in ("left", "right"):
            event[side] = summarize_side(samples, side, body_weight, reasons, data["insole_geometry"][side])
        left, right = event["left"]["kinematics"], event["right"]["kinematics"]
        event["bilateral"] = {
            "kinematics": {
                "rom_asymmetry_percent": compare(left, right, "rom_deg"),
                "peak_flexion_difference_deg": compare(left, right, "maximum_deg", difference=True),
                "peak_angular_velocity_asymmetry_percent": compare(left, right, "peak_abs_velocity_deg_s"),
                "peak_angular_acceleration_asymmetry_percent": compare(left, right, "peak_abs_acceleration_deg_s2"),
            },
            "loading": {
                "peak_force_asymmetry_percent": compare(event["left"]["loading"], event["right"]["loading"], "peak_plantar_normal_force_n"),
                "impulse_asymmetry_percent": compare(event["left"]["loading"], event["right"]["loading"], "impulse_n_s"),
            },
        }
        # Preserve legacy absolute fields and expose direction explicitly.
        event["bilateral"]["signed_asymmetry_percent"] = {}
        for key, left_value, right_value in (
            ("rom_asymmetry_percent", left["rom_deg"], right["rom_deg"]),
            ("peak_force_asymmetry_percent", event["left"]["loading"]["peak_plantar_normal_force_n"],
             event["right"]["loading"]["peak_plantar_normal_force_n"]),
            ("impulse_asymmetry_percent", event["left"]["loading"]["impulse_n_s"],
             event["right"]["loading"]["impulse_n_s"]),
        ):
            denominator = ((left_value + right_value) / 2
                           if left_value is not None and right_value is not None else None)
            event["bilateral"]["signed_asymmetry_percent"][key] = (
                100 * (right_value - left_value) / denominator if denominator else None)
        analysis["events"].append(event)
    return analysis


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
    args = parser.parse_args()
    input_path = args.session_path
    output_path = ROOT / "data" / "derived" / f"{input_path.stem}_analysis.json"
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
