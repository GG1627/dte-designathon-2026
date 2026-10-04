"""Adapter contracts only; constructed CSV cases are NOT hardware validation."""
import copy
import csv
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from hardware_session_adapter import (REQUIRED_FIELDS, read_csv, timing_quality, adapt_session,
                                     attach_demo_insoles, run_existing_pipeline)


def fixture_rows():
    rows = []
    for i in range(700):
        phase = 1 if i < 200 else 2 if i < 400 else 3
        t = (i - 400) / 100
        angle = .25 * (1 - math.cos(2 * math.pi * t)) if phase == 3 else 0
        velocity = .25 * 2 * math.pi * math.sin(2 * math.pi * t) if phase == 3 else .1 + (i - 200) / 200 if phase == 2 else 0
        row = dict.fromkeys(REQUIRED_FIELDS, 0)
        row.update(sequence=1000 + i, timestamp_us_actual=12000000 + i * 10000,
                   phase=phase, ble_connected=int(i < 500))
        for segment in ('thigh', 'shank'):
            row.update({f'{segment}_valid': 1, f'{segment}_i2c_ok': 1,
                        f'{segment}_az_m_s2': 9.80665,
                        f'{segment}_gy_rad_s': velocity if phase == 2 or segment == 'shank' else 0})
        if phase == 3:
            row['shank_ax_m_s2'] = -9.80665 * math.sin(angle)
            row['shank_az_m_s2'] = 9.80665 * math.cos(angle)
        rows.append(row)
    return rows


def write_csv(tmp_path, rows):
    path = tmp_path / 'session_0001.csv'
    with path.open('w') as stream:
        stream.write('# test-generated measurements; not physical hardware validation\n')
        writer = csv.DictWriter(stream, fieldnames=[*REQUIRED_FIELDS, 'knee_angle_deg_debug'])
        writer.writeheader()
        writer.writerows({**row, 'knee_angle_deg_debug': '99999'} for row in rows)
    return path


def test_parse_schema_si_units_phases_and_hardware_sources(tmp_path):
    path = write_csv(tmp_path, fixture_rows())
    frames, metadata = read_csv(path, 'left')
    raw = adapt_session(path, 'left', 'test_participant')
    assert metadata and len(frames) == 700
    assert raw['hardware_acquisition']['status'] == 'ready_for_kintra'
    assert len(raw['samples']) == 300 and raw['samples'][0]['sequence'] == 1400
    assert raw['samples'][0]['timestamp_s'] == 0.0
    assert raw['samples'][0]['timestamp_us_actual'] == 16000000
    assert set(raw['samples'][0]) == {'timestamp_s', 'timestamp_us_actual', 'sequence', 'left'}
    packet = raw['samples'][0]['left']['imu']['thigh']
    assert packet['accel_m_s2'] == {'x': 0, 'y': 0, 'z': 9.80665}
    assert packet['source'] == 'hardware' and packet['quality']['valid']
    assert 'right' not in raw['sources'] and not raw['synthetic']
    assert len(raw['calibration_records']['thigh']['static_accel']) == 200
    assert raw['calibration_records']['shank']['positive_flexion_gyro'][0] == [0, .1, 0]
    assert 'knee' not in packet and 'knee_angle_deg_debug' not in str(raw['samples'])


@pytest.mark.parametrize('segment,flag', [('thigh', 'valid'), ('shank', 'valid'), ('thigh', 'i2c_ok'), ('shank', 'i2c_ok')])
def test_invalid_flags_preserved_and_pipeline_refused(tmp_path, segment, flag):
    rows = fixture_rows(); rows[450][f'{segment}_{flag}'] = 0
    rows[450][f'{segment}_gx_rad_s'] = ''
    raw = adapt_session(write_csv(tmp_path, rows))
    packet = raw['samples'][50]['right']['imu'][segment]
    assert not packet['quality']['valid'] and packet['gyro_rad_s']['x'] is None
    assert len(raw['samples']) == 300
    assert raw['samples'][50]['timestamp_s'] == rows[450]['timestamp_us_actual'] / 1e6
    assert raw['hardware_acquisition']['status'] == 'invalid_hardware_acquisition'
    with pytest.raises(ValueError):
        run_existing_pipeline(raw)


