"""Software integration and hard availability gates; not hardware validation."""
import copy
import json
from dataclasses import replace

import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from test_baseline_simulation import ROOT
from kintra_pipeline import run_pipeline, PipelineConfig
from synthetic_bilateral import bilateral_fixture, fixture_config, SCENARIOS
from synthetic_movement import ideal_calibration_records, training_records, movement_fixture
from sensor_configuration import Sensor, KneeSensors, SensorConfiguration, SIDES
from biomechanical_events import extract_events
from bilateral_comparison import compare_knees, compare_plantar, comparison
from contextual_reference import fit_personal_reference, compare_personal_reference
from waveform_similarity import fit_waveform_reference, compare_waveforms
from activity_svm import MovementModel
from activity_temporal import synthetic_temporal_model
from measurement_reliability import measurement_change_reliability


@pytest.fixture(scope='module')
def cases():
    return {s:run_pipeline(raw:=bilateral_fixture(s),fixture_config(raw,s)) for s in SCENARIOS}


@pytest.fixture(scope='module')
def references():
    histories = {s:[] for s in SIDES}
    for i in range(5):
        raw = bilateral_fixture(session_id=f'bilateral_history_{i}')
        result = run_pipeline(raw,fixture_config(raw,chronological_index=i+1))
        for side in SIDES:
            histories[side].append(result['knees'][side]['record'])
    return histories,{s:fit_personal_reference(histories[s]) for s in SIDES}, {s:fit_waveform_reference(histories[s]) for s in SIDES}


def assert_null_gate(output):
    assert output['status']=='unavailable' and output['reasons']
    assert output['events']==[]
    assert all(v is None for metric in output['metrics'].values() for v in metric.values())


def pairs():
    return extract_events(bilateral_fixture(),knee_required=False)['bilateral_pairs']


def test_four_imu_fixture_has_both_independent_knees(cases):
    raw = bilateral_fixture()
    original = copy.deepcopy(raw)
    result = run_pipeline(raw,fixture_config(raw))
    assert raw==original
    assert result==cases['symmetric']
    assert result['schema_version']=='kintra-bilateral-session/2.0.0'
    for side in SIDES:
        knee = result['knees'][side]
        assert knee['status']=='ready' and knee['kinematics']['status']=='ready'
        assert len(knee['biomechanics']['events'])==3
        assert all('knee' not in row['right' if side=='left' else 'left'] for row in knee['kinematics']['samples'])
        for row in knee['kinematics']['samples']:
            for q in row[side]['orientation'].values():
                assert np.isfinite(q).all() and np.linalg.norm(q)==pytest.approx(1)
    assert 'ground_truth' not in json.dumps(result,allow_nan=False)


def test_independent_left_mounting_calibration_does_not_change_right(cases):
    raw = bilateral_fixture()
    config = fixture_config(raw)
    options = copy.deepcopy(config.side_options)
    for segment,angles in (('thigh',(12,-8,5)),('shank',(-20,10,30))):
        rotation = Rotation.from_euler('xyz',angles,degrees=True).as_matrix()
        for row in raw['samples']:
            packet = row['left']['imu'][segment]
            for channel in ('gyro_rad_s','accel_m_s2'):
                packet[channel] = dict(zip('xyz',(rotation.T @ list(packet[channel].values())).tolist()))
        for channel in ('static_accel','positive_flexion_gyro'):
            options['left']['calibration_records'][segment][channel] = (
                np.array(options['left']['calibration_records'][segment][channel]) @ rotation).tolist()
    result = run_pipeline(raw,replace(config,side_options=options))
    assert result['knees']['right']==cases['symmetric']['knees']['right']
    left = result['knees']['left']
    assert left['calibration']['segments']['thigh']['R_sensor_to_segment'] != left['calibration']['segments']['shank']['R_sensor_to_segment']
    assert left['status']=='ready'
    assert result['bilateral']['knee_kinematics']['metrics']['rom_deg']['absolute_difference'] < .05


@pytest.mark.parametrize('side',SIDES)
@pytest.mark.parametrize('failure',('calibration','input'))
def test_one_side_failure_preserves_other(side,failure,cases):
    raw = bilateral_fixture()
    options = {}
    if failure=='calibration':
        records = ideal_calibration_records()
        records['shank']['positive_flexion_gyro'] = [[0,0,0]]*60
        options[side] = {'calibration_records':records}
    else:
        raw['samples'][100][side]['imu']['shank']['gyro_rad_s']['y'] = None
    result = run_pipeline(raw,fixture_config(raw,side_options=options))
    assert result['knees'][side]['status']==('calibration_required' if failure=='calibration' else 'invalid_input')
    other = 'right' if side=='left' else 'left'
    assert result['knees'][other]==cases['symmetric']['knees'][other]
    assert result['bilateral']['plantar_loading']['status']=='ready'
    assert_null_gate(result['bilateral']['knee_kinematics'])


