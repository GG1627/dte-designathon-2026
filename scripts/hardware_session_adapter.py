"""Fail-closed ESP32 CSV bridge; actual timestamps and existing algorithms only."""
import argparse
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median

SEGMENTS = ('thigh', 'shank')
AXES = ('x', 'y', 'z')
PHASES = {0: 'IDLE', 1: 'STATIC', 2: 'FLEXION', 3: 'MOVEMENT'}
SENSOR_IDS = {s: f'kintra_demo_{s}_imu' for s in SEGMENTS}
CHANNELS = {'accel_m_s2': 'a', 'gyro_rad_s': 'g'}
REQUIRED_FIELDS = ('sequence', 'timestamp_us_actual', 'phase', 'ble_connected',
                   *(f'{s}_{kind}{axis}_{unit}' for s in SEGMENTS
                     for kind, unit in (('a', 'm_s2'), ('g', 'rad_s')) for axis in AXES),
                   *(f'{s}_{flag}' for s in SEGMENTS for flag in ('valid', 'i2c_ok')))
# Prototype acquisition gates, NOT clinical/reliability thresholds.
TIMING_RULES = {'nominal_rate_hz': 100, 'expected_interval_us': 10000,
                'effective_rate_min_hz': 95, 'effective_rate_max_hz': 105,
                'max_mean_abs_jitter_us': 500, 'max_abs_jitter_us': 2000,
                'sequence_gaps_allowed': 0, 'interpolation': 'none',
                'provenance': 'prototype_engineering_acquisition_criteria'}
CALIBRATION_RULES = {'minimum_samples_per_phase': 200, 'minimum_duration_s': 1.99,
                     'provenance': 'prototype_two_second_collection_minimum_not_scientific_sufficiency'}


def read_csv(path, side):
    if side not in ('left', 'right'):
        raise ValueError('Instrumented side must be left or right')
    metadata, lines = [], []
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        if line.lstrip().startswith('#'):
            metadata.append(line.lstrip()[1:].strip())
        elif line.strip():
            lines.append(line)
    reader = csv.DictReader(lines)
    if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError('Missing or duplicate CSV header')
    missing = set(REQUIRED_FIELDS) - set(reader.fieldnames)
    if missing:
        raise ValueError('Missing CSV fields: ' + ', '.join(sorted(missing)))
    frames = []
    for number, row in enumerate(reader, 2):
        if None in row or any(row[k] is None for k in REQUIRED_FIELDS):
            raise ValueError(f'CSV record {number}: truncated/extra fields')
        try:
            sequence, timestamp, phase = (int(row[k]) for k in ('sequence', 'timestamp_us_actual', 'phase'))
            if sequence < 0 or timestamp < 0 or phase not in PHASES:
                raise ValueError('Invalid sequence, timestamp or phase')
            flags = {k: int(row[k]) for k in REQUIRED_FIELDS if k.endswith(('_valid', '_i2c_ok')) or k == 'ble_connected'}
            if any(v not in (0, 1) for v in flags.values()):
                raise ValueError('Flags must be 0 or 1')
            sample = {'timestamp_s': timestamp / 1e6, 'sequence': sequence, side: {'imu': {}}}
            for segment in SEGMENTS:
                reasons, packet = [], {'timestamp_s': timestamp / 1e6, 'source': 'hardware',
                                       'sensor_id': SENSOR_IDS[segment], 'synthetic': False}
                if not flags[f'{segment}_valid']:
                    reasons.append('sensor_valid_flag_false')
                if not flags[f'{segment}_i2c_ok']:
                    reasons.append('i2c_status_bad')
                for channel, prefix in CHANNELS.items():
                    unit = 'm_s2' if prefix == 'a' else 'rad_s'
                    packet[channel] = {}
                    for axis in AXES:
                        text = row[f'{segment}_{prefix}{axis}_{unit}'].strip()
                        value = float(text) if text else None
                        if value is None or not math.isfinite(value):
                            reasons.append(f'missing_or_nonfinite_{channel}_{axis}')
                            value = None
                        packet[channel][axis] = value
                packet['quality'] = {'valid': not reasons, 'reasons': reasons}
                sample[side]['imu'][segment] = packet
            frames.append({'timestamp_us': timestamp, 'phase': phase,
                           'ble_connected': bool(flags['ble_connected']), 'sample': sample})
        except (ValueError, TypeError) as error:
            raise ValueError(f'CSV record {number}: {error}') from error
    return frames, metadata


