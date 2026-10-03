"""Focused software checks; not sensor accuracy or medical validation."""
import copy
import hashlib
import json
import math
import sys
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import generate_mock_data as mock
from analyze_knee_kinematics import summarize_knee
from baseline_simulation import (
    CONTEXT_FIELDS, METRICS, Rules, compare_evaluations, evaluation_fixture,
    extract_session, fit_baseline, generate_reference_history, summarize_session,
)
from run_baseline_demo import run_demo


def fixture(name="balanced", index=6):
    return evaluation_fixture(json.loads((ROOT / "data/mock" / f"{name}.json").read_text()), index)


def process(data, rules=Rules()):
    return summarize_session(extract_session(data, rules), rules)


def find(results, side, metric, event_id=None):
    return next(result for result in results if result["side"] == side and result["metric"] == metric
                and (event_id is None or result["event_id"] == event_id))


@contextmanager
def temporary_output():
    # Normal mkdir avoids restrictive Windows ACLs imposed by tempfile's 0o700.
    root = (ROOT / "data/baseline_demo").resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f".test-{uuid.uuid4().hex}"
    if not path.resolve().is_relative_to(root):
        raise ValueError("Test output must stay within the dedicated output directory")
    path.mkdir()
    try:
        yield path
    finally:
        for item in path.iterdir():
            item.unlink()
        path.rmdir()


class BaselineSimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.history = generate_reference_history()
        cls.reference_metrics = [process(data) for data in cls.history]
        cls.baseline = fit_baseline(cls.reference_metrics)
        cls.balanced = process(fixture())

    def toy_summary(self, session_id, value, count=3, role="reference"):
        """Controlled extracted metrics to isolate the two-level statistics."""
        extracted = copy.deepcopy(self.balanced)
        extracted["session_id"] = session_id
        extracted["metadata"]["role"] = role
        templates = extracted["event_metrics"][:6]
        extracted["event_metrics"] = [
            {**event, "event_id": f"toy_{index}", "value": value}
            for index in range(count) for event in templates]
        return summarize_session(extracted)

    def test_known_fixture_metrics_and_analysis_convention(self):
        for side, amplitude in (("left", 38), ("right", 36)):
            events = self.balanced["event_metrics"]
            expected_rom = math.radians(amplitude) * (1 - math.exp(-0.5 * (0.35 / 0.18) ** 2))
            self.assertAlmostEqual(find(events, side, "knee_rom_rad")["value"], expected_rom, places=12)
            self.assertAlmostEqual(find(events, side, "peak_plantar_normal_force_bw")["value"], 1.7, places=12)
            self.assertAlmostEqual(find(events, side, "landing_window_impulse_bw_s")["value"], 0.51, places=12)
            data = fixture()
            window = [s for s in data["samples"] if 1 <= s["timestamp_s"] <= 1.6]
            self.assertEqual(len(window), 61)
            self.assertAlmostEqual(math.radians(summarize_knee(window, side)["rom_deg"]), expected_rom, places=12)

    def test_existing_generator_regressions_and_direct_ten_percent_bias(self):
        biased = process(fixture("right_load_bias"))
        for name in ("balanced", "right_load_bias", "sensor_dropout"):
            mock.verify(fixture(name))
        for metric in list(METRICS)[1:]:
            for event_id in ("landing_1", "landing_2", "landing_3"):
                a = find(self.balanced["event_metrics"], "right", metric, event_id)["value"]
                b = find(biased["event_metrics"], "right", metric, event_id)["value"]
                self.assertAlmostEqual(b / a, 1.1, places=12)
                self.assertAlmostEqual(100 * (b - a) / a, 10, places=12)
                self.assertEqual(find(biased["event_metrics"], "left", metric, event_id)["value"],
                                 find(self.balanced["event_metrics"], "left", metric, event_id)["value"])

    def test_repeatable_generation_and_reference_variation(self):
        self.assertEqual(self.history, generate_reference_history())
        self.assertNotEqual(self.history, generate_reference_history(123))
        self.assertEqual(len(self.history), 5)
        for data in self.history:
            self.assertEqual(len(data["annotations"]), 6)
            self.assertEqual(data["baseline_demo"]["role"], "reference")
            self.assertEqual(len(data["samples"]), 1200)
        for baseline in self.baseline["metrics"]:
            self.assertEqual(baseline["status"], "ready")
            self.assertEqual(baseline["eligible_session_count"], 5)
            self.assertEqual(baseline["contributing_event_count"], 30)
            self.assertGreater(baseline["mad"], 1e-6)
            values = [e["value"] for e in self.reference_metrics[0]["event_metrics"]
                      if e["side"] == baseline["side"] and e["metric"] == baseline["metric"]]
            self.assertGreater(max(values) - min(values), 1e-6)

    def test_generation_bounds_derivatives_and_spatial_consistency(self):
        for data in self.history:
            mock.verify_measurements(data)
            for event in data["baseline_demo"]["waveforms"]:
                self.assertGreaterEqual(round(event["end_s"] - event["start_s"], 2), 0.55)
                self.assertLessEqual(round(event["end_s"] - event["start_s"], 2), 0.65)
                for side in ("left", "right"):
                    self.assertGreaterEqual(event["force_scale"][side], 0.965 * 0.975)
                    self.assertLessEqual(event["force_scale"][side], 1.035 * 1.025)
            landings = data["baseline_demo"]["waveforms"]
            t, step = 1.19, 1e-5
            for side in ("left", "right"):
                before, current, after = [mock.knee(tt, side, landings) for tt in (t-step, t, t+step)]
                velocity = (after["flexion_rad"] - before["flexion_rad"]) / (2 * step)
                acceleration = (after["flexion_rad"] - 2*current["flexion_rad"] + before["flexion_rad"]) / step**2
                self.assertAlmostEqual(velocity, current["angular_velocity_rad_s"], places=6)
                self.assertAlmostEqual(acceleration, current["angular_acceleration_rad_s2"], places=4)
                foot = data["samples"][130][side]["insole"]
                cells = data["insole_geometry"][side]
                regional_force = sum(p*c["area_m2"] for p,c in zip(foot["cell_pressures_pa"],cells)
                                     if c["region"] == "medial")
                self.assertAlmostEqual(regional_force / foot["plantar_normal_force_n"], foot["medial_fraction"])

    def test_equal_session_weight_despite_unequal_event_counts(self):
        summaries = [self.toy_summary(f"ref_{index}", value, 30 if index == 4 else 3)
                     for index, value in enumerate((1, 2, 3, 4, 100))]
        fitted = fit_baseline(summaries)
        metric = fitted["metrics"][0]
        self.assertEqual(metric["median"], 3)
        self.assertEqual(metric["mad"], 1)
        self.assertEqual(metric["contributing_event_count"], 42)
        self.assertEqual(median([1]*3 + [2]*3 + [3]*3 + [4]*3 + [100]*30), 100)

    def test_separation_duplicates_roles_and_frozen_baseline(self):
        before = copy.deepcopy(self.baseline)
        compare_evaluations(self.baseline, [self.balanced])
        self.assertEqual(before, self.baseline)
        overlapping = copy.deepcopy(self.balanced)
        overlapping["session_id"] = self.baseline["reference_session_ids"][0]
        with self.assertRaisesRegex(ValueError, "overlap"):
            compare_evaluations(self.baseline, [overlapping])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            fit_baseline([self.reference_metrics[0]] * 2)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            compare_evaluations(self.baseline, [self.balanced] * 2)
        with self.assertRaisesRegex(ValueError, "reference sessions only"):
            fit_baseline([self.balanced])
        wrong_role = copy.deepcopy(self.reference_metrics[0])
        wrong_role["session_id"] = "not_in_fitted_history"
        with self.assertRaisesRegex(ValueError, "evaluation sessions only"):
            compare_evaluations(self.baseline, [wrong_role])

    def test_dropout_is_feature_specific_and_preserves_valid_events(self):
        dropout = process(fixture("sensor_dropout"))
        evaluated = compare_evaluations(self.baseline, [dropout])[0]
        knee = find(evaluated["comparisons"], "left", "knee_rom_rad")
        self.assertEqual(knee["status"], "compared")
        self.assertEqual(knee["valid_event_count"], 3)
        for metric in list(METRICS)[1:]:
            events = dropout["event_metrics"]
            self.assertEqual(find(events, "left", metric, "landing_1")["status"], "accepted")
            self.assertEqual(find(events, "left", metric, "landing_3")["status"], "accepted")
            bad = find(events, "left", metric, "landing_2")
            self.assertIsNone(bad["value"])
            self.assertIn("sensor_dropout", bad["reasons"])
            comparison = find(evaluated["comparisons"], "left", metric)
            self.assertEqual(comparison["valid_event_count"], 2)
            self.assertIsNone(comparison["evaluation_median"])
            self.assertIsNone(comparison["signed_difference"])
            self.assertIn("insufficient_valid_events", comparison["reasons"])
            self.assertEqual(find(evaluated["comparisons"], "right", metric)["status"], "compared")

    def test_invalid_or_null_knee_leaves_force_available(self):
        for change in ("quality", "null"):
            data = fixture()
            if change == "quality":
                data["samples"][130]["left"]["knee"]["quality"] = {"valid": False, "reasons": ["bad_alignment"]}
            else:
                data["samples"][130]["left"]["knee"]["flexion_rad"] = None
            events = extract_session(data)["event_metrics"]
            self.assertEqual(find(events, "left", "knee_rom_rad")["status"], "rejected")
            self.assertEqual(find(events, "left", "peak_plantar_normal_force_bw")["status"], "accepted")
            self.assertEqual(find(events, "right", "knee_rom_rad")["status"], "accepted")

    def test_pressure_mismatch_missing_cells_and_force_quality(self):
        for change in ("mismatch", "null", "partial", "quality"):
            data = fixture()
            foot = data["samples"][130]["left"]["insole"]
            if change == "mismatch":
                foot["cell_pressures_pa"][0] += 1
            elif change == "null":
                foot["cell_pressures_pa"][0] = None
            elif change == "partial":
                foot["cell_pressures_pa"].pop()
            else:
                foot["quality"] = {"valid": False, "reasons": ["bad_calibration"]}
            events = extract_session(data)["event_metrics"]
            self.assertEqual(find(events, "left", "knee_rom_rad")["status"], "accepted")
            for metric in list(METRICS)[1:]:
                self.assertEqual(find(events, "left", metric)["status"], "rejected")
            if change == "mismatch":
                self.assertIn("inconsistent_pressure_force", find(events, "left", list(METRICS)[1])["reasons"])

    def test_unavailable_cop_is_not_a_force_failure(self):
        data = fixture()
        for sample in data["samples"]:
            for side in ("left", "right"):
                foot = sample[side]["insole"]
                foot["cop_m"] = foot["medial_fraction"] = foot["lateral_fraction"] = None
        self.assertTrue(all(e["status"] == "accepted" for e in extract_session(data)["event_metrics"]))

    def test_missing_frame_endpoint_order_and_sequence(self):
        for change, reason in (("gap", "sample_discontinuity"), ("endpoint", "incomplete_window_boundaries"),
                               ("order", "non_monotonic_timestamps"), ("sequence", "sequence_discontinuity")):
            data = fixture()
            if change == "gap":
                del data["samples"][130]
            elif change == "endpoint":
                del data["samples"][100]
            elif change == "order":
                data["samples"][131]["timestamp_s"] = data["samples"][130]["timestamp_s"]
            else:
                data["samples"][130]["sequence"] += 5
            for event in extract_session(data)["event_metrics"][:6]:
                self.assertEqual(event["status"], "rejected")
                self.assertIn(reason, event["reasons"])

    def test_actual_timestamps_drive_trapezoidal_integral(self):
        data = fixture()
        data["samples"][112]["timestamp_s"] += 0.0005
        rules = Rules(timestamp_abs_tol_s=0.001)  # Explicitly allow this test's timing jitter.
        events = extract_session(data, rules)["event_metrics"]
        result = find(events, "left", "landing_window_impulse_bw_s")
        ss = [s for s in data["samples"] if 1 <= s["timestamp_s"] <= 1.6]
        expected = sum((b["timestamp_s"]-a["timestamp_s"])
                       *(a["left"]["insole"]["plantar_normal_force_n"]+b["left"]["insole"]["plantar_normal_force_n"])/2
                       for a,b in zip(ss,ss[1:])) / (75*9.80665)
        self.assertEqual(result["status"], "accepted")
        self.assertAlmostEqual(result["value"], expected, places=14)
        self.assertNotAlmostEqual(result["value"], 0.51, places=8)

    def test_zero_mad_zero_reference_and_degenerate_mad(self):
        for values, zero_reference in (([0]*5, True), ([2]*5, False),
                                       ([1+i*1e-14 for i in range(5)], False)):
            baseline = fit_baseline([self.toy_summary(f"r{i}", v) for i,v in enumerate(values)])
            result = compare_evaluations(baseline, [self.toy_summary("eval", 3, role="evaluation")])[0]
            for comparison in result["comparisons"]:
                self.assertIsNotNone(comparison["signed_difference"])
                self.assertIsNone(comparison["robust_standardized_difference"])
                self.assertIn("zero_or_degenerate_mad", comparison["standardized_difference_reasons"])
                if zero_reference:
                    self.assertIsNone(comparison["percent_difference"])
                    self.assertIn("zero_reference", comparison["percent_difference_reasons"])
                else:
                    self.assertIsNotNone(comparison["percent_difference"])

    def test_insufficient_history_and_reference_event_counts(self):
        unavailable = compare_evaluations(fit_baseline([]), [self.balanced])[0]["comparisons"]
        self.assertTrue(all("baseline_unavailable" in c["reasons"] for c in unavailable))
        for references in (self.reference_metrics[:4],
                           [self.toy_summary(f"r{i}", i, count=2) for i in range(5)]):
            baseline = fit_baseline(references)
            self.assertTrue(all(m["status"] == "insufficient_reference_history" for m in baseline["metrics"]))
            result = compare_evaluations(baseline, [self.balanced])[0]
            self.assertTrue(all("insufficient_reference_history" in c["reasons"] for c in result["comparisons"]))
            self.assertTrue(all(c["signed_difference"] is None for c in result["comparisons"]))
        configured = Rules(min_reference_sessions=4)
        self.assertTrue(all(m["status"] == "ready" for m in fit_baseline(self.reference_metrics[:4], configured)["metrics"]))

    def test_incompatible_grouping_contexts(self):
        for field in CONTEXT_FIELDS:
            with self.subTest(field=field):
                evaluation = copy.deepcopy(self.balanced)
                evaluation["context"][field] = "incompatible"
                results = compare_evaluations(self.baseline, [evaluation])[0]["comparisons"]
                self.assertTrue(all("incompatible_context" in c["reasons"] for c in results))
                self.assertTrue(all(c["signed_difference"] is None for c in results))
        data = fixture()
        data["insole_geometry"]["left"][0]["x_m"] += 0.01
        evaluation = process(data)
        self.assertNotEqual(evaluation["context"]["configuration_signature"], self.balanced["context"]["configuration_signature"])
        self.assertTrue(all("incompatible_context" in c["reasons"] for c in
                            compare_evaluations(self.baseline, [evaluation])[0]["comparisons"]))

    def test_configurable_event_minimum(self):
        rules = Rules(min_valid_events=4)
        baseline = fit_baseline([process(data, rules) for data in self.history], rules)
        self.assertTrue(all(m["status"] == "ready" for m in baseline["metrics"]))
        comparisons = compare_evaluations(baseline, [process(fixture(), rules)])[0]["comparisons"]
        self.assertTrue(all("insufficient_valid_events" in c["reasons"] for c in comparisons))
        self.assertTrue(all(c["evaluation_median"] is None for c in comparisons))

    def test_repeated_run_outputs_and_fixture_bytes(self):
        paths = list((ROOT / "data/mock").glob("*.json"))
        before = {p.name: p.read_bytes() for p in paths}
        with temporary_output() as directory:
            output = Path(directory)
            sentinel = output / "unrelated.json"
            sentinel.write_text("do not change")
            run_demo(output)
            hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob("*.json")}
            run_demo(output)
            self.assertEqual(hashes, {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob("*.json")})
            self.assertEqual(sentinel.read_text(), "do not change")
            self.assertEqual(len(json.loads((output / "manifest.json").read_text())["generated_files"]), 9)
        self.assertEqual(before, {p.name: p.read_bytes() for p in paths})


if __name__ == "__main__":
    unittest.main()