def test_sequence_gap_and_actual_jitter(tmp_path):
    rows = fixture_rows(); rows.pop(430); rows[440]['timestamp_us_actual'] += 100
    frames, _ = read_csv(write_csv(tmp_path, rows), 'right')
    report = timing_quality(frames)
    assert report['sequence_gap_count'] == report['missing_sequences'] == 1
    assert report['max_interval_us'] == 20000
    assert report['max_abs_jitter_us'] == 10000
    assert report['mean_abs_jitter_us'] > 0
    raw = adapt_session(write_csv(tmp_path, rows))
    assert len(raw['samples']) == 299  # Missing frame never inserted.
    assert raw['samples'][30]['sequence'] == 1431


def test_good_jitter_bridges_only_timestamps_preserving_values_and_rows(tmp_path):
    rows = fixture_rows()
    for i in range(400, 700):
        rows[i]['timestamp_us_actual'] += 100 if i % 2 else -100
    path = write_csv(tmp_path, rows)
    frames, _ = read_csv(path, 'right')
    originals = [f for f in frames if f['phase'] == 3]
    raw = adapt_session(path, participant_id='test_participant')
    quality = raw['hardware_acquisition']
    assert quality['status'] == 'ready_for_kintra'
    assert quality['canonical_input_quality']['status'] != 'invalid_input'
    assert quality['movement_timing']['mean_abs_jitter_us'] == 200
    assert quality['movement_timing']['max_abs_jitter_us'] == 200
    assert raw['sampling']['rate_hz'] == 100.0
    assert raw['sampling']['actual_duration_s'] == (rows[-1]['timestamp_us_actual'] - rows[400]['timestamp_us_actual']) / 1e6
    assert raw['sampling']['duration_s'] == 2.99
    assert len(raw['samples']) == len(originals) == 300
    for i, (adapted, frame) in enumerate(zip(raw['samples'], originals)):
        original = copy.deepcopy(frame['sample'])
        assert adapted['sequence'] == original['sequence']
        assert adapted['timestamp_us_actual'] == frame['timestamp_us']
        assert adapted['timestamp_s'] == i / 100.0
        if i:
            assert adapted['timestamp_s'] - raw['samples'][i - 1]['timestamp_s'] == pytest.approx(.01, abs=1e-15)
        for segment in ('thigh', 'shank'):
            original['right']['imu'][segment]['timestamp_s'] = i / 100.0
        original['timestamp_s'] = i / 100.0
        original['timestamp_us_actual'] = frame['timestamp_us']
        assert adapted == original  # Every measurement/quality/source value unchanged.
    assert run_existing_pipeline(raw)['pipeline']['knees']['right']['kinematics']['status'] == 'ready'


@pytest.mark.parametrize('fault', ['gap', 'max_jitter', 'mean_jitter', 'movement_gap'])
def test_failed_timing_never_constructs_uniform_timeline(tmp_path, fault):
    rows = fixture_rows()
    if fault == 'gap':
        rows.pop(430)
    elif fault == 'max_jitter':
        rows[450]['timestamp_us_actual'] += 2001
    elif fault == 'mean_jitter':
        for i in range(400, 700):
            rows[i]['timestamp_us_actual'] += 700 if i % 2 else -700
    else:
        rows[450]['phase'] = 0
    raw = adapt_session(write_csv(tmp_path, rows))
    assert raw['hardware_acquisition']['status'] == 'invalid_hardware_acquisition'
    expected = [r for r in rows if r['phase'] == 3]
    assert len(raw['samples']) == len(expected)
    for sample, original in zip(raw['samples'], expected):
        assert sample['sequence'] == original['sequence']
        assert sample['timestamp_s'] == original['timestamp_us_actual'] / 1e6
        assert sample['timestamp_us_actual'] == original['timestamp_us_actual']
        assert all(p['timestamp_s'] == sample['timestamp_s'] for p in sample['right']['imu'].values())
    assert raw['provenance']['timestamp_policy'].startswith('actual absolute')
    with pytest.raises(ValueError, match='invalid_hardware_acquisition'):
        run_existing_pipeline(raw)


