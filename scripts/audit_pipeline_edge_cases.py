"""Reproduce pipeline review findings with constructed inputs, not hardware data.

Run: python -B scripts/audit_pipeline_edge_cases.py
This observes current behavior without changing production code or references.
"""
import copy
import csv
import hashlib
import json
import math
from pathlib import Path

from aligned_kinematics import finite_difference, orientations
from contextual_reference import context_key, fit_personal_reference, scalar_session
from hardware_session_adapter import REQUIRED_FIELDS, adapt_session
from kintra_pipeline import run_pipeline
from madgwick import relative_flexion_y_rad
from synthetic_bilateral import bilateral_fixture, fixture_config


def main():
    findings = {}
    raw = bilateral_fixture()
    angle = math.radians(60)
    for row in raw['samples']:
        packet = row['right']['imu']['shank']
        packet['gyro_rad_s'] = dict.fromkeys('xyz', 0.)
        packet['accel_m_s2'] = {'x': -9.80665 * math.sin(angle), 'y': 0.,
                               'z': 9.80665 * math.cos(angle)}
    reconstructed = orientations(raw)
    findings['stationary_initialization'] = {
        'true_angle_deg': 60.,
        'first_estimate_deg': math.degrees(reconstructed[0]['knee']['flexion_rad']),
        'estimate_at_one_second_deg': math.degrees(reconstructed[100]['knee']['flexion_rad']),
        'last_estimate_deg': math.degrees(reconstructed[-1]['knee']['flexion_rad']),
    }

    findings['full_flexion_range'] = []
    for degrees in (60, 90, 100, 120):
        half = math.radians(degrees) / 2
        observed = math.degrees(relative_flexion_y_rad((math.cos(half), 0, math.sin(half), 0)))
        findings['full_flexion_range'].append({'true_angle_deg': degrees, 'reported_deg': observed})

    raw = bilateral_fixture()
    feet = [copy.deepcopy(row['left']['insole']) for row in raw['samples']]
    for index, row in enumerate(raw['samples']):
        row['left']['insole'] = copy.deepcopy(feet[max(0, index - 8)])
    result = run_pipeline(raw, fixture_config(raw))
    record = result['knees']['right']['record']
    cropped = record['biomechanics']['events'][0]['loading']['left']
    accepted = [row for row in scalar_session(record)['event_metrics']
                if row['side'] == 'left' and 'impulse' in row['metric']]
    findings['asynchronous_foot_contacts'] = {
        'contact_offset_s': .08,
        'own_left_contact_impulse_n_s': result['insoles']['left']['events'][0]['loading']['impulse_n_s'],
        'left_impulse_in_right_knee_record_n_s': cropped['impulse_n_s'],
        'cropped_loading_quality': cropped['quality'],
        'scalar_impulse_statuses': [row['status'] for row in accepted],
        'bilateral_plantar_status': result['bilateral']['plantar_loading']['status'],
    }

    reference_raw = bilateral_fixture()
    reference_record = run_pipeline(reference_raw, fixture_config(reference_raw))['knees']['right']['record']
    history = []
    for index in range(5):
        session = copy.deepcopy(reference_record)
        session['session_id'] = f'audit_history_{index}'
        sensors = copy.deepcopy(session['sensor_configuration'])
        sensors['acquisition_context'] = {
            'source': 'hardware', 'hardware_validated': False, 'instrumented_side': 'right',
            'source_sha256': hashlib.sha256(str(index).encode()).hexdigest(),
        }
        session['context'] = context_key(session, sensors, session['processing_configuration'])
        history.append(session)
    separate = fit_personal_reference(history)
    for session in history:
        session['context'] = copy.deepcopy(history[0]['context'])
    common = fit_personal_reference(history)
    findings['per_recording_hash_in_reference_context'] = {
        'session_count': 5,
        'distributions_with_file_hashes': len(separate['metrics']),
        'eligible_counts_with_file_hashes': sorted({m['eligible_session_count'] for m in separate['metrics']}),
        'distributions_with_common_context': len(common['metrics']),
        'eligible_counts_with_common_context': sorted({m['eligible_session_count'] for m in common['metrics']}),
    }

    folder = Path(__file__).resolve().parents[1] / 'data' / 'baseline_demo' / 'pipeline_review'
    folder.mkdir(parents=True, exist_ok=True)
    csv_path = folder / 'constructed_timing_probe.csv'
    rows = []
    for index in range(700):
        phase = 1 if index < 200 else 2 if index < 400 else 3
        elapsed = max(0, index - 400) * .0105
        angle = .05 * elapsed ** 2
        row = dict.fromkeys(REQUIRED_FIELDS, 0)
        row.update(sequence=index, timestamp_us_actual=index * 10500, phase=phase)
        for segment in ('thigh', 'shank'):
            row.update({f'{segment}_valid': 1, f'{segment}_i2c_ok': 1,
                        f'{segment}_az_m_s2': 9.80665})
            row[f'{segment}_gy_rad_s'] = (.1 + (index - 200) / 200 if phase == 2
                                          else .1 * elapsed if phase == 3 and segment == 'shank' else 0.)
        if phase == 3:
            row['shank_ax_m_s2'] = -9.80665 * math.sin(angle)
            row['shank_az_m_s2'] = 9.80665 * math.cos(angle)
        rows.append(row)
    try:
        with csv_path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=REQUIRED_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        adapted = adapt_session(csv_path, 'right', 'audit_participant')
        samples = adapted['samples']
        acceleration = finite_difference(
            [row['right']['imu']['shank']['gyro_rad_s']['y'] for row in samples],
            [row['timestamp_s'] for row in samples])
        findings['nominal_hardware_timeline'] = {
            'adapter_status': adapted['hardware_acquisition']['status'],
            'actual_rate_hz': adapted['hardware_acquisition']['movement_timing']['effective_rate_hz'],
            'actual_duration_s': adapted['sampling']['actual_duration_s'],
            'analysis_duration_s': adapted['sampling']['duration_s'],
            'true_acceleration_rad_s2': .1,
            'nominal_time_acceleration_rad_s2': acceleration[100],
        }
    finally:
        csv_path.unlink(missing_ok=True)
    output = folder / 'findings.json'
    output.write_text(json.dumps(findings, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps(findings, indent=2, allow_nan=False))
    print(f'\nSaved {output}')


if __name__ == '__main__':
    main()