def timing_quality(frames):
    intervals = [b['timestamp_us'] - a['timestamp_us'] for a, b in zip(frames, frames[1:])]
    steps = [b['sample']['sequence'] - a['sample']['sequence'] for a, b in zip(frames, frames[1:])]
    duration = (frames[-1]['timestamp_us'] - frames[0]['timestamp_us']) / 1e6 if frames else 0
    rate = (len(frames) - 1) / duration if len(frames) > 1 and duration > 0 else None
    jitter = [abs(dt - TIMING_RULES['expected_interval_us']) for dt in intervals]
    report = {'sample_count': len(frames), 'duration_s': duration, 'effective_rate_hz': rate,
              'sequence_gap_count': sum(step > 1 for step in steps),
              'missing_sequences': sum(max(0, step - 1) for step in steps),
              'sequence_duplicate_or_reversal_count': sum(step <= 0 for step in steps),
              'nonmonotonic_timestamp_count': sum(dt <= 0 for dt in intervals),
              'mean_interval_us': mean(intervals) if intervals else None,
              'median_interval_us': median(intervals) if intervals else None,
              'max_interval_us': max(intervals) if intervals else None,
              'min_interval_us': min(intervals) if intervals else None,
              'mean_abs_jitter_us': mean(jitter) if jitter else None,
              'max_abs_jitter_us': max(jitter) if jitter else None}
    reasons = []
    if rate is None or not 95 <= rate <= 105:
        reasons.append('effective_rate_outside_prototype_95_to_105_hz')
    for key in ('sequence_gap_count', 'sequence_duplicate_or_reversal_count', 'nonmonotonic_timestamp_count'):
        if report[key]:
            reasons.append(key)
    if jitter and mean(jitter) > 500:
        reasons.append('mean_abs_jitter_exceeds_prototype_500_us')
    if jitter and max(jitter) > 2000:
        reasons.append('max_abs_jitter_exceeds_prototype_2000_us')
    return {**report, 'status': 'ready' if not reasons else 'invalid_hardware_acquisition',
            'reasons': reasons, 'criteria': copy.deepcopy(TIMING_RULES)}


