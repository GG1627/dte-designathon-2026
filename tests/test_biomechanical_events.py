import copy
import pytest
from test_baseline_simulation import fixture
from process_sensor_session import process_session
from generate_raw_sensor_fixture import to_raw_session
from biomechanical_events import extract_events, EventProtocol, contact_indices
from activity_context import contact_intervals, DetectorRules
from event_biomechanics import event_metrics


def processed():
    result = process_session(to_raw_session(fixture()))
    result['monitored_knee_side'] = 'right'
    for row in result['samples']: row['left'].pop('knee')
    return result


def test_canonical_sensor_events_and_biomechanics():
    data = processed()
    events = extract_events(data)
    assert events['status'] == 'ready' and len(events['landings']) == 3
    assert len(events['bilateral_pairs']) == 3
    assert len(events['noncontact_intervals']) == 4
    assert contact_intervals(data['samples'],'right',DetectorRules()) == contact_indices(data['samples'],'right')
    metrics = event_metrics(data,events)
    assert metrics['event_source'] == events['version']
    assert all(e['event_source']==events['version'] for e in metrics['events'])
    assert metrics['uninstrumented_knee']['status'] == 'unavailable'
    for event in metrics['events']:
        loading=event['loading']['right']
        assert loading['contact_time_s'] > 0
        assert loading['average_loading_rate_n_s'] > 0
        assert loading['quality']['valid']
    assert events['protocol']['validated_for_current_hardware'] is False


def test_event_metadata_poisoning():
    data = processed()
    expected = extract_events(data)
    data.update(scenario='running',activity='soccer',annotations=[],ground_truth='poison')
    assert extract_events(data)==expected


@pytest.mark.parametrize('fault',['quality','gap','pressure','nan','time'])
def test_invalid_events_unavailable(fault):
    data=processed()
    if fault=='gap': del data['samples'][100]
    elif fault=='quality': data['samples'][120]['left']['insole']['quality']['valid']=False
    elif fault=='pressure': data['samples'][120]['right']['insole']['plantar_normal_force_n'] *=2
    elif fault=='nan': data['samples'][120]['right']['knee']['flexion_rad']=float('nan')
    else: data['samples'][120]['left']['insole']['timestamp_s']=9
    events=extract_events(data)
    assert events['status']=='unavailable' and events['reasons'] and events['landings']==[]
    assert event_metrics(data,events)['status']=='unavailable'


def test_boundary_contacts_excluded_and_protocol_configurable():
    data=processed()
    window=data['samples'][120:140]
    assert contact_indices(window,'right')==[]
    with pytest.raises(ValueError): EventProtocol(contact_threshold_n=-1)
    assert len(extract_events(data,EventProtocol(contact_threshold_n=1))['landings'])==3
