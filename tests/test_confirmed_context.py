import copy
import pytest
from test_baseline_simulation import ROOT
from athlete_confirmation import confirm_record, confirmation_record
from contextual_reference import context_key, fit_personal_reference, compare_personal_reference
from baseline_simulation import Rules


def record(index=0,movement='repeated_jump_landing',activity='basketball_training'):
    event={'event_id':'contact','knee_flexion_waveform_rad':[0,.4,0],
           'loading':{side:{'peak_force_bw':1.7,'impulse_n_s':100} for side in ('left','right')}}
    result={'session_id':f'session_{index}','participant_id':'athlete','side':'right','synthetic':True,
        'body_weight_n':75*9.80665, 'biomechanics':{'session_metrics':{'knee_rom_rad':.4,
            'left_peak_plantar_normal_force_bw':1.7,'right_peak_plantar_normal_force_bw':1.7},
            'events':[{**copy.deepcopy(event),'event_id':f'contact_{i}'} for i in range(3)]},
        'model_history':{'raw_svm_prediction':'repeated_jump_landing','temporal_model_prediction':'repeated_jump_landing'}}
    result=confirm_record(result,movement,activity,'user_confirmed' if movement else None,'user_confirmed' if activity else None)
    result['context']=context_key(result,{'profile':'imu_pair_plus_insole','side':'right'}, {'filter':'none','event':'canonical'})
    return result


@pytest.mark.parametrize('movement,activity',[(None,'basketball_training'),('repeated_jump_landing',None),(None,None)])
def test_both_confirmations_required(movement,activity):
    data=record(movement=movement,activity=activity)
    reference=fit_personal_reference([data],Rules(min_reference_sessions=1))
    assert all(m['eligible_session_count']==0 for m in reference['metrics'])
    assert compare_personal_reference(data,reference)['status']=='requires_confirmation'


def test_correction_preserves_history_and_metrics():
    original=record()
    corrected=confirm_record(original,'squat_like_repetitions','basketball_training','user_corrected','user_confirmed')
    assert corrected['model_history']==original['model_history']
    assert corrected['biomechanics']==original['biomechanics']
    assert corrected['confirmation']['movement_source']=='user_corrected'
    assert corrected['confirmation_history'][-1]['confirmed_movement']=='repeated_jump_landing'
    assert original['confirmation']['confirmed_movement']=='repeated_jump_landing'


@pytest.mark.parametrize('mismatch',['activity','movement','configuration','processing','side','participant'])
def test_exact_reference_context(mismatch):
    history=[record(i) for i in range(5)]
    reference=fit_personal_reference(history)
    before=copy.deepcopy(reference)
    current=record(6)
    if mismatch=='activity': current=record(6,activity='volleyball_training')
    elif mismatch=='movement': current=record(6,movement='running_like')
    else:
        key={'configuration':'configuration_signature','processing':'processing_signature','side':'side','participant':'participant_id'}[mismatch]
        current['context'][key]='different'
    assert compare_personal_reference(current,reference)['status']=='insufficient_reference'
    assert compare_personal_reference(record(6),reference)['status']=='ready'
    assert reference==before


def test_forged_movement_key_not_confirmation():
    data=record(movement=None)
    data['context']['confirmed_movement']='repeated_jump_landing'
    reference=fit_personal_reference([data],Rules(min_reference_sessions=1))
    assert all(m['eligible_session_count']==0 for m in reference['metrics'])
