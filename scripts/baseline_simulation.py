"""Standalone synthetic history, metric extraction, fitting, and comparison.

No contact detector or medical inference. Functions do not write files.
"""
import copy
import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from statistics import median

import generate_mock_data as mock

GENERATOR_VERSION = "baseline-history/1.1.0"
PROCESSING_VERSION = "annotated-landing-metrics/1.1.0"
BASELINE_VERSION = "session-median-mad/1.0.0"
CONFIGURATION_ID = "mock_ideal_bilateral_knee_insole_v1"
METRICS = {
    "knee_rom_rad": "rad",
    "peak_plantar_normal_force_bw": "BW",
    "landing_window_impulse_bw_s": "BW*s",
}
SIDES = ("left", "right")
CONTEXT_FIELDS = ("participant_id", "joint", "activity", "configuration_id",
                  "configuration_signature", "processing_version", "processing_signature")


@dataclass(frozen=True)
class Rules:
    """Configurable demonstration rules, not clinically validated requirements."""
    min_valid_events: int = 3
    min_reference_sessions: int = 5
    timestamp_abs_tol_s: float = 1e-8
    mad_abs_tol: float = 1e-12
    mad_rel_tol: float = 1e-12

    def __post_init__(self):
        for count in (self.min_valid_events, self.min_reference_sessions):
            if isinstance(count, bool) or not isinstance(count, int) or count < 1:
                raise ValueError("Minimum counts must be positive integers")
        for tolerance in (self.timestamp_abs_tol_s, self.mad_abs_tol, self.mad_rel_tol):
            if not finite(tolerance) or tolerance < 0:
                raise ValueError("Tolerances must be finite and nonnegative")


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def demo_metadata(role, index, recorded_at, seed=None):
    return {"schema_version": "1.0.0", "role": role, "joint": "knee",
            "chronological_index": index, "recorded_at": recorded_at,
            "configuration_id": CONFIGURATION_ID,
            "generation_seed": seed, "generator_version": GENERATOR_VERSION if seed is not None
            else "legacy-mock-generator/0.1.0",
            "synthetic_ordering": True}


def generate_reference_history(seed=20261003, session_count=5, participant=None):
    """Seeded comparable sessions; optional synthetic participant parameters."""
    if not isinstance(session_count, int) or session_count < 1:
        raise ValueError("session_count must be a positive integer")
    participant = participant or {"id": "synthetic_athlete", "mass_kg": 75,
                                  "force_scale": {"left": 1, "right": 1},
                                  "flexion_degrees": {"left": 38, "right": 36}}
    history = []
    for index in range(session_count):
        session_seed = seed + index
        rng = random.Random(session_seed)
        force_session = rng.uniform(0.965, 1.035)
        flexion_session = rng.uniform(0.97, 1.03)
        duration_session = rng.uniform(-0.025, 0.025)
        timing_session = rng.uniform(-0.015, 0.015)
        landings = []
        for event in range(6):
            start = 1.0 + 2 * event
            duration = round(0.6 + duration_session + rng.uniform(-0.025, 0.025), 2)
            landing = {"start_s": start, "end_s": round(start + duration, 2),
                       "flexion_sigma_s": 0.18 * duration / 0.6,
                       "force_scale": {}, "flexion_amplitude_rad": {}, "flexion_offset_s": {}}
            for side in SIDES:
                nominal_degrees = participant["flexion_degrees"][side]
                landing["force_scale"][side] = (force_session * rng.uniform(0.975, 1.025)
                    * participant["force_scale"][side] * participant["mass_kg"] / mock.MASS_KG)
                landing["flexion_amplitude_rad"][side] = (
                    math.radians(nominal_degrees) * flexion_session * rng.uniform(0.975, 1.025))
                landing["flexion_offset_s"][side] = (
                    duration * 0.25 / 0.6 + timing_session + rng.uniform(-0.01, 0.01))
            landings.append(landing)
        data = mock.session("reference_history", landings=landings, duration_s=12)
        data["session_id"] = f"mock_reference_{index + 1:03d}"
        if participant["id"] != "synthetic_athlete":
            data["session_id"] += f"__{participant['id']}"
        data["participant"] = {"id": participant["id"], "mass_kg": participant["mass_kg"]}
        day = date(2026, 9, 1) + timedelta(days=index)
        data["baseline_demo"] = demo_metadata("reference", index + 1,
                                              f"{day.isoformat()}T12:00:00Z", session_seed)
        data["baseline_demo"]["waveforms"] = landings  # Ground truth, never used to extract metrics.
        data["baseline_demo"]["participant_parameters"] = participant
        mock.verify_measurements(data)
        history.append(data)
    return history