def adapt_session(path, side='right', participant_id=None):
    frames, metadata = read_csv(path, side)
    timing = timing_quality(frames)
    groups = {phase: [f for f in frames if f['phase'] == phase] for phase in PHASES}
    phases = {PHASES[p]: {'sample_count': len(rows), 'duration_s': timing_quality(rows)['duration_s'],
                          'start_s': rows[0]['sample']['timestamp_s'] if rows else None,
                          'end_s': rows[-1]['sample']['timestamp_s'] if rows else None}
              for p, rows in groups.items()}
    records = {s: {'static_accel': [], 'positive_flexion_gyro': []} for s in SEGMENTS}
    for phase, channel, key in ((1, 'accel_m_s2', 'static_accel'), (2, 'gyro_rad_s', 'positive_flexion_gyro')):
        for frame in groups[phase]:
            for segment in SEGMENTS:
                values = frame['sample'][side]['imu'][segment][channel]
                records[segment][key].append([values[a] for a in AXES])
    reasons = list(timing['reasons'])
    invalid = {s: [f['sample']['sequence'] for f in frames if not f['sample'][side]['imu'][s]['quality']['valid']]
               for s in SEGMENTS}
    for segment, sequences in invalid.items():
        if sequences:
            reasons.append(f'{segment}_invalid_samples:{len(sequences)}')
    calibration_reasons = []
    for phase in (1, 2):
        stats = phases[PHASES[phase]]
        if stats['sample_count'] < 200 or stats['duration_s'] < 1.99:
            calibration_reasons.append(f'{PHASES[phase].lower()}_missing_or_short_requires_200_samples_and_1.99_s')
        if groups[phase] and any(not f['sample'][side]['imu'][s]['quality']['valid'] for f in groups[phase] for s in SEGMENTS):
            calibration_reasons.append(f'{PHASES[phase].lower()}_contains_invalid_imu')
    movement = groups[3]
    if len(movement) < 3:
        reasons.append('movement_phase_missing_or_short')
    movement_timing = timing_quality(movement)
    reasons.extend('movement:' + r for r in movement_timing['reasons'])
    rate = movement_timing['effective_rate_hz'] or 100.0
    for frame in movement:
        frame['sample']['timestamp_us_actual'] = frame['timestamp_us']
    raw = {'schema_version': '0.1.0', 'session_id': Path(path).stem, 'synthetic': False,
           'activity': None, 'participant': {'id': participant_id, 'mass_kg': None},
           'sampling': {'rate_hz': rate, 'nominal_rate_hz': 100.0,
                        'duration_s': movement_timing['duration_s'],
                        'actual_duration_s': movement_timing['duration_s'], 'clock': 'esp_timer_get_time',
                        'synchronization_uncertainty_s': None,
                        'synchronization_basis': 'frame-start timestamp; sequential sensor reads; offset unmeasured'},
           'sources': {side: {'knee': list(SENSOR_IDS.values())}},
           'annotations': [], 'samples': [f['sample'] for f in movement],
           'calibration_records': records,
           'provenance': {'source': 'hardware', 'hardware_validated': False,
                          'source_csv': str(Path(path).resolve()), 'source_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                          'metadata_comments': metadata, 'instrumented_knee_side': side,
                          'opposite_knee': 'unavailable', 'debug_angle_columns_used': False,
                          'timestamp_policy': 'actual absolute hardware microseconds / 1e6; no resampling'}}
    canonical = {'status': 'unavailable', 'reasons': ['hardware_or_calibration_gates_not_passed']}
    calibrations = None
    # No numerical algorithm import needed for incomplete/faulty recordings.
    if not timing['reasons'] and not calibration_reasons and not invalid['thigh'] and not invalid['shank']:
        from sensor_to_segment_calibration import calibrate_pair
        try:
            calibrations = calibrate_pair(records)
        except (ValueError, TypeError) as error:
            calibration_reasons.append(str(error))
    if (not timing['reasons'] and not movement_timing['reasons']
            and not any(invalid.values()) and calibrations and len(movement) >= 3):
        # Uniform analysis coordinate only; retain measured timestamps and signals.
        nominal_rate = raw['sampling']['nominal_rate_hz']
        first_sequence = movement[0]['sample']['sequence']
        for row in raw['samples']:
            row['timestamp_s'] = (row['sequence'] - first_sequence) / nominal_rate
            for packet in row[side]['imu'].values():
                packet['timestamp_s'] = row['timestamp_s']
        raw['sampling'].update(rate_hz=nominal_rate,
                               duration_s=raw['samples'][-1]['timestamp_s'],
                               clock='sequence_nominal_analysis_coordinate')
        raw['provenance'].update(
            timestamp_policy='(sequence - first_movement_sequence) / nominal_rate_hz; no signal resampling',
            actual_timestamp_clock='esp_timer_get_time', first_movement_sequence=first_sequence)
        from signal_preprocessing import validate_signals
        canonical = validate_signals(raw, side, 'imu_pair_only')
        reasons.extend('canonical:' + r for r in canonical['reasons'])
    status = ('invalid_hardware_acquisition' if timing['reasons'] or movement_timing['reasons'] or any(invalid.values()) or canonical['status'] == 'invalid_input'
              else 'calibration_required' if calibration_reasons
              else 'invalid_hardware_acquisition' if len(movement) < 3 else 'ready_for_kintra')
    report = {'status': status, 'reasons': sorted(set(reasons + calibration_reasons)),
              'timing': timing, 'movement_timing': movement_timing, 'phases': phases,
              'signal_quality': {s: {'valid_percent': 100 * (1 - len(invalid[s]) / len(frames)) if frames else None,
                                    'invalid_sequences': invalid[s]} for s in SEGMENTS},
              'calibration': {'status': 'calibration_required' if calibration_reasons else 'ready' if calibrations else 'unavailable',
                              'reasons': calibration_reasons, 'criteria': copy.deepcopy(CALIBRATION_RULES)},
              'canonical_input_quality': canonical, 'no_interpolation': True}
    raw['hardware_acquisition'] = report
    if calibrations:
        raw['calibration_result'] = calibrations
    return raw


def attach_demo_insoles(raw, mass_kg):
    """Explicit optional helper: existing synthetic insole generator, never knee motion."""
    if not isinstance(mass_kg, (int, float)) or not math.isfinite(mass_kg) or mass_kg <= 0:
        raise ValueError('Explicit measured body mass required for insole normalization')
    from generate_mock_data import geometry, insole
    result = copy.deepcopy(raw)
    result['participant']['mass_kg'] = mass_kg
    result['contains_synthetic_measurements'] = True
    result['insole_geometry'] = {s: geometry(s) for s in ('left', 'right')}
    start = result['samples'][0]['timestamp_s'] if result['samples'] else 0
    for side in ('left', 'right'):
        result['sources'].setdefault(side, {})['insole'] = f'synthetic_demo_{side}_insole'
        for row in result['samples']:
            packet = insole(row['timestamp_s'] - start, side, result['insole_geometry'][side], 1, False)
            packet.update(timestamp_s=row['timestamp_s'], source='synthetic_demo', synthetic=True)
            row.setdefault(side, {})['insole'] = packet
    result['provenance']['insole_source'] = 'synthetic_demo'
    return result


