"""Engineering checks for a frozen synthetic reference, not athlete validation."""
import copy
import json
import unittest

from test_baseline_simulation import find
from baseline_simulation import (Rules, compare_controlled_observations, context,
                                 evaluation_fixture, extract_session, fit_controlled_reference)
from generate_raw_sensor_fixture import generate_training_fixture
from process_sensor_session import process_session


class ControlledReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = evaluation_fixture(process_session(generate_training_fixture()), 1)
        cls.extracted = extract_session(cls.data)
        cls.ids = [f'landing_{i}' for i in range(1, 6)]

    def test_five_reference_trials_and_fifteen_observations_recover_changes(self):
        ref = fit_controlled_reference(self.extracted, self.ids)
        before = json.dumps(ref, sort_keys=True)
        results = compare_controlled_observations(ref, self.extracted)
        self.assertEqual(ref['reference_status'], 'controlled_test_reference')
        self.assertEqual(ref['session_count'], 1)
        self.assertEqual(len(results), 15 * 6)
        self.assertEqual({e['event_id'] for e in results}, {f'landing_{i}' for i in range(6, 21)})
        force = 'peak_plantar_normal_force_bw'
        for number in range(6, 11):
            for side in ('left', 'right'):
                self.assertAlmostEqual(find(results, side, force, f'landing_{number}')['percent_difference'],
                                       2 * (number - 5))
        self.assertAlmostEqual(find(results, 'right', force, 'landing_20')['percent_difference'], 14)
        self.assertAlmostEqual(find(results, 'left', force, 'landing_20')['percent_difference'], 0)
        self.assertLess(find(results, 'right', 'knee_rom_rad', 'landing_15')['percent_difference'], -19)
        changed = copy.deepcopy(self.extracted)
        for event in changed['event_metrics']:
            if event['event_id'] not in self.ids:
                event['value'] *= 2
        compare_controlled_observations(ref, changed)
        self.assertEqual(json.dumps(ref, sort_keys=True), before)
        for key in ('typical_error', 'cv_percent', 'sem', 'mdc', 'source'):
            self.assertIsNone(ref['measurement_error'][key])
        self.assertFalse(ref['measurement_error']['clinical_meaning_established'])

    def test_zero_variability_and_rejected_trials_remain_unavailable(self):
        ref = fit_controlled_reference(self.extracted, self.ids)
        results = compare_controlled_observations(ref, self.extracted)
        force = find(results, 'right', 'peak_plantar_normal_force_bw', 'landing_20')
        self.assertIsNone(force['robust_standardized_difference'])
        self.assertEqual(force['standardized_difference_reasons'], ['zero_or_degenerate_mad'])
        faulty = copy.deepcopy(self.extracted)
        for event in faulty['event_metrics']:
            if event['side'] == 'right' and event['metric'] == 'knee_rom_rad':
                event.update(value=None, status='rejected', reasons=['invalid_knee_sample'])
        ref = fit_controlled_reference(faulty, self.ids)
        knee = find(ref['metrics'], 'right', 'knee_rom_rad')
        self.assertEqual(knee['status'], 'insufficient_reference')
        self.assertIsNone(knee['median'])
        self.assertIsNone(knee['mad'])
        self.assertEqual(knee['valid_event_count'], 0)
        result = find(compare_controlled_observations(ref, faulty), 'right', 'knee_rom_rad', 'landing_6')
        self.assertIsNone(result['signed_difference'])
        self.assertIn('invalid_knee_sample', result['reasons'])

    def test_like_for_like_context_and_side(self):
        ref = fit_controlled_reference(self.extracted, self.ids)
        for field in ('participant_id', 'joint', 'activity', 'configuration_signature', 'processing_signature'):
            changed = copy.deepcopy(self.extracted)
            changed['context'][field] = 'different'
            results = compare_controlled_observations(ref, changed)
            self.assertTrue(all(e['status'] == 'unavailable' and 'incompatible_context' in e['reasons']
                                for e in results))
        right_only = copy.deepcopy(ref)
        right_only['metrics'] = [m for m in ref['metrics'] if m['side'] == 'right']
        left = find(compare_controlled_observations(right_only, self.extracted),
                    'left', 'knee_rom_rad', 'landing_6')
        self.assertIn('incompatible_context', left['reasons'])
        changed_data = copy.deepcopy(self.data)
        changed_data['baseline_demo']['acquisition_context'] = {'surface': 'different'}
        self.assertNotEqual(context(changed_data, Rules())['configuration_signature'],
                            self.extracted['context']['configuration_signature'])

    def test_reference_ids_and_rules_are_explicit(self):
        for ids in ([], ['unknown'], ['landing_1', 'landing_1']):
            with self.assertRaises(ValueError):
                fit_controlled_reference(self.extracted, ids)
        with self.assertRaises(ValueError):
            fit_controlled_reference(self.extracted, self.ids, Rules(min_valid_events=4))


if __name__ == '__main__':
    unittest.main()
