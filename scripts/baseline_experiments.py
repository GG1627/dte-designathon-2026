"""Reproducible quality, participant, and history-size experiments."""
import copy
import math
import random
from statistics import median

import generate_mock_data as mock
from baseline_simulation import (
    SIDES, Rules, compare_evaluations, evaluation_fixture, extract_session,
    fit_baseline, generate_reference_history, summarize_session,
)

PROFILES = (
    {"id": "synthetic_athlete", "label": "Athlete A", "mass_kg": 75,
     "description": "Equal usual plantar loading; different left/right motion.",
     "force_scale": {"left": 1, "right": 1}, "flexion_degrees": {"left": 38, "right": 36}},
    {"id": "synthetic_right_favoring", "label": "Athlete B", "mass_kg": 75,
     "description": "Usually greater right loading and right flexion.",
     "force_scale": {"left": 1, "right": 1.12}, "flexion_degrees": {"left": 32, "right": 40}},
    {"id": "synthetic_lower_amplitude", "label": "Athlete C", "mass_kg": 75,
     "description": "Usually lower force and flexion amplitudes.",
     "force_scale": {"left": 0.88, "right": 0.88}, "flexion_degrees": {"left": 30, "right": 28}},
)
SCENARIOS = {
    "balanced": ("Balanced landing", "Complete fixture; all metrics available."),
    "right_load_bias": ("Greater right loading", "Complete fixture; right force/impulse exceed balanced by 10%."),
    "reference_bilateral_loading": ("Both sides: increased loading", "Synthetic measurements matched to the five-session reference, then force and impulse increased by 10%."),
    "reference_reduced_rom": ("Reduced movement range", "Synthetic measurements matched to the five-session reference, then ROM reduced by 20%."),
    "reference_right_loading": ("Right side: increased loading", "Synthetic measurements matched to the five-session reference, then right force and impulse increased by 14%."),
    "sensor_dropout": ("Left insole dropout", "Knee comparisons retained; two valid left force/impulse events."),
    "noisy_measurements": ("Measurement noise", "Seeded pressure noise and smooth angle perturbation; no values repaired."),
    "insole_clock_offset": ("Insole clock offset", "Left insole timestamps displaced by 30 ms; left force metrics rejected."),
    "placement_error": ("Placement check failed", "Flagged left-knee alignment failure; insole metrics retained."),
    "force_calibration_error": ("Force calibration failed", "Flagged left-insole calibration failure; knee metrics retained."),
    "boundary_gap": ("Gap at landing boundary", "Left insole missing at second landing onset; incomplete event rejected."),
    "missing_frame": ("Missing shared frame", "Missing second-landing boundary frame affects both sides and signals."),
    "unflagged_force_drift": ("Unflagged force drift", "Consistent pressure/force drift remains comparable; its cause cannot be inferred."),
}
HISTORY_SIZES = (3, 5, 10, 20)
REFERENCE_EXAMPLES = ("reference_bilateral_loading", "reference_reduced_rom", "reference_right_loading")


def rebuild_foot(foot, cells):
    """Recompute dependent fields from perturbed full-cell calibrated pressures."""
    pressures = foot["cell_pressures_pa"]
    force = mock.reconstructed_force(pressures, cells)
    foot["plantar_normal_force_n"] = force
    contact = force > mock.CONTACT_THRESHOLD_N
    foot["cop_m"] = ({axis: sum(p*c["area_m2"]*c[axis] for p,c in zip(pressures,cells))/force
                      for axis in ("x_m", "y_m")} if contact else None)
    foot["medial_fraction"] = (sum(p*c["area_m2"] for p,c in zip(pressures,cells)
                                   if c["region"] == "medial")/force if contact else None)
    foot["lateral_fraction"] = 1-foot["medial_fraction"] if contact else None
    foot["quality"] = {"valid": True, "reasons": [] if contact else ["below_contact_threshold"]}


