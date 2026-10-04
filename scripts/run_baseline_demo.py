"""Run the complete standard-library personal-baseline demonstration."""
import argparse
import hashlib
import json
from pathlib import Path

from baseline_simulation import (
    Rules, compare_evaluations, evaluation_fixture, extract_session,
    fit_baseline, generate_reference_history, summarize_session,
)
from baseline_experiments import app_snapshot, build_experiments

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "baseline_demo"
FIXTURES = ("balanced", "right_load_bias", "sensor_dropout")


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_demo(output=OUTPUT, seed=20261003, rules=Rules(), include_experiments=False,
             app_output=None, sensor_pipeline=False):
    """Replace named generated outputs only; app export is explicitly selected by CLI."""
    if sensor_pipeline and output == OUTPUT:
        output = OUTPUT / "sensor_pipeline"
    fixture_paths = [ROOT / "data" / "mock" / f"{name}.json" for name in FIXTURES]
    original_hashes = {path.name: file_hash(path) for path in fixture_paths}
    references = generate_reference_history(seed)
    evaluation_inputs = [evaluation_fixture(json.loads(path.read_text(encoding="utf-8")), index + 6)
                         for index, path in enumerate(fixture_paths)]
    if sensor_pipeline:
        if include_experiments or app_output is not None:
            raise ValueError("Sensor round-trip uses separate outputs, without the ideal-angle app export")
        from generate_raw_sensor_fixture import to_raw_session
        from process_sensor_session import process_session
        references = [process_session(to_raw_session(s)) for s in references]
        evaluation_inputs = [process_session(to_raw_session(s)) for s in evaluation_inputs]
    reference_metrics = [summarize_session(extract_session(s, rules), rules) for s in references]
    baseline = fit_baseline(reference_metrics, rules)
    evaluations = [summarize_session(extract_session(s, rules), rules) for s in evaluation_inputs]
    baseline_before = json.dumps(baseline, sort_keys=True, allow_nan=False)
    evaluated = compare_evaluations(baseline, evaluations)
    if baseline_before != json.dumps(baseline, sort_keys=True, allow_nan=False):
        raise RuntimeError("Evaluation mutated the frozen reference")
    if original_hashes != {path.name: file_hash(path) for path in fixture_paths}:
        raise RuntimeError("Original fixtures changed")
    outputs = {f"reference_{index:03d}.json": session
               for index, session in enumerate(references, 1)}
    outputs.update({"reference_metrics.json": reference_metrics, "baseline.json": baseline,
                    "evaluations.json": evaluated,
                    "manifest.json": {"synthetic": True, "seed": seed, "rules": baseline["rules"],
                                      "sensor_pipeline": sensor_pipeline,
                                      "reference_session_ids": baseline["reference_session_ids"],
                                      "evaluation_session_ids": [s["session_id"] for s in evaluated],
                                      "original_fixture_sha256": original_hashes,
                                      "generated_files": sorted([*outputs, "reference_metrics.json",
                                                                 "baseline.json", "evaluations.json", "manifest.json"]),
                                      "interpretation": "Descriptive synthetic differences; no medical validation"}})
    if include_experiments:
        fixtures = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in fixture_paths}
        experiments, challenges = build_experiments(fixtures, seed, rules)
        outputs.update({"experiments.json": experiments, "challenge_sessions.json": challenges,
                        "app_snapshot.json": app_snapshot(experiments)})
        outputs["manifest.json"]["generated_files"] = sorted(outputs)
    if app_output is not None:
        if not include_experiments:
            raise ValueError("App export requires experiment results")
        app_output.parent.mkdir(parents=True, exist_ok=True)
        app_output.write_bytes((json.dumps(outputs["app_snapshot.json"], separators=(",", ":"),
                                          sort_keys=True, allow_nan=False) + "\n").encode("utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    for name, data in outputs.items():
        # Reference streams use the existing compact fixture convention; results are indented.
        payload = json.dumps(data, allow_nan=False, sort_keys=True,
                             indent=None if name.startswith("reference_0") else 2,
                             separators=(",", ":") if name.startswith("reference_0") else None)
        (output / name).write_bytes((payload + "\n").encode("utf-8"))
    return baseline, evaluated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20261003)
    parser.add_argument("--min-valid-events", type=int, default=3)
    parser.add_argument("--min-reference-sessions", type=int, default=5)
    parser.add_argument("--sensor-pipeline", action="store_true",
                        help="Round-trip references and evaluations through ideal raw IMUs and Madgwick; separate outputs")
    args = parser.parse_args()
    rules = Rules(min_valid_events=args.min_valid_events,
                  min_reference_sessions=args.min_reference_sessions)
    output = OUTPUT / "sensor_pipeline" if args.sensor_pipeline else OUTPUT
    baseline, evaluations = run_demo(output=output, seed=args.seed, rules=rules,
                                    include_experiments=not args.sensor_pipeline,
                                    app_output=None if args.sensor_pipeline else ROOT / "rn-app/src/data/baseline-results.json",
                                    sensor_pipeline=args.sensor_pipeline)
    ready = sum(m["status"] == "ready" for m in baseline["metrics"])
    print(f"Synthetic history: 5 reference sessions x 6 bilateral landings; {ready}/6 baseline metrics ready.")
    for session in evaluations:
        peak = next(m for m in session["comparisons"]
                    if m["side"] == "right" and m["metric"] == "peak_plantar_normal_force_bw")
        change = peak["percent_difference"]
        label = f"{change:+.2f}%" if change is not None else ", ".join(peak["reasons"])
        value = f"{peak['evaluation_median']:.4f} BW" if peak["evaluation_median"] is not None else "unavailable"
        unavailable = sum(m["status"] == "unavailable" for m in session["comparisons"])
        print(f"{session['session_id']}: right peak {value}, "
              f"personal reference difference {label}; {unavailable} unavailable comparisons.")
        for insight in session["insights"]:
            print(f"  Provisional reference insight: {insight['summary']}")
    dropout = evaluations[-1]
    left_force = next(m for m in dropout["comparisons"]
                      if m["side"] == "left" and m["metric"] == "peak_plantar_normal_force_bw")
    print(f"Dropout: {left_force['valid_event_count']} valid left-insole events; "
          f"left force comparison {left_force['status']} (minimum {rules.min_valid_events}). "
          "Knee events remain valid.")
    print(f"JSON results: {output.relative_to(ROOT).as_posix()}/")
    if args.sensor_pipeline:
        print("References and evaluations both use ideal IMU emulation and Madgwick. App snapshot unchanged.")
    else:
        print("Experiments: 3 participant patterns, 13 evaluation scenarios, history sizes 3/5/10/20.")
        print("App snapshot refreshed: rn-app/src/data/baseline-results.json")
    print("Software demonstration only; no real-sensor or medical validation.")


if __name__ == "__main__":
    main()
