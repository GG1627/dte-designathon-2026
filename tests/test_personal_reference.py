"""Personal-reference architecture and descriptive semantics, not clinical tests."""
import copy
import json
import unittest

from test_baseline_simulation import fixture, find, process
from baseline_experiments import PROFILES, REFERENCE_EXAMPLES, reference_example
from baseline_simulation import (Rules, compare_evaluations, comparison_values,
                                 fit_baseline, generate_reference_history)
from reference_insights import build_insights


class PersonalReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.history = [process(s) for s in generate_reference_history()]
        cls.reference = fit_baseline(cls.history)
        cls.examples = {
            name: compare_evaluations(cls.reference, [process(reference_example(
                fixture(), cls.history, PROFILES[0], name, Rules()))])[0]
            for name in REFERENCE_EXAMPLES}

    def test_insufficient_history_cannot_be_provisional(self):
        baseline = fit_baseline(self.history[:4])
        for metric in baseline['metrics']:
            self.assertEqual(metric['computation_status'], 'unavailable')
            self.assertEqual(metric['reference_status'], 'insufficient_reference')
            self.assertIsNone(metric['median'])
        self.assertFalse(compare_evaluations(baseline, [process(fixture())])[0]['insights'])

    def test_computable_history_is_only_provisional(self):
        for metric in self.reference['metrics']:
            self.assertEqual(metric['computation_status'], 'available')
            self.assertEqual(metric['reference_status'], 'provisional_reference')
            self.assertEqual(metric['eligible_session_count'], 5)
            self.assertEqual(metric['contributing_event_count'], 30)
            self.assertEqual(len(metric['contributing_session_ids']), 5)
        self.assertEqual(self.reference['sufficiency_policy'], 'configurable_software_demonstration_only')

    def test_synthetic_maturity_never_longitudinal_even_when_minimum_changes(self):
        for count in (1, 3, 5):
            fitted = fit_baseline(self.history[:count], Rules(min_reference_sessions=1))
            self.assertTrue(all(m['reference_status'] == 'provisional_reference' for m in fitted['metrics']))
            self.assertNotIn('longitudinal_reference', json.dumps(fitted))

    def test_context_mismatches_and_side_are_unavailable(self):
        evaluation = process(fixture())
        for field in ('participant_id', 'joint', 'activity', 'configuration_id',
                      'configuration_signature', 'processing_version', 'processing_signature'):
            wrong = copy.deepcopy(evaluation)
            wrong['context'][field] = 'different'
            result = compare_evaluations(self.reference, [wrong])[0]
            self.assertTrue(all(c['comparison_availability'] == 'unavailable'
                                and 'incompatible_context' in c['reasons'] for c in result['comparisons']))
            self.assertEqual(result['insights'], [])
        right_only = copy.deepcopy(self.reference)
        right_only['metrics'] = [m for m in right_only['metrics'] if m['side'] == 'right']
        result = compare_evaluations(right_only, [evaluation])[0]
        self.assertTrue(all(c['comparison_availability'] == 'unavailable'
                            for c in result['comparisons'] if c['side'] == 'left'))

    def test_evaluations_and_insights_never_mutate_reference(self):
        before = json.dumps(self.reference, sort_keys=True)
        compare_evaluations(self.reference, [process(fixture('right_load_bias'))])
        for example in self.examples.values():
            build_insights(example['comparisons'])
        self.assertEqual(json.dumps(self.reference, sort_keys=True), before)

    def test_reliability_stays_unestablished_and_null(self):
        for reliability in [self.reference['measurement_reliability'],
                            *[m['measurement_reliability'] for m in self.reference['metrics']]]:
            self.assertFalse(reliability['empirically_established'])
            for field in ('typical_error', 'cv_percent', 'sem', 'mdc', 'source'):
                self.assertIsNone(reliability[field])

    def assert_pattern(self, scenario, pattern, side, metric, percent):
        insight = self.examples[scenario]['insights'][0]
        self.assertEqual(insight['pattern'], pattern)
        self.assertFalse(insight['medical_inference'])
        self.assertEqual(insight['reference_status'], 'provisional_reference')
        self.assertEqual(insight['activity'], 'bilateral_landing')
        evidence = find(insight['evidence'], side, metric)
        self.assertAlmostEqual(evidence['percent_difference'], percent)
        self.assertAlmostEqual(evidence['signed_difference'], evidence['current'] - evidence['reference'])
        self.assertEqual(len(insight['evidence']), 4)

    def test_bilateral_loading_pattern_and_evidence(self):
        self.assert_pattern('reference_bilateral_loading', 'bilateral_loading_increase',
                            'left', 'peak_plantar_normal_force_bw', 10)

    def test_reduced_rom_pattern_and_evidence(self):
        self.assert_pattern('reference_reduced_rom', 'rom_decrease', 'right', 'knee_rom_rad', -20)

    def test_right_loading_pattern_and_evidence(self):
        self.assert_pattern('reference_right_loading', 'right_loading_increase',
                            'right', 'peak_plantar_normal_force_bw', 14)

    def test_insights_ignore_generation_labels_and_ground_truth(self):
        comparisons = copy.deepcopy(self.examples['reference_right_loading']['comparisons'])
        before = copy.deepcopy(comparisons)
        for c in comparisons:
            c.update(scenario='reference_reduced_rom', phase='baseline',
                     ground_truth={'flexion': 'invalid'}, programmed={'force_scale': -999})
        self.assertEqual(build_insights(comparisons), build_insights(before))
        # Exact same available measurements, with different directions, change pattern.
        for c in comparisons:
            if c['metric'] == 'peak_plantar_normal_force_bw' and c['side'] == 'left':
                c.update(**comparison_values(c['reference_median'] * 1.1,
                         {'median': c['reference_median'], 'mad': c['reference_mad']}, set(), Rules()))
                c['evaluation_median'] = c['reference_median'] * 1.1
        self.assertEqual(build_insights(comparisons)[0]['pattern'], 'bilateral_loading_increase')

    def test_invalid_metrics_are_never_insight_evidence(self):
        evaluated = compare_evaluations(self.reference, [process(fixture('sensor_dropout'))])[0]
        for insight in evaluated['insights']:
            self.assertFalse(any(e['side'] == 'left' and e['metric'] != 'knee_rom_rad'
                                 for e in insight['evidence']))
        comparisons = copy.deepcopy(self.examples['reference_right_loading']['comparisons'])
        comparisons[0]['status'] = 'rejected'
        self.assertFalse(any(e['side'] == comparisons[0]['side'] and e['metric'] == comparisons[0]['metric']
                             for i in build_insights(comparisons) for e in i['evidence']))
        for c in comparisons:
            c['comparison_availability'] = 'unavailable'
        self.assertEqual(build_insights(comparisons), [])

    def test_numerical_equivalence_is_not_a_percentage_deadband(self):
        ref = {'median': 1, 'mad': .01}
        self.assertEqual(comparison_values(1 + 1e-13, ref, set(), Rules())['direction'], 'near_reference')
        self.assertEqual(comparison_values(1.0001, ref, set(), Rules())['direction'], 'increased')
        self.assertEqual(comparison_values(.9999, ref, set(), Rules())['direction'], 'decreased')
        self.assertIsNone(comparison_values(None, ref, {'invalid'}, Rules())['direction'])

    def test_within_and_between_session_dispersion_are_distinct(self):
        for metric in self.reference['metrics']:
            self.assertEqual(metric['dispersion_scope'], 'between_session_medians')
            self.assertTrue(all(m['event_mad'] is not None for m in metric['session_summaries']))
        self.assertTrue(all(m['dispersion_scope'] == 'within_session_events'
                            for m in self.history[0]['session_metrics']))


if __name__ == '__main__':
    unittest.main()
