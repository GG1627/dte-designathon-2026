"""Cross-pipeline regression checks for the ideal synthetic IMU bridge."""
import copy
import json
import math
import unittest

from test_baseline_simulation import ROOT, fixture, process, temporary_output
from analyze_session import analyze_session
from baseline_simulation import compare_evaluations, extract_session, fit_baseline, generate_reference_history
from generate_raw_sensor_fixture import generate_fixture, to_raw_session
from process_sensor_session import process_session
from run_baseline_demo import run_demo
from test_madgwick_knee import check_edge_cases


class SensorIntegrationTests(unittest.TestCase):
    def test_committed_processed_fixture_is_consumable_but_not_mixed_with_ideal_history(self):
        processed = json.loads((ROOT / 'data/processed/mock_balanced_processed.json').read_text())
        from baseline_simulation import evaluation_fixture
        result = process(evaluation_fixture(processed, 21))
        self.assertTrue(all(m['status'] == 'accepted' for m in result['event_metrics']))
        ideal = fit_baseline([process(s) for s in generate_reference_history()])
        comparisons = compare_evaluations(ideal, [result])[0]['comparisons']
        self.assertTrue(all('incompatible_context' in m['reasons'] for m in comparisons))

    def test_raw_roundtrip_preserves_context_and_avoids_ground_truth_leakage(self):
        source = generate_reference_history(session_count=1)[0]
        original = copy.deepcopy(source)
        raw = to_raw_session(source)
        self.assertEqual(source, original)
        output = process_session(raw)
        self.assertEqual(output['baseline_demo'], source['baseline_demo'])
        self.assertEqual(len(output['samples']), 1200)
        for frame in raw['samples']:
            frame.pop('ground_truth')
        self.assertEqual(process_session(raw), output)
        self.assertTrue(all('ground_truth' not in frame for frame in output['samples']))
        self.assertTrue(all(a[side]['insole'] == b[side]['insole']
                            for a,b in zip(source['samples'], output['samples']) for side in ('left','right')))

    def test_processor_rejects_imu_quality_offsets_and_frame_gaps(self):
        for fault in ('quality', 'timestamp', 'gap', 'boolean'):
            raw = generate_fixture()
            packet = raw['samples'][100]['left']['imu']['shank']
            if fault == 'quality':
                packet['quality'] = {'valid': False, 'reasons': ['sensor_dropout']}
            elif fault == 'timestamp':
                packet['timestamp_s'] = 1.03
            elif fault == 'boolean':
                packet['gyro_rad_s']['y'] = True
            else:
                del raw['samples'][100]
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                process_session(raw)
        check_edge_cases()

    def test_analyzer_and_extractor_agree_on_shared_metrics_and_faults(self):
        for name in ('balanced', 'right_load_bias', 'sensor_dropout'):
            data = fixture(name)
            analysis = analyze_session(data)
            extracted = extract_session(data)
            for result in extracted['event_metrics']:
                side = next(e for e in analysis['events'] if e['event_id'] == result['event_id'])[result['side']]
                metric = result['metric']
                value = (math.radians(side['kinematics']['rom_deg'])
                         if metric == 'knee_rom_rad' and side['kinematics']['rom_deg'] is not None
                         else side['loading']['peak_force_bw'] if metric == 'peak_plantar_normal_force_bw'
                         else side['loading']['impulse_n_s'] / (75 * 9.80665)
                         if metric == 'landing_window_impulse_bw_s' and side['loading']['impulse_n_s'] is not None
                         else None)
                if result['value'] is None:
                    self.assertIsNone(value)
                else:
                    self.assertAlmostEqual(value, result['value'])
        for fault in ('boundary', 'sequence', 'pressure', 'negative', 'clock'):
            data = fixture()
            if fault == 'boundary':
                del data['samples'][100]
            elif fault == 'sequence':
                data['samples'][120]['sequence'] += 7
            elif fault == 'pressure':
                data['samples'][120]['left']['insole']['plantar_normal_force_n'] *= 2
            elif fault == 'negative':
                data['samples'][120]['left']['insole']['plantar_normal_force_n'] = -1
            else:
                data['samples'][120]['left']['insole']['timestamp_s'] = 1.23
            event = analyze_session(data)['events'][0]
            self.assertIsNone(event['left']['loading']['peak_force_bw'], fault)
            self.assertIsNone(event['left']['loading']['impulse_n_s'], fault)
            if fault in ('boundary', 'sequence'):
                self.assertIsNone(event['left']['kinematics']['rom_deg'])
            else:
                self.assertIsNotNone(event['left']['kinematics']['rom_deg'])

    def test_signed_asymmetry_retains_direction_and_legacy_magnitude(self):
        data = fixture('right_load_bias')
        event = analyze_session(data)['events'][0]['bilateral']
        signed = event['signed_asymmetry_percent']['peak_force_asymmetry_percent']
        self.assertAlmostEqual(signed, 100 * .17 / 1.785)
        self.assertAlmostEqual(event['loading']['peak_force_asymmetry_percent'], abs(signed))
        for sample in data['samples']:
            sample['left'], sample['right'] = sample['right'], sample['left']
        data['insole_geometry']['left'], data['insole_geometry']['right'] = (
            data['insole_geometry']['right'], data['insole_geometry']['left'])
        reversed_event = analyze_session(data)['events'][0]['bilateral']
        self.assertAlmostEqual(reversed_event['signed_asymmetry_percent']['peak_force_asymmetry_percent'], -signed)

    def test_sensor_baseline_demo_and_feature_specific_dropout(self):
        paths = [ROOT / 'data/mock' / f'{name}.json' for name in ('balanced','right_load_bias','sensor_dropout')]
        originals = [path.read_bytes() for path in paths]
        with temporary_output() as output:
            baseline, evaluations = run_demo(output=output, sensor_pipeline=True)
            self.assertTrue(all(m['status'] == 'ready' for m in baseline['metrics']))
            dropout = evaluations[2]['comparisons']
            self.assertTrue(all(m['signed_difference'] is not None for m in dropout if m['metric'] == 'knee_rom_rad'))
            self.assertTrue(all(m['valid_event_count'] == 2 and 'insufficient_valid_events' in m['reasons']
                                for m in dropout if m['side'] == 'left' and m['metric'] != 'knee_rom_rad'))
            for metric in ('peak_plantar_normal_force_bw', 'landing_window_impulse_bw_s'):
                values = [next(m['evaluation_median'] for m in e['comparisons']
                               if m['side'] == 'right' and m['metric'] == metric) for e in evaluations[:2]]
                self.assertAlmostEqual(values[1] / values[0], 1.1)
        self.assertEqual(originals, [path.read_bytes() for path in paths])


if __name__ == '__main__':
    unittest.main()