@pytest.mark.parametrize('scenario',('left_calibration_invalid','right_knee_absent','missing_left','incompatible_processing'))
def test_failed_gates_have_no_numeric_comparison(scenario,cases):
    assert_null_gate(cases[scenario]['bilateral']['knee_kinematics'])
    assert cases[scenario]['bilateral']['plantar_loading']['status']=='ready'


def test_actual_demo_availability_no_fabricated_opposite_knee(cases):
    result = cases['missing_left']
    assert result['configuration']['mode']=='single_knee_plus_mock_insoles'
    assert result['knees']['right']['status']=='ready'
    assert result['knees']['left']['status']=='unavailable'
    assert result['knees']['left']['record'] is None
    assert 'samples' not in result['knees']['left']['kinematics']
    assert result['bilateral']['plantar_loading']['source']=='synthetic_demo'
    assert all(result['insoles'][s]['source']=='synthetic_demo' for s in SIDES)


def test_both_knees_absent_still_have_foot_metrics():
    raw = bilateral_fixture()
    for side in SIDES:
        raw['sources'][side].pop('knee')
        for row in raw['samples']: row[side].pop('imu')
    result = run_pipeline(raw,fixture_config(raw))
    assert all(result['knees'][s]['status']=='unavailable' for s in SIDES)
    assert_null_gate(result['bilateral']['knee_kinematics'])
    assert result['bilateral']['plantar_loading']['status']=='ready'


@pytest.mark.parametrize('field,value',(('confirmed_activity','volleyball_training'),('confirmed_movement','running_like'),('confirmed_activity',None)))
def test_bilateral_requires_compatible_confirmed_context(field,value):
    raw = bilateral_fixture()
    result = run_pipeline(raw,fixture_config(raw,side_options={'left':{field:value}}))
    assert all(result['knees'][s]['status']=='ready' for s in SIDES)
    assert_null_gate(result['bilateral']['knee_kinematics'])


def test_same_predictions_never_confirm_movements(cases):
    raw = bilateral_fixture()
    result = run_pipeline(raw,fixture_config(raw,confirmed_movement=None,confirmed_activity=None,
                          movement_source=None,activity_source=None))
    assert result['activity']['confirmation']['status']=='requires_confirmation'
    for side in SIDES:
        assert result['knees'][side]['personal_reference']['status']=='requires_confirmation'
    assert_null_gate(result['bilateral']['knee_kinematics'])


def test_configuration_mismatch_blocks_bilateral():
    raw = bilateral_fixture()
    config = fixture_config(raw)
    sensors = replace(config.sensor_configuration,knee_protocols={'left':'v1','right':'v2'})
    result = run_pipeline(raw,replace(config,sensor_configuration=sensors))
    assert all(result['knees'][s]['status']=='ready' for s in SIDES)
    assert 'incompatible_sensor_configuration' in result['bilateral']['knee_kinematics']['reasons']
    assert_null_gate(result['bilateral']['knee_kinematics'])


def test_acquisition_context_mismatch_blocks_bilateral():
    raw = bilateral_fixture()
    result = run_pipeline(raw,fixture_config(raw,side_options={'left':{'acquisition_context':{'task':'different'}}}))
    assert_null_gate(result['bilateral']['knee_kinematics'])


def test_forged_confirmation_and_invalid_event_metrics_are_gated(cases):
    knees = copy.deepcopy(cases['symmetric']['knees'])
    knees['left']['record']['confirmation']['confirmed_activity']='volleyball_training'
    assert_null_gate(compare_knees(knees,pairs()))
    knees = copy.deepcopy(cases['symmetric']['knees'])
    knees['right']['biomechanics']['events'][1]['kinematics']['rom_deg']=None
    assert_null_gate(compare_knees(knees,pairs()))


def test_unpaired_events_block_all_comparisons(cases):
    assert_null_gate(compare_knees(cases['symmetric']['knees'],pairs()[:1]))
    assert_null_gate(compare_plantar(cases['symmetric']['insoles'],pairs()[:1]))


