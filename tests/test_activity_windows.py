import pytest
from test_baseline_simulation import ROOT
from activity_svm import MovementModel
from synthetic_movement import training_records, movement_fixture, ideal_calibration_records
from sensor_to_segment_calibration import calibrate_pair
from aligned_kinematics import reconstruct
from activity_windows import WindowConfig, window_predictions


@pytest.fixture(scope='module')
def model():
    return MovementModel().fit(training_records())


def test_windows_share_model_features_and_retain_episode(model):
    session=reconstruct(movement_fixture('repeated_jump_landing',9,12),calibrate_pair(ideal_calibration_records()))
    episode=model.predict(session)
    result=window_predictions(session,model)
    assert len(result['windows'])==3
    assert [w['start_index'] for w in result['windows']]==[0,300,600]
    assert result['config']['duration_s']==6 and result['config']['overlap_fraction']==.5
    for w in result['windows']:
        expected=model.predict({**session,'samples':session['samples'][w['start_index']:w['end_index']+1]})
        assert w['features']==expected['features']
        assert w['raw_svm_prediction']==expected['raw_svm_prediction']
    assert episode['athlete_confirmed_movement'] is None


@pytest.mark.parametrize('kwargs',[{'duration_s':0},{'overlap_fraction':1},{'feature_schema_version':'unknown'}])
def test_invalid_window_parameters(kwargs):
    with pytest.raises(ValueError): WindowConfig(**kwargs)


def test_short_recording_unavailable_not_padded(model):
    session=reconstruct(movement_fixture('low_activity',duration_s=2),calibrate_pair(ideal_calibration_records()))
    result=window_predictions(session,model)
    assert result['status']=='unavailable' and result['windows']==[] and result['reasons']
