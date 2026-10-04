import copy
import json
import pytest
from test_baseline_simulation import ROOT
from activity_svm import MovementModel,SVMConfig
from activity_temporal import synthetic_temporal_model
from synthetic_movement import movement_fixture,training_records,ideal_calibration_records
from kintra_pipeline import run_pipeline,PipelineConfig,STAGES
from contextual_reference import fit_personal_reference
from waveform_similarity import fit_waveform_reference


@pytest.fixture(scope='module')
def models():
    train=training_records()
    svm=MovementModel().fit(train)
    return svm,synthetic_temporal_model(svm,train)


def config(models,**kwargs):
    return PipelineConfig(calibration_records=ideal_calibration_records(),movement_model=models[0],
        temporal_model=models[1],**kwargs)


def test_every_stage_records_status_and_truth_does_not_leak(models):
    raw=movement_fixture('repeated_jump_landing',9,12)
    original=copy.deepcopy(raw)
    expected=run_pipeline(raw,config(models))
    assert set(expected['stages'])==set(STAGES)
    assert all(set(('status','version','provenance','reasons')) <= set(s) for s in expected['stages'].values())
    assert all(s['reasons'] for s in expected['stages'].values() if s['status'] not in ('ready',))
    assert expected['stages']['confirmation']['status']=='requires_confirmation'
    assert expected['stages']['personal_reference']['status']=='requires_confirmation'
    assert expected['stages']['temporal_model']['status']=='ready'
    assert raw==original
    raw.update(activity='soccer',scenario='squat',annotations=[],phases=['poison'],ground_truth='poison')
    for row in raw['samples']: row['ground_truth']='poison'
    assert run_pipeline(raw,config(models))==expected
    assert 'ground_truth' not in json.dumps(expected,allow_nan=False)
    assert all('knee' not in r.get('left',{}) for r in expected['stages']['kinematics']['samples'])


def test_missing_calibration_and_invalid_signal_explicit_states(models):
    raw=movement_fixture('repeated_jump_landing',9)
    result=run_pipeline(raw,PipelineConfig(movement_model=models[0]))
    assert result['stages']['calibration']['status']=='calibration_required'
    assert result['stages']['kinematics']['status']=='unavailable'
    raw['samples'][50]['right']['imu']['shank']['gyro_rad_s']['x']=None
    result=run_pipeline(raw,config(models))
    assert result['stages']['input_quality']['status']=='invalid_input' and result['record'] is None
    assert all(s['reasons'] for s in result['stages'].values() if s['status']!='ready')


def test_end_to_end_confirmed_reference_context_and_reliability(models):
    selections={'confirmed_movement':'repeated_jump_landing','confirmed_activity':'basketball_training',
                'movement_source':'manually_selected','activity_source':'manually_selected'}
    history=[run_pipeline(movement_fixture('repeated_jump_landing',i),config(models,chronological_index=i+1,**selections))['record'] for i in range(5)]
    reference=fit_personal_reference(history)
    wave_reference=fit_waveform_reference(history)
    before=copy.deepcopy(reference)
    kwargs={**selections,'scalar_reference':reference,'waveform_reference':wave_reference,'chronological_index':6}
    raw=movement_fixture('repeated_jump_landing',9)
    confirmed=run_pipeline(raw,config(models,**kwargs))
    assert confirmed['stages']['personal_reference']['status']=='ready'
    assert confirmed['stages']['waveform_comparison']['status']=='ready'
    assert confirmed['stages']['reliability']['status']=='reliability_not_established'
    assert all(r['change_exceeds_mdc'] is None for r in confirmed['stages']['reliability']['results'])
    wrong=run_pipeline(raw,config(models,**{**kwargs,'confirmed_activity':'volleyball_training'}))
    corrected=run_pipeline(raw,config(models,**{**kwargs,'confirmed_movement':'squat_like_repetitions','movement_source':'user_corrected'}))
    for result in (wrong,corrected):
        assert result['stages']['personal_reference']['status']=='insufficient_reference'
        assert result['record']['biomechanics']==confirmed['record']['biomechanics']
        assert result['record']['model_history']==confirmed['record']['model_history']
    assert reference==before
    assert confirmed['stages']['act']['status']=='not_yet_implemented'
    assert 'confirmed_movement' in confirmed['stages']['verify']['match_fields']


def test_imu_only_fallback_has_activity_but_no_invented_contact_metrics():
    training=training_records()
    model=MovementModel(SVMConfig('imu_pair_only')).fit(training)
    raw=movement_fixture('repeated_jump_landing',9)
    for row in raw['samples']:
        row.pop('left')
        row['right'].pop('insole')
    result=run_pipeline(raw,PipelineConfig(profile='imu_pair_only',calibration_records=ideal_calibration_records(),movement_model=model))
    assert result['stages']['kinematics']['status']=='ready'
    assert result['stages']['activity_svm']['status']=='ready'
    assert result['stages']['events']['status']=='unavailable'
    assert result['record']['biomechanics']['session_metrics']=={}


def test_pipeline_missing_geometry_is_invalid_input_not_exception(models):
    raw=movement_fixture('repeated_jump_landing',9)
    raw.pop('insole_geometry')
    result=run_pipeline(raw,config(models))
    assert result['stages']['input_quality']['status']=='invalid_input'
    assert 'insole_geometry_required' in result['stages']['input_quality']['reasons']
    assert result['record'] is None