def test_symmetric_metrics_near_zero(cases):
    for channel in cases['symmetric']['bilateral'].values():
        assert channel['status']=='ready' and len(channel['events'])==3
        for metric in channel['metrics'].values():
            assert metric['absolute_difference']==pytest.approx(0,abs=1e-10)
            assert metric['asymmetry_percent'] is None or abs(metric['asymmetry_percent']) < 1e-10


def test_programmed_unilateral_rom_change_keeps_left_and_feet_same(cases):
    original,changed = cases['symmetric'],cases['right_rom_reduced']
    assert original['knees']['left']['kinematics']==changed['knees']['left']['kinematics']
    metric = changed['bilateral']['knee_kinematics']['metrics']['rom_deg']
    assert metric['right']/metric['left']==pytest.approx(.8,abs=.01)
    assert metric['signed_difference_right_minus_left'] < -5
    assert changed['bilateral']['plantar_loading']['metrics']==original['bilateral']['plantar_loading']['metrics']


def test_programmed_unilateral_force_change_keeps_motion_same(cases):
    original,changed = cases['symmetric'],cases['right_force_increased']
    for side in SIDES:
        assert [r[side]['knee'] for r in original['knees'][side]['kinematics']['samples']]==[
            r[side]['knee'] for r in changed['knees'][side]['kinematics']['samples']]
    metric = changed['bilateral']['plantar_loading']['metrics']['peak_force_bw']
    assert metric['right']==pytest.approx(metric['left']*1.2)
    assert metric['asymmetry_percent']==pytest.approx(18.18181818)
    assert metric['signed_difference_right_minus_left'] > 0


def test_zero_denominator_and_signed_convention():
    zero = comparison(0,0)
    assert zero['absolute_difference']==0 and zero['asymmetry_percent'] is None
    assert zero['signed_asymmetry_percent'] is None
    change = comparison(1,1.2)
    assert change['asymmetry_percent']==pytest.approx(abs(1-1.2)/1.1*100)
    assert change['signed_difference_right_minus_left']==pytest.approx(.2)


@pytest.mark.parametrize('side',SIDES)
def test_dropout_foot_does_not_block_knee_or_other_foot(side):
    raw = bilateral_fixture()
    raw['samples'][120][side]['insole']['quality']['valid']=False
    raw['samples'][120][side]['insole']['plantar_normal_force_n']=None
    original = copy.deepcopy(raw)
    result = run_pipeline(raw,fixture_config(raw))
    assert raw==original
    assert all(result['knees'][s]['kinematics']['status']=='ready' for s in SIDES)
    assert result['insoles'][side]['status']=='invalid_input'
    assert result['insoles']['right' if side=='left' else 'left']['status']=='ready'
    assert_null_gate(result['bilateral']['plantar_loading'])
    assert_null_gate(result['bilateral']['knee_kinematics'])


@pytest.mark.parametrize('side',SIDES)
def test_own_side_reference_and_cross_side_rejection(side,references,cases):
    history,scalar,wave = references
    current = cases['symmetric']['knees'][side]['record']
    other = 'right' if side=='left' else 'left'
    assert compare_personal_reference(current,scalar[side])['status']=='ready'
    assert compare_personal_reference(current,scalar[other])['status']=='insufficient_reference'
    assert current['context']['side']==side
    assert scalar[side]['metrics'][0]['context']['side']==side
    assert scalar[side]['metrics'][0]['source']=='synthetic_demo'
    assert history[side][0]['context']['configuration_signature']!=history[other][0]['context']['configuration_signature']
    assert compare_waveforms(current,wave[side])['status']=='ready'
    assert compare_waveforms(current,wave[other])['status']=='insufficient_reference'
    assert wave[side]['references'][0]['source']=='synthetic_demo'