def evaluation_fixture(data, index):
    """Attach explicit assumed context to a COPY of a legacy evaluation fixture."""
    if data.get("schema_version") != mock.SCHEMA_VERSION or data.get("synthetic") is not True:
        raise ValueError("Only the existing synthetic 0.1.0 fixtures are supported by this adapter")
    result = copy.deepcopy(data)
    result["baseline_demo"] = demo_metadata("evaluation", index, "2026-10-03T12:00:00Z")
    result["baseline_demo"]["configuration_assumption"] = (
        "Legacy fixture explicitly assigned the ideal mock configuration; fingerprint checked")
    return result


def context(data, rules):
    metadata = data["baseline_demo"]
    # A matching ID alone is insufficient: geometry, extraction/calibration, sources,
    # schema, and sampling settings must also match. No scenario label is consulted.
    processing = dict(data["processing"])
    # Descriptions of synthetic noise are not a change to the actual filter method.
    if isinstance(processing.get("filter"), str):
        processing["filter"] = processing["filter"].split(";")[0].strip()
    configuration = {"schema_version": data["schema_version"],
                     "rate_hz": data["sampling"]["rate_hz"],
                     "clock": data["sampling"]["clock"],
                     "processing": processing, "sources": data["sources"],
                     "insole_geometry": data["insole_geometry"]}
    return {"participant_id": data["participant"]["id"], "joint": metadata["joint"],
            "activity": data["activity"], "configuration_id": metadata["configuration_id"],
            "configuration_signature": digest(configuration),
            "processing_version": PROCESSING_VERSION,
            "processing_signature": digest({"min_valid_events": rules.min_valid_events,
                                             "timestamp_abs_tol_s": rules.timestamp_abs_tol_s,
                                             "pressure_force_rel_tol": mock.PRESSURE_FORCE_REL_TOL,
                                             "pressure_force_abs_tol_n": mock.PRESSURE_FORCE_ABS_TOL_N})}


def window_reasons(samples, start, end, rate, rules, stream_reasons):
    reasons = set(stream_reasons)
    if not finite(start) or not finite(end) or end <= start:
        return reasons | {"invalid_annotation_bounds"}
    if not finite(rate) or rate <= 0:
        return reasons | {"invalid_sampling_rate"}
    if len(samples) < 2:
        return reasons | {"incomplete_window"}
    tolerance = rules.timestamp_abs_tol_s
    if (not math.isclose(samples[0]["timestamp_s"], start, rel_tol=0, abs_tol=tolerance)
            or not math.isclose(samples[-1]["timestamp_s"], end, rel_tol=0, abs_tol=tolerance)):
        reasons.add("incomplete_window_boundaries")
    for a, b in zip(samples, samples[1:]):
        if not math.isclose(b["timestamp_s"] - a["timestamp_s"], 1 / rate,
                            rel_tol=0, abs_tol=tolerance):
            reasons.add("sample_discontinuity")
        if (not isinstance(a.get("sequence"), int) or isinstance(a.get("sequence"), bool)
                or not isinstance(b.get("sequence"), int) or isinstance(b.get("sequence"), bool)
                or b["sequence"] != a["sequence"] + 1):
            reasons.add("sequence_discontinuity")
    return reasons


def signal_reasons(signal, label):
    if signal.get("quality", {}).get("valid") is True:
        return set()
    return {f"invalid_{label}_sample", *signal.get("quality", {}).get("reasons", [])}


