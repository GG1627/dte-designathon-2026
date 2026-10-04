"""Protect Antonio's corrected ideal sagittal kinematics during baseline integration."""
import copy
import math
import unittest

from test_baseline_simulation import fixture
from analyze_session import analyze_session
from generate_raw_sensor_fixture import generate_fixture, generate_training_fixture, to_raw_session
from process_sensor_session import process_session


class KinematicRegressionTests(unittest.TestCase):
    def test_balanced_gyro_peaks_repeat_without_angle_differentiation(self):
        raw = generate_fixture()
        processed = process_session(raw)
        events = analyze_session(processed)['events']
        for side, speed, acceleration in (('left', 128.0453614948893, 1171.0309645019179),
                                          ('right', 121.30613194252668, 1109.3977558439221)):
            for key, expected in (('peak_abs_velocity_deg_s', speed),
                                  ('peak_abs_acceleration_deg_s2', acceleration)):
                peaks = [event[side]['kinematics'][key] for event in events]
                self.assertLess(max(peaks) - min(peaks), 1e-9)
                for peak in peaks:
                    self.assertAlmostEqual(peak, expected, places=8)
            for source, result in zip(raw['samples'], processed['samples']):
                self.assertEqual(result[side]['knee']['angular_velocity_rad_s'],
                                 source[side]['imu']['shank']['gyro_rad_s']['y']
                                 - source[side]['imu']['thigh']['gyro_rad_s']['y'])

    def test_ground_truth_does_not_control_processing(self):
        raw = generate_fixture()
        expected = process_session(raw)
        for row in raw['samples']:
            row.pop('ground_truth')
        self.assertEqual(process_session(raw), expected)
        # Nonzero parent gyro must also participate in relative velocity.
        for row in raw['samples']:
            row['left']['imu']['thigh']['gyro_rad_s']['y'] = 0.1
        result = process_session(raw)
        for source, row in zip(raw['samples'], result['samples']):
            self.assertEqual(row['left']['knee']['angular_velocity_rad_s'],
                             source['left']['imu']['shank']['gyro_rad_s']['y'] - 0.1)

    def test_training_phases_survive_processing(self):
        raw = generate_training_fixture()
        self.assertEqual(len(raw['samples']), 4100)
        self.assertEqual(len(raw['annotations']), 20)
        result = process_session(raw)
        self.assertEqual(result['phases'], raw['phases'])
        for row in result['samples']:
            self.assertTrue(all(math.isfinite(value) for side in ('left', 'right')
                                for key, value in row[side]['knee'].items() if key != 'quality'))
        no_truth = copy.deepcopy(raw)
        no_truth.pop('ground_truth')
        for row in no_truth['samples']:
            row.pop('ground_truth')
        self.assertEqual(process_session(no_truth), result)
        events = analyze_session(result)['events']
        self.assertEqual(len(events), 20)
        for side in ('left', 'right'):
            baseline = [e[side]['kinematics']['maximum_deg'] for e in events[:5]]
            self.assertLess(max(baseline) - min(baseline), 0.2)
            for key in ('peak_force_bw', 'impulse_n_s', 'average_loading_rate_n_s'):
                values = [e[side]['loading'][key] for e in events[5:10]]
                self.assertTrue(all(b > a for a, b in zip(values, values[1:])))
            for key in ('maximum_deg', 'rom_deg'):
                values = [e[side]['kinematics'][key] for e in events[10:15]]
                self.assertTrue(all(b < a for a, b in zip(values, values[1:])))
        self.assertTrue(all(abs(e['bilateral']['loading']['peak_force_asymmetry_percent']) < 1e-10
                            for e in events[:15]))
        bias = [e['bilateral']['loading']['peak_force_asymmetry_percent'] for e in events[15:]]
        self.assertTrue(all(b > a for a, b in zip(bias, bias[1:])))
        self.assertAlmostEqual(bias[-1], 100 * 0.14 / 1.07)

    def test_adapter_preserves_context_quality_and_validation_only_derivatives(self):
        source = fixture('sensor_dropout')
        raw = to_raw_session(source)
        self.assertEqual(raw['baseline_demo'], source['baseline_demo'])
        for original, packet in zip(source['samples'], raw['samples']):
            for side in ('left', 'right'):
                self.assertEqual(packet[side]['insole'], original[side]['insole'])
                for key in ('angular_velocity_rad_s', 'angular_acceleration_rad_s2'):
                    self.assertEqual(packet['ground_truth'][f'{side}_knee_{key}'], original[side]['knee'][key])


if __name__ == '__main__':
    unittest.main()