def test_own_reference_recovers_unilateral_change_and_keeps_history_fixed(references):
    history,scalar,wave = references
    before = copy.deepcopy((history,scalar,wave))
    raw = bilateral_fixture('right_rom_reduced')
    result = run_pipeline(raw,fixture_config(raw,chronological_index=6,
        side_options={s:{'scalar_reference':scalar[s],'waveform_reference':wave[s],
            'longitudinal_history':tuple(history[s])} for s in SIDES}))
    for side in SIDES:
        knee = result['knees'][side]
        c = next(c for c in knee['personal_reference']['comparisons'] if c['metric']=='knee_rom_rad')
        assert c['comparison_availability']=='available'
        assert c['source']=='synthetic_demo'
        assert c['direction']==('near_reference' if side=='left' else 'decreased')
        assert c['percent_difference']==pytest.approx(0 if side=='left' else -20,abs=.5)
        assert knee['waveform_comparison']['status']=='ready'
        assert knee['longitudinal']['context']['side']==side
        assert knee['longitudinal']['direction']==('unchanged' if side=='left' else 'decreased')
        assert knee['longitudinal']['reference_updating']=='none; analytics_only'
        assert knee['reliability']['status']=='reliability_not_established'
        assert all(r['change_exceeds_mdc'] is None for r in knee['reliability']['results'])
    assert before==(history,scalar,wave)


@pytest.mark.parametrize('side',SIDES)
def test_mdc_side_scope_and_bilateral_reliability_remain_fail_closed(side,references,cases):
    context = references[0][side][0]['context']
    evidence = {'metric':'knee_rom_rad','unit':'rad','mdc':.01,'empirically_established':True,
                'source':'TEST ONLY injected contract evidence','context':{**context,'side':'right' if side=='left' else 'left'}}
    result = measurement_change_reliability(.8,.4,'knee_rom_rad','rad',context,evidence)
    assert result['status']=='reliability_not_established' and result['change_exceeds_mdc'] is None
    for channel in cases['symmetric']['bilateral'].values():
        assert channel['measurement_reliability']['change_exceeds_measurement_error'] is None


def test_provenance_survives_metrics_references_interpretation(cases):
    result = cases['symmetric']
    for side in SIDES:
        knee = result['knees'][side]
        assert knee['source']=='synthetic_demo'
        assert set(knee['biomechanics']['metric_sources'].values())=={'synthetic_demo'}
        assert knee['record']['measurement_sources']['knee']=='synthetic_demo'
        for event in knee['biomechanics']['events']:
            assert event['kinematics']['source']=='synthetic_demo'
            assert all(event['loading'][s]['source']=='synthetic_demo' for s in SIDES)
        assert result['interpretation']['sources'][side]['knee']=='synthetic_demo'


def test_synthetic_fixture_cannot_be_declared_hardware(cases):
    raw = bilateral_fixture()
    config = fixture_config(raw)
    sensors = config.sensor_configuration
    knees = {s:KneeSensors(*(replace(getattr(sensors.knees[s],segment),source='hardware')
                             for segment in ('thigh','shank'))) for s in SIDES}
    result = run_pipeline(raw,replace(config,sensor_configuration=replace(sensors,knees=knees)))
    for side in SIDES:
        assert result['knees'][side]['status']=='invalid_input'
        assert result['knees'][side]['source']=='unavailable'
        assert result['knees'][side]['record'] is None
        assert 'synthetic_measurements_cannot_be_labeled_hardware' in result['knees'][side]['reasons']
    assert_null_gate(result['bilateral']['knee_kinematics'])


def test_synthetic_packet_provenance_survives_missing_top_level_flag():
    raw = bilateral_fixture()
    config = fixture_config(raw)
    raw['synthetic']=False
    sensors = config.sensor_configuration
    feet = {s:replace(sensors.insoles[s],source='hardware') for s in SIDES}
    result = run_pipeline(raw,replace(config,sensor_configuration=replace(sensors,insoles=feet)))
    assert all(result['insoles'][s]['status']=='invalid_input' and result['insoles'][s]['source']=='unavailable' for s in SIDES)
    assert_null_gate(result['bilateral']['plantar_loading'])


@pytest.mark.parametrize('fault',('identity','absent_packet','absent_segment'))
def test_no_absent_sensor_becomes_zero(fault):
    raw = bilateral_fixture()
    config = fixture_config(raw)
    if fault=='identity': raw['sources']['left']['knee'][0]='different_imu'
    elif fault=='absent_packet':
        for row in raw['samples']: row['left'].pop('imu')
    else:
        for row in raw['samples']: row['left']['imu'].pop('thigh')
    result = run_pipeline(raw,config)
    assert result['knees']['left']['status']=='invalid_input'
    assert result['knees']['right']['status']=='ready'
    assert 'samples' not in result['knees']['left']['kinematics']
    assert_null_gate(result['bilateral']['knee_kinematics'])


