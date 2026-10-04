"""Legacy contract coverage backed by canonical implementations."""
import copy
import json
from unittest.mock import patch

import pytest
from test_baseline_simulation import ROOT, fixture
import aligned_kinematics
import analyze_knee_kinematics
import analyze_session
import bilateral_comparison
import event_biomechanics
import process_sensor_session
from generate_raw_sensor_fixture import generate_fixture
from synthetic_movement import ideal_calibration_records
from sensor_to_segment_calibration import calibrate_pair


def test_legacy_helpers_are_canonical_aliases():
    assert analyze_session.summarize_side is event_biomechanics.summarize_side
    assert analyze_knee_kinematics.summarize_knee is event_biomechanics.summarize_knee
    assert analyze_knee_kinematics.asymmetry_percent is bilateral_comparison.asymmetry_percent
    assert process_sensor_session.finite_difference is aligned_kinematics.finite_difference


def test_processor_delegates_both_sides_and_preserves_legacy_schema():
    raw = generate_fixture()
    before = copy.deepcopy(raw)
    with patch('process_sensor_session.reconstruct', wraps=aligned_kinematics.reconstruct) as fusion:
        result = process_sensor_session.process_session(raw)
    assert [call.args[2] for call in fusion.call_args_list]==['left','right']
    assert raw==before
    assert result['annotations']==raw['annotations']
    for row,source in zip(result['samples'],raw['samples']):
        for side in ('left','right'):
            assert set(row[side]['orientation'])=={'thigh_wxyz','shank_wxyz','relative_wxyz'}
            assert row[side]['insole']==source[side]['insole']
    assert json.loads(json.dumps(result))['session_id']==raw['session_id']


def test_explicit_calibration_uses_canonical_calibration_even_without_ideal_marker():
    raw = generate_fixture()
    raw['processing']['sensor_to_segment_alignment']='requires_measured_calibration'
    records = {s:ideal_calibration_records() for s in ('left','right')}
    result = process_sensor_session.process_session(raw,records)
    for side in ('left','right'):
        expected = aligned_kinematics.reconstruct(raw,calibrate_pair(records[side]),side)
        assert [r[side]['knee'] for r in result['samples']]==[r[side]['knee'] for r in expected['samples']]
    assert 'calibration_transform_wxyz' not in result['processing']
    assert result['processing']['sensor_to_segment_calibration']=='independent measured static/functional PCA'


def test_identity_adapter_cannot_claim_hardware_calibration():
    raw = generate_fixture()
    raw['synthetic']=False
    with pytest.raises(ValueError,match='measured calibration required'):
        process_sensor_session.process_session(raw)


def test_legacy_processor_obeys_canonical_clock_policy_without_resampling():
    raw = generate_fixture()
    raw['samples'][100]['timestamp_s'] += .00001  # Previously within the old 1% rule.
    before = copy.deepcopy(raw)
    with pytest.raises(ValueError,match='sample_discontinuity'):
        process_sensor_session.process_session(raw)
    assert raw==before


def test_report_preserves_annotated_impulse_while_canonical_contacts_keep_own_scope():
    data = fixture()
    legacy = analyze_session.analyze_session(data)
    event = legacy['events'][0]
    annotation = data['annotations'][0]
    assert (event['start_s'],event['end_s'])==(annotation['start_s'],annotation['end_s'])
    rows = [r for r in data['samples'] if annotation['start_s'] <= r['timestamp_s'] <= annotation['end_s']]
    expected = event_biomechanics.summarize_side(rows,'left',75*9.80665,[],data['insole_geometry']['left'])
    assert event['left']==expected
    assert legacy['analysis_version']=='0.2.0'
    assert legacy['definitions']['impulse']=='trapezoidal integration over the full annotated window, N*s'


def test_legacy_signed_fields_project_authoritative_bilateral_utility():
    event = analyze_session.analyze_session(fixture('right_load_bias'))['events'][0]
    left,right = (event[s]['loading']['peak_plantar_normal_force_n'] for s in ('left','right'))
    canonical = bilateral_comparison.comparison(left,right)
    assert event['bilateral']['loading']['peak_force_asymmetry_percent']==canonical['asymmetry_percent']
    assert event['bilateral']['signed_asymmetry_percent']['peak_force_asymmetry_percent']==canonical['signed_asymmetry_percent']
    assert bilateral_comparison.asymmetry_percent(0,0) is None