def extract_session(data, rules=Rules()):
    """Extract only event metrics; preserve failures and signal-specific provenance."""
    samples = data["samples"]
    stream_reasons = set()
    if any(not finite(s.get("timestamp_s")) for s in samples):
        stream_reasons.add("invalid_timestamp")
    times = [s["timestamp_s"] for s in samples if finite(s.get("timestamp_s"))]
    if any(b <= a for a, b in zip(times, times[1:])):
        stream_reasons.add("non_monotonic_timestamps")
    mass = data["participant"].get("mass_kg")
    bw = mass * 9.80665 if finite(mass) and mass > 0 else None
    events = []
    annotations = [a for a in data["annotations"] if a.get("type") == "synthetic_landing_window"]
    ids = [a["event_id"] for a in annotations]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate annotation event IDs")
    for annotation in annotations:
        start, end = annotation.get("start_s"), annotation.get("end_s")
        window = [s for s in samples if finite(s.get("timestamp_s"))
                  and finite(start) and finite(end) and start <= s["timestamp_s"] <= end]
        common = window_reasons(window, start, end, data["sampling"].get("rate_hz"),
                                rules, stream_reasons)
        for side in SIDES:
            knee_reasons, force_reasons = set(common), set(common)
            if bw is None:
                force_reasons.add("invalid_participant_mass")
            angles, forces = [], []
            cells = data["insole_geometry"][side]
            for sample in window:
                knee = sample.get(side, {}).get("knee", {})
                knee_reasons.update(signal_reasons(knee, "knee"))
                knee_time = knee.get("timestamp_s", sample["timestamp_s"])
                if not finite(knee_time) or abs(knee_time - sample["timestamp_s"]) > rules.timestamp_abs_tol_s:
                    knee_reasons.add("unaligned_knee_timestamp")
                angle = knee.get("flexion_rad")
                if not finite(angle):
                    knee_reasons.add("missing_or_nonfinite_flexion")
                else:
                    angles.append(angle)
                foot = sample.get(side, {}).get("insole", {})
                force_reasons.update(signal_reasons(foot, "insole"))
                foot_time = foot.get("timestamp_s", sample["timestamp_s"])
                if not finite(foot_time) or abs(foot_time - sample["timestamp_s"]) > rules.timestamp_abs_tol_s:
                    force_reasons.add("unaligned_insole_timestamp")
                force = foot.get("plantar_normal_force_n")
                if not finite(force) or force < 0:
                    force_reasons.add("missing_or_invalid_force")
                else:
                    forces.append(force)
                if foot.get("quality", {}).get("valid") is True:
                    try:
                        reconstructed = mock.reconstructed_force(foot.get("cell_pressures_pa"), cells)
                        if finite(force) and not math.isclose(
                                reconstructed, force, rel_tol=mock.PRESSURE_FORCE_REL_TOL,
                                abs_tol=mock.PRESSURE_FORCE_ABS_TOL_N):
                            force_reasons.add("inconsistent_pressure_force")
                    except ValueError as error:
                        force_reasons.add(str(error))
            values = {}
            if not knee_reasons:
                values["knee_rom_rad"] = max(angles) - min(angles)
            if not force_reasons:
                values["peak_plantar_normal_force_bw"] = max(forces) / bw
                values["landing_window_impulse_bw_s"] = sum(
                    (b["timestamp_s"] - a["timestamp_s"]) * (fa + fb) / 2
                    for a, b, fa, fb in zip(window, window[1:], forces, forces[1:])) / bw
            for name, unit in METRICS.items():
                reasons = knee_reasons if name == "knee_rom_rad" else force_reasons
                value = values.get(name)
                if value is not None and not finite(value):
                    reasons = reasons | {"nonfinite_metric"}
                    value = None
                events.append({"event_id": annotation["event_id"], "side": side,
                               "metric": name, "unit": unit, "start_s": start, "end_s": end,
                               "sample_count": len(window), "value": value,
                               "status": "rejected" if reasons else "accepted",
                               "reasons": sorted(reasons),
                               "source_ids": data["sources"][side][
                                   "knee" if name == "knee_rom_rad" else "insole"]})
    return {"schema_version": "baseline-results/1.0.0", "session_id": data["session_id"],
            "synthetic": data["synthetic"], "metadata": data["baseline_demo"],
            "context": context(data, rules),
            "processing": {"version": PROCESSING_VERSION, "event_method": "synthetic_annotation_window",
                           "endpoints": "inclusive", "impulse_method": "trapezoidal_actual_timestamps",
                           "rules": asdict(rules), "pressure_force_rel_tol": mock.PRESSURE_FORCE_REL_TOL,
                           "pressure_force_abs_tol_n": mock.PRESSURE_FORCE_ABS_TOL_N},
            "event_metrics": events}


def summarize_session(extracted, rules=Rules()):
    """Equal-weight event medians, with independent eligibility for each metric."""
    if extracted["processing"]["rules"]["min_valid_events"] != rules.min_valid_events:
        raise ValueError("Session summary rules differ from the extraction context")
    summaries = []
    for side in SIDES:
        for name, unit in METRICS.items():
            results = [e for e in extracted["event_metrics"] if e["side"] == side and e["metric"] == name]
            valid = [e for e in results if e["status"] == "accepted"]
            eligible = len(valid) >= rules.min_valid_events
            summaries.append({"side": side, "metric": name, "unit": unit,
                              "status": "accepted" if eligible else "insufficient_valid_events",
                              "median": median(e["value"] for e in valid) if eligible else None,
                              "valid_event_count": len(valid), "total_event_count": len(results),
                              "valid_event_ids": [e["event_id"] for e in valid],
                              "reasons": [] if eligible else ["insufficient_valid_events"],
                              "rejected_events": [{"event_id": e["event_id"], "reasons": e["reasons"]}
                                                  for e in results if e["status"] == "rejected"]})
    return {**extracted, "session_metrics": summaries}


def group_key(ctx, side, metric):
    return tuple(ctx[field] for field in CONTEXT_FIELDS) + (side, metric)


def require_unique_sessions(sessions):
    ids = [s["session_id"] for s in sessions]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate session IDs")