@pytest.mark.parametrize('phase', [0, 1, 2])
def test_missing_phase_fails_closed(tmp_path, phase):
    rows = fixture_rows()
    for row in rows:
        if phase == 0 or row['phase'] == phase:
            row['phase'] = 0
    raw = adapt_session(write_csv(tmp_path, rows))
    assert raw['hardware_acquisition']['calibration']['status'] == 'calibration_required'
    assert raw['hardware_acquisition']['status'] != 'ready_for_kintra'
    with pytest.raises(ValueError):
        run_existing_pipeline(raw)


def test_existing_pca_rejects_unexcited_thigh(tmp_path):
    rows = fixture_rows()
    for row in rows:
        row['thigh_gy_rad_s'] = 0
    raw = adapt_session(write_csv(tmp_path, rows))
    assert raw['hardware_acquisition']['status'] == 'calibration_required'
    assert raw['samples'][0]['timestamp_s'] == 16.0
    assert any('unexcited' in reason for reason in raw['hardware_acquisition']['reasons'])


def test_existing_pipeline_reconstruction_features_and_unavailable_opposite(tmp_path):
    raw = adapt_session(write_csv(tmp_path, fixture_rows()), 'left', 'test_participant')
    original = copy.deepcopy(raw)
    result = run_existing_pipeline(raw)
    assert raw == original
    knees = result['pipeline']['knees']
    assert knees['left']['kinematics']['status'] == 'ready'
    assert knees['left']['source'] == 'hardware' and knees['right']['status'] == 'unavailable'
    assert result['knee_summary']['rom_deg'] > 20
    assert all(math.isfinite(row['left']['knee'][k]) for row in knees['left']['kinematics']['samples']
               for k in ('flexion_rad', 'angular_velocity_rad_s', 'angular_acceleration_rad_s2'))
    assert result['existing_activity_features']['profile'] == 'imu_pair_only'
    assert knees['left']['activity_svm']['status'] == 'unavailable'
    assert knees['left']['record']['context']['side'] == 'left'


def test_synthetic_insole_merge_never_fabricates_knee(tmp_path):
    raw = adapt_session(write_csv(tmp_path, fixture_rows()), 'right', 'test_participant')
    merged = attach_demo_insoles(raw, 75)
    assert 'left' not in raw['samples'][0] and 'insole' not in raw['samples'][0]['right']
    assert merged['synthetic'] is False and merged['contains_synthetic_measurements']
    assert merged['samples'][0]['right']['imu'] == raw['samples'][0]['right']['imu']
    assert 'imu' not in merged['samples'][0]['left']
    for side in ('left', 'right'):
        assert merged['samples'][0][side]['insole']['source'] == 'synthetic_demo'
        assert merged['samples'][0][side]['insole']['timestamp_s'] == raw['samples'][0]['timestamp_s']
    result = run_existing_pipeline(merged)
    assert result['pipeline']['knees']['right']['source'] == 'hardware'
    assert result['pipeline']['insoles']['left']['source'] == 'synthetic_demo'


def test_short_calibration_and_missing_identity_are_not_substituted(tmp_path):
    rows = fixture_rows(); rows[199]['phase'] = 0
    raw = adapt_session(write_csv(tmp_path, rows))
    assert raw['hardware_acquisition']['status'] == 'calibration_required'
    assert any('static_missing_or_short' in r for r in raw['hardware_acquisition']['reasons'])
    raw = adapt_session(write_csv(tmp_path, fixture_rows()))
    with pytest.raises(ValueError, match='participant_identity_required'):
        run_existing_pipeline(raw)