def test_sensor_schema_supports_hardware_pair_and_mock_feet():
    pair = KneeSensors(Sensor(True,'hardware','esp32_thigh'),Sensor(True,'hardware','esp32_shank'))
    config = SensorConfiguration('single_knee_plus_mock_insoles',{'left':KneeSensors(),'right':pair},
        {s:Sensor(True,'synthetic_demo',f'software_{s}_foot') for s in SIDES})
    assert config.metadata()['knees']['right']['thigh']['source']=='hardware'
    assert config.metadata()['knees']['left']['thigh']['present'] is False
    with pytest.raises(ValueError): Sensor(False,'hardware','absent')
    with pytest.raises(ValueError): replace(config,knees={'left':pair,'right':pair})


def test_existing_svm_hmm_work_without_feature_extension():
    training = training_records()
    svm = MovementModel().fit(training)
    hmm = synthetic_temporal_model(svm,training)
    raw = bilateral_fixture()
    result = run_pipeline(raw,fixture_config(raw,movement_model=svm,temporal_model=hmm,
        confirmed_movement=None,confirmed_activity=None,movement_source=None,activity_source=None))
    activity = result['activity']
    assert activity['motion_source_side']=='right'
    assert activity['svm']['status']=='ready' and activity['temporal']['status']=='ready'
    assert len(activity['svm']['episode']['features']['values'])==19
    assert activity['svm']['episode']['features']['schema_version']=='one-knee-motion-bilateral-feet/1.0.0'
    assert activity['svm']['episode']['prediction_is_confirmation'] is False
    assert activity['temporal']['prediction_is_confirmation'] is False
    assert activity['confirmation']['status']=='requires_confirmation'
    assert result['knees']['left']['activity_svm']['status']=='unavailable'
    assert_null_gate(result['bilateral']['knee_kinematics'])


def test_legacy_profiles_keep_original_contract():
    for profile in ('imu_pair_plus_insole','imu_pair_only'):
        result = run_pipeline(movement_fixture('repeated_jump_landing'),PipelineConfig(
            profile=profile,calibration_records=ideal_calibration_records()))
        assert result['version']=='kintra-modular-pipeline/1.0.0'
        assert 'knees' not in result
        assert result['stages']['kinematics']['status']=='ready'


def test_app_contract_explicit_states_and_unchanged_act_verify(cases):
    result = cases['missing_left']
    assert {'configuration','input_quality','knees','insoles','activity','bilateral','interpretation','act','verify'} <= set(result)
    assert result['act']['status']==result['verify']['status']=='not_yet_implemented'
    assert result['interpretation']['medical_inference'] is False
    json.dumps(result,allow_nan=False)


@pytest.mark.parametrize('side',SIDES)
def test_foot_ewma_is_separate_for_each_side(side,references):
    history,scalar,wave = references
    raw = bilateral_fixture('right_force_increased')
    result = run_pipeline(raw,fixture_config(raw,chronological_index=6,
        side_options={s:{'longitudinal_history':tuple(history[s]),
            'trend_metric':f'{s}_peak_plantar_normal_force_bw'} for s in SIDES}))
    trend = result['knees'][side]['longitudinal']
    assert trend['status']=='ready' and trend['context']['side']==side
    assert trend['metric']==f'{side}_peak_plantar_normal_force_bw'
    assert trend['points'][-1]['value']==pytest.approx(1.7 if side=='left' else 2.04)
    assert trend['points'][-1]['ewma']==pytest.approx(1.7 if side=='left' else 1.802)
    assert trend['direction']==('unchanged' if side=='left' else 'increased')


def test_cross_side_ewma_history_cannot_be_pooled(references):
    raw = bilateral_fixture()
    result = run_pipeline(raw,fixture_config(raw,chronological_index=6,
        side_options={'left':{'longitudinal_history':tuple(references[0]['right'])}}))
    trend = result['knees']['left']['longitudinal']
    assert trend['status']=='unavailable'
    assert all(p['ewma'] is None and 'incompatible_context' in p['reasons'] for p in trend['points'][:-1])


def test_wrong_side_and_different_session_cannot_be_compared(cases):
    knees = copy.deepcopy(cases['symmetric']['knees'])
    knees['left']['record']['context']['side']='right'
    assert_null_gate(compare_knees(knees,pairs()))
    knees = copy.deepcopy(cases['symmetric']['knees'])
    knees['right']['record']['session_id']='different_day'
    assert_null_gate(compare_knees(knees,pairs()))
    feet = copy.deepcopy(cases['symmetric']['insoles'])
    feet['right']['session_id']='different_day'
    assert_null_gate(compare_plantar(feet,pairs()))