def fit_baseline(reference_sessions, rules=Rules()):
    """Fit reference-only distributions; every eligible session has equal weight."""
    require_unique_sessions(reference_sessions)
    groups = {}
    for session in reference_sessions:
        if session["metadata"]["role"] != "reference":
            raise ValueError("Baseline fitting accepts reference sessions only")
        if session["processing"]["rules"]["min_valid_events"] != rules.min_valid_events:
            raise ValueError("Inconsistent reference aggregation rules")
        for metric in session["session_metrics"]:
            key = group_key(session["context"], metric["side"], metric["metric"])
            groups.setdefault(key, []).append((session, metric))
    fitted = []
    for entries in groups.values():
        first_session, first_metric = entries[0]
        eligible = [(s, m) for s, m in entries if m["status"] == "accepted"]
        ready = len(eligible) >= rules.min_reference_sessions
        center = median(m["median"] for _, m in eligible) if ready else None
        dispersion = median(abs(m["median"] - center) for _, m in eligible) if ready else None
        fitted.append({"context": first_session["context"], "side": first_metric["side"],
                       "metric": first_metric["metric"], "unit": first_metric["unit"],
                       "status": "ready" if ready else "insufficient_reference_history",
                       "median": center, "mad": dispersion,
                       "eligible_session_count": len(eligible), "total_session_count": len(entries),
                       "contributing_event_count": sum(m["valid_event_count"] for _, m in eligible),
                       "contributing_session_ids": [s["session_id"] for s, _ in eligible],
                       "session_summaries": [{"session_id": s["session_id"], "median": m["median"],
                                              "valid_event_count": m["valid_event_count"],
                                              "total_event_count": m["total_event_count"],
                                              "status": m["status"], "reasons": m["reasons"],
                                              "rejected_events": m["rejected_events"]} for s, m in entries],
                       "reasons": [] if ready else ["insufficient_reference_history"]})
    return {"schema_version": "baseline-results/1.0.0", "synthetic": True,
            "version": BASELINE_VERSION, "aggregation": "median_of_reference_session_medians",
            "dispersion": "median_absolute_deviation_of_session_medians", "rules": asdict(rules),
            "reference_session_ids": [s["session_id"] for s in reference_sessions], "metrics": fitted}


def compare_evaluations(baseline, evaluation_sessions):
    """Compare without mutating the baseline; reject role mistakes, duplicates, overlap."""
    require_unique_sessions(evaluation_sessions)
    if set(baseline["reference_session_ids"]) & {s["session_id"] for s in evaluation_sessions}:
        raise ValueError("Reference/evaluation session overlap")
    reference = {group_key(m["context"], m["side"], m["metric"]): m for m in baseline["metrics"]}
    rules = Rules(**baseline["rules"])
    evaluations = []
    for session in evaluation_sessions:
        if session["metadata"]["role"] != "evaluation":
            raise ValueError("Comparison accepts evaluation sessions only")
        comparisons = []
        for metric in session["session_metrics"]:
            ref = reference.get(group_key(session["context"], metric["side"], metric["metric"]))
            reasons = set(metric["reasons"])
            if ref is None:
                reasons.add("incompatible_context" if baseline["metrics"] else "baseline_unavailable")
            elif ref["status"] != "ready":
                reasons.add("insufficient_reference_history")
            difference = percent = standardized = None
            percent_reasons, standardized_reasons = [], []
            if not reasons:
                difference = metric["median"] - ref["median"]
                if ref["median"] == 0:
                    percent_reasons = ["zero_reference"]
                else:
                    percent = 100 * difference / ref["median"]
                if ref["mad"] <= max(rules.mad_abs_tol, rules.mad_rel_tol * abs(ref["median"])):
                    standardized_reasons = ["zero_or_degenerate_mad"]
                else:
                    standardized = 0.67448975 * difference / ref["mad"]
            else:
                percent_reasons = standardized_reasons = sorted(reasons)
            comparisons.append({"side": metric["side"], "metric": metric["metric"], "unit": metric["unit"],
                                "evaluation_median": metric["median"],
                                "valid_event_count": metric["valid_event_count"],
                                "reference_median": ref["median"] if ref else None,
                                "reference_mad": ref["mad"] if ref else None,
                                "signed_difference": difference, "percent_difference": percent,
                                "robust_standardized_difference": standardized,
                                "status": "unavailable" if reasons else (
                                    "partial" if percent_reasons or standardized_reasons else "compared"),
                                "reasons": sorted(reasons),
                                "percent_difference_reasons": percent_reasons,
                                "standardized_difference_reasons": standardized_reasons})
        evaluations.append({**session, "baseline_version": baseline["version"], "comparisons": comparisons})
    return evaluations