def challenge_session(balanced, name, seed):
    """Produce signal faults/perturbations; expectations are metadata, never repairs."""
    data = copy.deepcopy(balanced)
    data["session_id"] = f"mock_{name}_001"
    data["scenario"] = name
    rng = random.Random(seed)
    for sample in data["samples"]:
        t = sample["timestamp_s"]
        if name == "noisy_measurements":
            for side in SIDES:
                knee = sample[side]["knee"]
                amplitude, omega = math.radians(0.2), 2*math.pi*5
                knee["flexion_rad"] += amplitude*math.sin(omega*t)
                knee["angular_velocity_rad_s"] += amplitude*omega*math.cos(omega*t)
                knee["angular_acceleration_rad_s2"] -= amplitude*omega**2*math.sin(omega*t)
                foot = sample[side]["insole"]
                foot["cell_pressures_pa"] = [p*rng.uniform(0.99, 1.01) for p in foot["cell_pressures_pa"]]
                rebuild_foot(foot, data["insole_geometry"][side])
        elif name == "insole_clock_offset":
            sample["left"]["insole"]["timestamp_s"] = t + 0.03
        elif name == "placement_error":
            sample["left"]["knee"]["flexion_rad"] += math.radians(4)
            sample["left"]["knee"]["quality"] = {"valid": False, "reasons": ["invalid_sensor_alignment"]}
        elif name == "force_calibration_error":
            foot = sample["left"]["insole"]
            foot["cell_pressures_pa"] = [p*1.08 for p in foot["cell_pressures_pa"]]
            rebuild_foot(foot, data["insole_geometry"]["left"])
            foot["quality"] = {"valid": False, "reasons": ["invalid_force_calibration"]}
        elif name == "boundary_gap" and 3 <= t < 3.04:
            sample["left"]["insole"] = mock.insole(t, "left", data["insole_geometry"]["left"], 1, True)
        elif name == "unflagged_force_drift":
            for side in SIDES:
                foot = sample[side]["insole"]
                foot["cell_pressures_pa"] = [p*1.08 for p in foot["cell_pressures_pa"]]
                rebuild_foot(foot, data["insole_geometry"][side])
    if name == "missing_frame":
        data["samples"] = [s for s in data["samples"] if s["timestamp_s"] != 3]
    if name == "noisy_measurements":
        data["processing"]["filter"] = "none; seeded synthetic noise"
    data = evaluation_fixture(data, 21)
    data["baseline_demo"]["challenge_seed"] = seed
    data["baseline_demo"]["expected_behavior"] = SCENARIOS[name][1]
    return data



def reference_example(balanced, summaries, profile, name, rules):
    """TEST ONLY: shape complete synthetic measurements around five-session medians.

    Targets are generation controls, never inputs to extraction/comparison/insight.
    A small pressure-shape adjustment matches impulse independently of peak force.
    All frames remain explicit, noise-free synthetic measurements.
    """
    data = evaluation_fixture(balanced, 21)
    data["session_id"] = f"mock_{name}_001__{profile['id']}"
    data["participant"] = {"id": profile["id"], "mass_kg": profile["mass_kg"]}
    data["baseline_demo"]["source_fixture_session_id"] = f"mock_{name}_001"
    data["baseline_demo"]["synthetic_reference_matched_measurements"] = True
    original = extract_session(data, rules)
    bw = profile["mass_kg"] * 9.80665
    for side in SIDES:
        targets = {metric: median(median(e["value"] for e in session["event_metrics"]
                                             if e["side"] == side and e["metric"] == metric
                                             and e["status"] == "accepted")
                                  for session in summaries[:5])
                   for metric in ("knee_rom_rad", "peak_plantar_normal_force_bw", "landing_window_impulse_bw_s")}
        movement_scale = 0.8 if name == "reference_reduced_rom" else 1.0
        load_scale = (1.1 if name == "reference_bilateral_loading" else
                      1.14 if name == "reference_right_loading" and side == "right" else 1.0)
        nominal_rom = next(e["value"] for e in original["event_metrics"]
                           if e["side"] == side and e["metric"] == "knee_rom_rad")
        scale = targets["knee_rom_rad"] * movement_scale / nominal_rom
        for row in data["samples"]:
            knee = row[side]["knee"]
            knee["flexion_rad"] = math.radians(8) + (knee["flexion_rad"] - math.radians(8)) * scale
            for key in ("angular_velocity_rad_s", "angular_acceleration_rad_s2"):
                knee[key] *= scale
        for event in data["annotations"]:
            window = [s for s in data["samples"] if event["start_s"] <= s["timestamp_s"] <= event["end_s"]]
            peak = max(s[side]["insole"]["plantar_normal_force_n"] for s in window)
            shape = [s[side]["insole"]["plantar_normal_force_n"] / peak for s in window]
            basis = [v * (1 - v) for v in shape]
            def integral(values):
                return sum((b["timestamp_s"] - a["timestamp_s"]) * (va + vb) / 2
                           for a, b, va, vb in zip(window, window[1:], values, values[1:]))
            target_peak = targets["peak_plantar_normal_force_bw"] * bw * load_scale
            target_impulse = targets["landing_window_impulse_bw_s"] * bw * load_scale
            adjustment = (target_impulse / target_peak - integral(shape)) / integral(basis)
            assert abs(adjustment) < 1  # Preserves nonnegative force and the chosen peak.
            for row, value, correction in zip(window, shape, basis):
                foot = row[side]["insole"]
                factor = target_peak * (value + adjustment * correction) / (peak * value) if value > 0 else 0
                foot["cell_pressures_pa"] = [p * factor for p in foot["cell_pressures_pa"]]
                rebuild_foot(foot, data["insole_geometry"][side])
    mock.verify_measurements(data)
    return data

