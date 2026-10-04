import copy
import pytest
from test_baseline_simulation import ROOT
from activity_svm import MovementModel, SVMConfig, extract_features, STATES
from synthetic_movement import training_records, held_out_records
from biomechanical_events import extract_events


@pytest.fixture(scope='module')
def datasets():
    return training_records(),held_out_records()


@pytest.mark.parametrize('profile',['imu_pair_plus_insole','imu_pair_only'])
def test_svm_profiles_synthetic_holdout(datasets,profile):
    train,test=datasets
    model=MovementModel(SVMConfig(profile)).fit(train,[r['group'] for r in test])
    assert not set(model.metadata['training_groups']) & set(model.metadata['held_out_groups'])
    predictions=[model.predict(r['session']) for r in test]
    assert [p['raw_svm_prediction'] for p in predictions]==[r['label'] for r in test]
    assert all(p['athlete_confirmed_movement'] is None and not p['prediction_is_confirmation'] for p in predictions)
    assert all(set(p['model_decision_scores'])==set(STATES) for p in predictions)
    assert not model.metadata['probability'] and not model.metadata['validated_on_real_athletes']


def test_feature_and_prediction_metadata_independence(datasets):
    train,test=datasets
    model=MovementModel().fit(train,[r['group'] for r in test])
    data=copy.deepcopy(test[-1]['session'])
    original=model.predict(data)
    data.update(session_id='squat',activity='soccer',scenario='walking',ground_truth={'label':'low_activity'},
                annotations=[],phases=['poison'],baseline_demo={'waveforms':'poison'})
    for row in data['samples']: row['ground_truth']='poison'
    assert model.predict(data)==original
    events=extract_events(data)
    assert extract_features(data,events=events)['event_source']==events['version']


def test_train_group_overlap_rejected(datasets):
    train,_=datasets
    with pytest.raises(ValueError): MovementModel().fit(train,[train[0]['group']])


def test_pair_only_uses_no_feet_and_invalid_data_rejected(datasets):
    train,test=datasets
    model=MovementModel(SVMConfig('imu_pair_only')).fit(train)
    data=copy.deepcopy(test[-1]['session'])
    expected=model.predict(data)
    for row in data['samples']:
        row.pop('left')
        row['right'].pop('insole')
    assert model.predict(data)==expected
    data['samples'][50]['right']['knee']['flexion_rad']=None
    with pytest.raises(ValueError): model.predict(data)
