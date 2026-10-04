import copy
import numpy as np
import pytest
from test_baseline_simulation import ROOT
from test_confirmed_context import record
from waveform_similarity import dtw_distance,fit_waveform_reference,compare_waveforms


def test_dtw_identical_stretched_different_and_magnitude_separate():
    wave=np.sin(np.linspace(0,np.pi,61))
    stretched=np.sin(np.linspace(0,np.pi,91))
    different=np.cos(np.linspace(0,2*np.pi,61))
    assert dtw_distance(wave,wave)['distance']==pytest.approx(0)
    assert dtw_distance(wave,stretched)['distance'] < dtw_distance(wave,different)['distance']
    assert dtw_distance(wave,wave*2+4)['distance']==pytest.approx(0,abs=1e-12)
    result=dtw_distance(wave,wave)
    assert 'z_score' in result['normalization']
    assert not {'safe','unsafe','normal','abnormal','risk'} & set(result)


@pytest.mark.parametrize('bad',[[0,0,0],[0,None,1],[0,float('inf'),1],[0,1],[1e308,-1e308,1e308]])
def test_dtw_missing_or_undefined_shape_unavailable(bad):
    with pytest.raises(ValueError): dtw_distance(bad,[0,1,0])


def test_medoid_is_an_eligible_confirmed_event_and_frozen():
    history=[record(i) for i in range(5)]
    history[0]['biomechanics']['events'][0]['knee_flexion_waveform_rad']=[0,.1,.4]
    original=copy.deepcopy(history)
    reference=fit_waveform_reference(history)
    assert history==original and reference['status']=='ready'
    ref=reference['references'][0]
    assert ref['contributing_event_count']==15 and ref['eligible_session_count']==5
    medoid=ref['medoid']
    assert medoid['values']==[0,.4,0]
    before=copy.deepcopy(reference)
    current=record(6)
    scalar=copy.deepcopy(current['biomechanics'])
    assert compare_waveforms(current,reference)['status']=='ready'
    assert reference==before and current['biomechanics']==scalar
    assert compare_waveforms(record(7,activity='volleyball_training'),reference)['status']=='insufficient_reference'
    assert compare_waveforms(record(7,movement=None),reference)['status']=='requires_confirmation'


def test_waveform_history_requires_sessions_not_five_trials():
    data=record()
    data['biomechanics']['events']*=5
    assert fit_waveform_reference([data])['status']=='insufficient_reference'
    assert fit_waveform_reference([record(i,movement=None) for i in range(5)])['status']=='insufficient_reference'


def test_waveform_forged_context_does_not_override_confirmation():
    reference=fit_waveform_reference([record(i) for i in range(5)])
    current=record(6,activity='volleyball_training')
    current['context']=record()['context']
    assert compare_waveforms(current,reference)['status']=='invalid_input'