def build_experiments(fixtures, seed=20261003, rules=Rules()):
    """Keep quality challenges held out and report prefix stability, not convergence claims."""
    challenge_streams = [challenge_session(fixtures["balanced"], name, seed + 100)
                         for name in SCENARIOS if name not in fixtures and name not in REFERENCE_EXAMPLES]
    inputs = [evaluation_fixture(fixtures[name], 21+i) for i,name in enumerate(fixtures)] + challenge_streams
    participants = []
    for profile in PROFILES:
        history = generate_reference_history(seed, session_count=20, participant=profile)
        summaries = [summarize_session(extract_session(s, rules), rules) for s in history]
        evaluation_summaries = []
        for original in inputs:
            data = copy.deepcopy(original)
            data["baseline_demo"]["source_fixture_session_id"] = original["session_id"]
            if profile["id"] != "synthetic_athlete":
                data["session_id"] += f"__{profile['id']}"
                data["baseline_demo"]["counterfactual_replay"] = True
            data["participant"] = {"id": profile["id"], "mass_kg": profile["mass_kg"]}
            evaluation_summaries.append(summarize_session(extract_session(data, rules), rules))
        for name in REFERENCE_EXAMPLES:
            example = reference_example(fixtures["balanced"], summaries, profile, name, rules)
            evaluation_summaries.append(summarize_session(extract_session(example, rules), rules))
        snapshots = []
        for count in HISTORY_SIZES:
            baseline = fit_baseline(summaries[:count], rules)
            evaluations = compare_evaluations(baseline, evaluation_summaries)
            snapshots.append({"reference_session_count": count, "baseline": baseline,
                              "evaluations": evaluations})
        participants.append({"profile": profile, "snapshots": snapshots})
    return {"schema_version": "baseline-experiments/1.0.0", "synthetic": True,
            "seed": seed, "scenarios": [{"id": k, "label": v[0], "description": v[1]}
                                        for k,v in SCENARIOS.items()],
            "participants": participants}, challenge_streams


def app_snapshot(experiments):
    """Lean, generated results only: never bundle raw streams or refit in React."""
    result = {k: experiments[k] for k in ("schema_version", "synthetic", "seed", "scenarios")}
    result["participants"] = []
    for participant in experiments["participants"]:
        snapshots = []
        for snapshot in participant["snapshots"]:
            baseline = snapshot["baseline"]
            snapshots.append({"reference_session_count": snapshot["reference_session_count"],
                              "baseline_version": baseline["version"], "rules": baseline["rules"],
                              "measurement_reliability": baseline["measurement_reliability"],
                              "metrics": baseline["metrics"],
                              "evaluations": [{"session_id": e["session_id"],
                                               "scenario": next(s["id"] for s in experiments["scenarios"]
                                                                if e["metadata"]["source_fixture_session_id"] == f"mock_{s['id']}_001"),
                                               "comparisons": e["comparisons"], "insights": e["insights"],
                                               "session_metrics": e["session_metrics"]}
                                              for e in snapshot["evaluations"]]})
        result["participants"].append({"profile": participant["profile"], "snapshots": snapshots})
    return result
