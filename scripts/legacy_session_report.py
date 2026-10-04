"""Annotated-window compatibility policy and JSON shape, not metric equations.

Canonical contact reports retain their own windows. This adapter preserves the
historical inclusive annotations and quality contract for existing fixtures.
"""
from baseline_simulation import Rules, window_reasons
from event_biomechanics import summarize_side, valid_number, CONTACT_THRESHOLD_N
from bilateral_comparison import comparison


def bilateral_summary(left, right):
    fields = {
        'kinematics': {
            'rom_asymmetry_percent': ('rom_deg', 'asymmetry_percent'),
            'peak_flexion_difference_deg': ('maximum_deg', 'absolute_difference'),
            'peak_angular_velocity_asymmetry_percent': ('peak_abs_velocity_deg_s', 'asymmetry_percent'),
            'peak_angular_acceleration_asymmetry_percent': ('peak_abs_acceleration_deg_s2', 'asymmetry_percent'),
        },
        'loading': {
            'peak_force_asymmetry_percent': ('peak_plantar_normal_force_n', 'asymmetry_percent'),
            'impulse_asymmetry_percent': ('impulse_n_s', 'asymmetry_percent'),
        },
    }
    result = {group: {label: comparison(left[group][key], right[group][key])[field]
                      for label, (key, field) in names.items()} for group, names in fields.items()}
    result['signed_asymmetry_percent'] = {
        label: comparison(left[group][key], right[group][key])['signed_asymmetry_percent']
        for group, label, key in (('kinematics','rom_asymmetry_percent','rom_deg'),
            ('loading','peak_force_asymmetry_percent','peak_plantar_normal_force_n'),
            ('loading','impulse_asymmetry_percent','impulse_n_s'))}
    return result


def analyze_annotated_session(data, source_file=None):
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
        event["bilateral"] = bilateral_summary(event["left"], event["right"])
        analysis["events"].append(event)
    return analysis
