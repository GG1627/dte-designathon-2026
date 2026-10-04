"""Movement candidates and confirmation gate: synthetic engineering tests only."""
import copy
import math
import json
import unittest

from test_baseline_simulation import ROOT, process
from activity_context import (DetectorRules, confirmed_activity, detect_movement_episodes,
                              with_activity_confirmation)
from baseline_simulation import (Rules, compare_evaluations, evaluation_fixture,
                                 fit_baseline, generate_reference_history)
from generate_raw_sensor_fixture import generate_fixture, to_raw_session
from process_sensor_session import process_session
from run_activity_context_demo import build_activity_demo


class ActivityContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = evaluation_fixture(process_session(generate_fixture()), 6)
        cls.detection = detect_movement_episodes(cls.session)
        cls.references = [process(with_activity_confirmation(process_session(to_raw_session(s)),
                          'basketball_training', 'manually_selected'))
                          for s in generate_reference_history()]
        cls.baseline = fit_baseline(cls.references)

    def test_landing_candidate_from_processed_signals(self):
        e = self.detection['episodes'][0]
        self.assertEqual(e['detected_movement'], 'repeated_jump_landing')
        self.assertEqual(e['features']['event_count'], 3)
        self.assertEqual(e['features']['bilateral_contact_pair_count'], 3)
        self.assertGreater(e['features']['median_knee_rom_deg'], 15)
        self.assertIn('basketball_training', e['candidate_activities'])
        self.assertFalse(self.detection['validated_classifier'])
        self.assertIsNone(e['confirmation']['confirmed_activity'])

    def test_twenty_landing_fixture_has_twenty_signal_contacts(self):
        data = json.loads((ROOT / 'data/processed/mock_training_20_landings_processed.json').read_text())
        episode = detect_movement_episodes(data)['episodes'][0]
        self.assertEqual(episode['detected_movement'], 'repeated_jump_landing')
        self.assertEqual(episode['features']['event_count'], 20)

    def test_quiet_gap_segments_separate_bouts(self):
        data = json.loads((ROOT / 'data/processed/mock_training_20_landings_processed.json').read_text())
        for row in data['samples']:
            if 8 <= row['timestamp_s'] <= 12:
                for side in ('left', 'right'):
                    row[side]['knee'].update(flexion_rad=math.radians(8), angular_velocity_rad_s=0)
                    row[side]['insole']['plantar_normal_force_n'] = 0
        episodes = detect_movement_episodes(data)['episodes']
        self.assertEqual(len(episodes), 2)
        self.assertLess(episodes[0]['end_s'], episodes[1]['start_s'])
        self.assertEqual([e['features']['event_count'] for e in episodes], [4, 14])

    def stationary(self):
        session = copy.deepcopy(self.session)
        for row in session['samples']:
            for side in ('left', 'right'):
                row[side]['knee'].update(flexion_rad=0, angular_velocity_rad_s=0)
                row[side]['insole']['plantar_normal_force_n'] = 0
        return session

    def test_low_activity_is_not_forced_into_a_sport(self):
        e = detect_movement_episodes(self.stationary())['episodes'][0]
        self.assertEqual(e['detected_movement'], 'low_activity')
        self.assertEqual(e['candidate_activities'], [])
        self.assertIsNone(e['confirmation']['confirmed_activity'])

    def test_ambiguous_motion_is_unclassified(self):
        session = self.stationary()
        for row in session['samples']:
            for side in ('left', 'right'):
                row[side]['knee'].update(flexion_rad=.1*math.sin(row['timestamp_s']),
                                         angular_velocity_rad_s=.1*math.cos(row['timestamp_s']))
        self.assertTrue(all(e['detected_movement'] == 'unclassified'
                            for e in detect_movement_episodes(session)['episodes']))

    def test_labels_annotations_truth_and_acceleration_are_not_detector_inputs(self):
        session = copy.deepcopy(self.session)
        session.update(session_id='running', activity='soccer_training', scenario='squat',
                       phases=['unrelated'], annotations=[], programmed={'scale': -99}, ground_truth=None)
        for row in session['samples']:
            row['ground_truth'] = 'invalid'
            for side in ('left', 'right'):
                row[side]['knee']['angular_acceleration_rad_s2'] = None
        self.assertEqual(detect_movement_episodes(session), self.detection)

    def test_invalid_or_missing_signals_are_not_interpolated(self):
        for fault in ('gap', 'quality', 'null'):
            session = copy.deepcopy(self.session)
            if fault == 'gap':
                del session['samples'][100]
            elif fault == 'quality':
                session['samples'][100]['left']['insole']['quality']['valid'] = False
            else:
                session['samples'][100]['right']['knee']['flexion_rad'] = None
            episode = detect_movement_episodes(session)['episodes'][0]
            self.assertEqual(episode['detected_movement'], 'unclassified')
            self.assertIsNone(episode['features']['event_count'])

    def test_confirmation_preserves_detector_and_biomechanics(self):
        original = copy.deepcopy(self.session)
        confirmed = with_activity_confirmation(original, 'basketball_training', detection=self.detection)
        corrected = with_activity_confirmation(confirmed, 'volleyball_training', 'user_corrected')
        self.assertEqual(original, self.session)
        self.assertEqual(corrected['samples'], original['samples'])
        self.assertEqual(corrected['activity'], original['activity'])
        ctx = corrected['baseline_demo']['activity_context']
        self.assertEqual(ctx['episodes'][0]['detected_movement'], 'repeated_jump_landing')
        self.assertEqual(ctx['confirmation']['confirmed_activity'], 'volleyball_training')
        self.assertEqual(ctx['confirmation']['source'], 'user_corrected')
        self.assertEqual(ctx['confirmation_history'][-1]['confirmed_activity'], 'basketball_training')

    def test_detector_only_cannot_contribute_even_if_legacy_context_matches(self):
        refs = copy.deepcopy(self.references)
        for ref in refs:
            ref['metadata']['activity_context'] = copy.deepcopy(self.detection)
        fitted = fit_baseline(refs, Rules(min_reference_sessions=1))
        self.assertTrue(all(m['eligible_session_count'] == 0 and m['median'] is None for m in fitted['metrics']))
        self.assertTrue(all(m['reference_status'] == 'insufficient_reference' for m in fitted['metrics']))
        self.assertTrue(all('activity_confirmation_required' in s['reasons']
                            for m in fitted['metrics'] for s in m['session_summaries']))

    def test_confirmed_and_manual_activity_select_reference(self):
        for source in ('user_confirmed', 'user_corrected', 'manually_selected'):
            current = with_activity_confirmation(self.session, 'basketball_training', source)
            self.assertEqual(confirmed_activity(current), 'basketball_training')
            evaluated = compare_evaluations(self.baseline, [process(current)])[0]
            self.assertTrue(all(c['comparison_availability'] == 'available' for c in evaluated['comparisons']))
            self.assertTrue(all(c['context']['activity'] == 'basketball_training' for c in evaluated['comparisons']))

    def test_old_reference_without_confirmation_provenance_is_not_trusted(self):
        baseline = copy.deepcopy(self.baseline)
        for metric in baseline['metrics']:
            metric.pop('activity_provenance')
        current = process(with_activity_confirmation(self.session, 'basketball_training'))
        result = compare_evaluations(baseline, [current])[0]
        self.assertTrue(all('reference_activity_confirmation_required' in c['reasons']
                            and c['signed_difference'] is None for c in result['comparisons']))

    def test_basketball_does_not_compare_with_volleyball(self):
        current = process(with_activity_confirmation(self.session, 'volleyball_training'))
        result = compare_evaluations(self.baseline, [current])[0]
        self.assertTrue(all('incompatible_context' in c['reasons'] and c['signed_difference'] is None
                            for c in result['comparisons']))
        self.assertEqual(result['insights'], [])

    def test_correction_rematches_extracted_metrics_without_recalculation(self):
        current = process(with_activity_confirmation(self.session, 'basketball_training'))
        corrected = with_activity_confirmation(current, 'volleyball_training', 'user_corrected')
        self.assertEqual(corrected['event_metrics'], current['event_metrics'])
        self.assertEqual(corrected['session_metrics'], current['session_metrics'])
        self.assertEqual(corrected['context']['activity'], 'volleyball_training')
        self.assertEqual(current['context']['activity'], 'basketball_training')

    def test_missing_confirmation_blocks_comparison_but_keeps_metrics(self):
        session = copy.deepcopy(self.session)
        session['baseline_demo']['activity_context'] = self.detection
        evaluated = compare_evaluations(self.baseline, [process(session)])[0]
        self.assertTrue(all(c['evaluation_median'] is not None and c['signed_difference'] is None
                            and 'activity_confirmation_required' in c['reasons'] for c in evaluated['comparisons']))

    def test_mixed_or_unconfirmed_episodes_cannot_label_whole_session(self):
        current = with_activity_confirmation(self.session, 'basketball_training', detection=self.detection)
        current['baseline_demo']['activity_context']['episodes'][0]['confirmation']['status'] = 'unconfirmed'
        self.assertIsNone(confirmed_activity(current))
        with self.assertRaises(ValueError):
            with_activity_confirmation(self.session, 'basketball_training', 'detector_only')

    def test_running_and_squat_candidates_use_combinations(self):
        running = self.stationary()
        squat = self.stationary()
        for row, other in zip(running['samples'], squat['samples']):
            t = row['timestamp_s']
            for side, offset in (('left', 0), ('right', .3)):
                angle = math.radians(20)*(1-math.cos(2*math.pi*t))
                velocity = math.radians(20)*2*math.pi*math.sin(2*math.pi*t)
                row[side]['knee'].update(flexion_rad=angle, angular_velocity_rad_s=velocity)
                phase = (t-offset) % .6
                row[side]['insole']['plantar_normal_force_n'] = 100 if .05 < phase < .23 else 0
                other[side]['knee'].update(flexion_rad=angle, angular_velocity_rad_s=velocity)
                other[side]['insole']['plantar_normal_force_n'] = 100
        self.assertEqual(detect_movement_episodes(running)['episodes'][0]['detected_movement'], 'running_like')
        self.assertEqual(detect_movement_episodes(squat)['episodes'][0]['detected_movement'], 'squat_like_repetitions')

    def test_judge_demo_proves_basketball_volleyball_separation(self):
        result = build_activity_demo()
        states = {s['activity']: s for s in result['states']}
        self.assertEqual(states['basketball_training']['eligible_session_count'], 5)
        self.assertEqual(states['volleyball_training']['eligible_session_count'], 0)
        self.assertEqual(states[None]['eligible_session_count'], 0)
        self.assertTrue(all(c['comparison_availability'] == 'available'
                            for c in states['basketball_training']['comparisons']))


if __name__ == '__main__':
    unittest.main()