def run_existing_pipeline(raw):
    quality = raw['hardware_acquisition']
    if quality['status'] != 'ready_for_kintra':
        raise ValueError(quality['status'] + ': ' + '; '.join(quality['reasons']))
    if not raw['participant']['id']:
        raise ValueError('participant_identity_required: supply --participant-id')
    from kintra_pipeline import PipelineConfig, run_pipeline
    from signal_preprocessing import FilterConfig
    from sensor_configuration import Sensor, KneeSensors, SensorConfiguration
    from activity_svm import extract_features
    from event_biomechanics import summarize_knee
    side = raw['provenance']['instrumented_knee_side']
    demo = raw.get('contains_synthetic_measurements') is True
    knees = {s: KneeSensors() for s in ('left', 'right')}
    knees[side] = KneeSensors(*(Sensor(True, 'hardware', SENSOR_IDS[s]) for s in SEGMENTS))
    feet = {s: Sensor(True, 'synthetic_demo', raw['sources'][s]['insole']) if demo else Sensor()
            for s in ('left', 'right')}
    sensors = SensorConfiguration('single_knee_plus_mock_insoles' if demo else 'bilateral_knees_plus_insoles', knees, feet)
    config = PipelineConfig(side=side, profile='imu_pair_plus_insole' if demo else 'imu_pair_only',
                            calibration_records=raw['calibration_records'], sensor_configuration=sensors,
                            filter=FilterConfig(provenance='hardware_adapter_no_filter_no_interpolation'),
                            acquisition_context={'source': 'hardware', 'hardware_validated': False,
                                                 'instrumented_side': side, 'source_sha256': raw['provenance']['source_sha256']})
    pipeline = run_pipeline(raw, config)
    knee = pipeline['knees'][side]
    if knee['kinematics']['status'] != 'ready':
        raise ValueError('Existing pipeline rejected hardware: ' + '; '.join(knee['reasons']))
    processed = {**raw, 'monitored_knee_side': side, 'samples': knee['kinematics']['samples']}
    # Reuse existing reconstructed signals; do not change model-dependent pipeline stages.
    features = extract_features(processed, profile=config.profile)
    return {'pipeline': pipeline, 'knee_summary': summarize_knee(processed['samples'], side),
            'existing_activity_features': features,
            'limitations': ['No trained movement/temporal models or personal reference supplied; those stages remain unavailable.']}


def print_report(raw):
    q = raw['hardware_acquisition'];t = q['timing']
    number = lambda x: 'unavailable' if x is None else f'{x:.3f}'
    print('KINTRA HARDWARE SESSION\n')
    for label, value in [('Rows', t['sample_count']), ('Duration (s)', number(t['duration_s'])),
                         ('Nominal rate (Hz)', 100), ('Effective rate (Hz)', number(t['effective_rate_hz'])),
                         ('Sequence gaps', t['sequence_gap_count']), ('Missing sequences', t['missing_sequences'])]:
        print(f'{label:25} {value}')
    for side in SEGMENTS:
        print(f'{side.title() + " valid (%)":25} {number(q["signal_quality"][side]["valid_percent"])}')
    for name, p in q['phases'].items():
        print(f'{name:25} {p["sample_count"]} samples; {p["duration_s"]:.3f} s')
    print('\nTiming (actual hardware intervals):')
    for key in ('mean_interval_us', 'median_interval_us', 'min_interval_us', 'max_interval_us', 'mean_abs_jitter_us', 'max_abs_jitter_us'):
        print(f'  {key:25} {number(t[key])}')
    print('\nSTATUS: ' + q['status'].upper())
    for reason in q['reasons']:
        print('  - ' + reason)
    print('No interpolation. Prototype engineering gates; no clinical/hardware accuracy claim.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_path', type=Path)
    parser.add_argument('--side', choices=('left', 'right'), default='right', help='Instrumented knee; default right')
    parser.add_argument('--participant-id', help='Actual athlete identity; required to run pipeline')
    parser.add_argument('--inspect', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--run-pipeline', action='store_true')
    parser.add_argument('--demo-insoles', action='store_true', help='Explicitly generate synthetic bilateral insoles only')
    parser.add_argument('--mass-kg', type=float)
    args = parser.parse_args()
    if args.run_pipeline and not args.participant_id:
        parser.error('--participant-id is required for --run-pipeline')
    try:
        raw = adapt_session(args.csv_path, args.side, args.participant_id)
        if args.demo_insoles:
            raw = attach_demo_insoles(raw, args.mass_kg)
        print_report(raw)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(raw, indent=2, allow_nan=False) + '\n')
            print('Saved canonical session: ' + str(args.output))
        if args.run_pipeline:
            result = run_existing_pipeline(raw)
            base = args.output or Path(__file__).resolve().parents[1] / 'data' / 'hardware' / (args.csv_path.stem + '.json')
            output = base.with_name(base.stem + '_pipeline.json')
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
            print('Existing knee summary: ' + json.dumps(result['knee_summary']))
            print('Saved pipeline output: ' + str(output))
        return 0 if raw['hardware_acquisition']['status'] == 'ready_for_kintra' else 2
    except (ValueError, OSError, ImportError) as error:
        print('STATUS: ' + ('DEPENDENCY_UNAVAILABLE' if isinstance(error, ImportError) else 'INVALID_HARDWARE_ACQUISITION'))
        print('  - ' + str(error))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
