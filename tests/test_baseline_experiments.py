"""Held-out quality challenges and personalized history checks."""
import json
import math
import unittest

from test_baseline_simulation import ROOT, find, process
from baseline_experiments import PROFILES, app_snapshot, build_experiments, challenge_session
from baseline_simulation import generate_reference_history
import generate_mock_data as mock


class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = {name: json.loads((ROOT / 'data/mock' / f'{name}.json').read_text())
                        for name in ('balanced', 'right_load_bias', 'sensor_dropout')}
        cls.experiments, cls.challenges = build_experiments(cls.fixtures)

    def test_quality_is_feature_specific(self):
        expected = {
            'insole_clock_offset': (3, 0, 3), 'placement_error': (0, 3, 3),
            'force_calibration_error': (3, 0, 3), 'boundary_gap': (3, 2, 3),
            'missing_frame': (2, 2, 2), 'noisy_measurements': (3, 3, 3),
            'unflagged_force_drift': (3, 3, 3),
        }
        for stream in self.challenges:
            summary = process(stream)
            metrics = summary['session_metrics']
            counts = tuple(find(metrics, side, metric)['valid_event_count'] for side, metric in (
                ('left', 'knee_rom_rad'), ('left', 'peak_plantar_normal_force_bw'),
                ('right', 'peak_plantar_normal_force_bw')))
            self.assertEqual(counts, expected[stream['scenario']], stream['scenario'])
            self.assertEqual(find(metrics, 'left', 'landing_window_impulse_bw_s')['valid_event_count'], counts[1])

    def test_noise_is_seeded_and_dependent_fields_remain_consistent(self):
        a = challenge_session(self.fixtures['balanced'], 'noisy_measurements', 123)
        self.assertEqual(a, challenge_session(self.fixtures['balanced'], 'noisy_measurements', 123))
        self.assertNotEqual(a, challenge_session(self.fixtures['balanced'], 'noisy_measurements', 124))
        mock.verify_measurements(a)
        sample = a['samples'][117]
        original = self.fixtures['balanced']['samples'][117]
        t, amp, omega = sample['timestamp_s'], math.radians(.2), 2*math.pi*5
        self.assertAlmostEqual(sample['left']['knee']['angular_velocity_rad_s'] -
                               original['left']['knee']['angular_velocity_rad_s'], amp*omega*math.cos(omega*t))

    def test_same_evaluation_has_different_personal_references(self):
        medians, differences = [], []
        for participant in self.experiments['participants']:
            snapshot = participant['snapshots'][1]
            baseline = find(snapshot['baseline']['metrics'], 'right', 'peak_plantar_normal_force_bw')
            evaluation = next(e for e in snapshot['evaluations']
                              if e['metadata']['source_fixture_session_id'] == 'mock_balanced_001')
            comparison = find(evaluation['comparisons'], 'right', 'peak_plantar_normal_force_bw')
            self.assertAlmostEqual(comparison['evaluation_median'], 1.7)
            self.assertEqual(baseline['context']['participant_id'], participant['profile']['id'])
            medians.append(baseline['median'])
            differences.append(comparison['signed_difference'])
        self.assertEqual(len(set(medians)), 3)
        self.assertGreater(differences[0], 0)
        self.assertLess(differences[1], 0)
        self.assertGreater(differences[2], differences[0])

    def test_history_prefixes_and_app_export_match_frozen_results(self):
        exported = app_snapshot(self.experiments)
        for participant, app_participant in zip(self.experiments['participants'], exported['participants']):
            for snapshot, app_result in zip(participant['snapshots'], app_participant['snapshots']):
                count = snapshot['reference_session_count']
                self.assertEqual(app_result['metrics'], snapshot['baseline']['metrics'])
                self.assertTrue(all(m['eligible_session_count'] == count for m in app_result['metrics']))
                self.assertTrue(all(m['status'] == ('insufficient_reference_history' if count == 3 else 'ready')
                                    for m in app_result['metrics']))
                for original, exported_eval in zip(snapshot['evaluations'], app_result['evaluations']):
                    self.assertEqual(original['comparisons'], exported_eval['comparisons'])
                    self.assertNotIn('event_metrics', exported_eval)
        self.assertNotIn('samples', json.dumps(exported))

    def test_history_chronology_and_profile_separation(self):
        ids = set()
        for profile in PROFILES:
            history = generate_reference_history(session_count=20, participant=profile)
            self.assertLess(history[-1]['baseline_demo']['recorded_at'], '2026-10-03')
            self.assertEqual(history[:5], generate_reference_history(participant=profile))
            for session in history:
                self.assertNotIn(session['session_id'], ids)
                ids.add(session['session_id'])


if __name__ == '__main__':
    unittest.main()
