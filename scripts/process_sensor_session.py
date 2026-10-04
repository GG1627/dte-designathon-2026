"""Legacy schema/CLI adapter over canonical validation, calibration and kinematics.

Implicit identity calibration is restricted to explicitly ideal synthetic fixtures.
Other mounting requires per-side static/functional calibration records. Runtime
orientation and derivatives are owned exclusively by aligned_kinematics.
"""
import argparse
import copy
import json
from pathlib import Path

from aligned_kinematics import reconstruct, finite_difference, INITIAL_TILT_ITERATIONS
from signal_preprocessing import validate_signals
from sensor_to_segment_calibration import calibrate_pair
from synthetic_sensor_validation import validate_processed

ROOT = Path(__file__).resolve().parents[1]
BETA = 0.1


def process_session(raw, calibration_records=None):
    """Preserve the old bilateral schema; delegate measurements to canonical code."""
    if calibration_records is None:
        if raw.get('synthetic') is not True or raw.get('processing',{}).get('sensor_to_segment_alignment') != 'ideal':
            raise ValueError('Explicit measured calibration required; identity is only for ideal synthetic fixtures')
        calibrations = {side: {segment: {'R_sensor_to_segment': [[1,0,0],[0,1,0],[0,0,1]]}
                              for segment in ('thigh','shank')} for side in ('left','right')}
    else:
        calibrations = {side: calibrate_pair(calibration_records[side]) for side in ('left','right')}
    sides = {}
    for side in ('left','right'):
        quality = validate_signals(raw, side, 'imu_pair_only')
        if quality['status'] != 'ready':
            raise ValueError('Invalid '+side+' IMU input: '+', '.join(quality['reasons']))
        sides[side] = reconstruct(raw, calibrations[side], side, BETA)
    processed = {key: copy.deepcopy(raw[key]) for key in (
        'schema_version','session_id','activity','synthetic','participant',
        'sampling','sources','insole_geometry','annotations')}
    for key in ('scenario','phases','baseline_demo'):
        if key in raw:
            processed[key] = copy.deepcopy(raw[key])
    processed["processing"] = {
        "stage": "post_sensor_processing", "orientation_filter": "Madgwick 6-DOF",
        "sensor_to_segment_calibration": "synthetic ideal alignment",
        "calibration_transform_wxyz": [1.0, 0.0, 0.0, 0.0],
        "hardware_calibration_requirement": "real hardware requires sensor-to-segment calibration",
        "knee_angle_source": "relative thigh/shank Madgwick orientation; signed Y pitch",
        "knee_angular_velocity_source": "relative thigh/shank gyroscope Y-axis; ideal aligned sagittal model",
        "knee_angular_acceleration_source": "finite difference of gyro-derived knee angular velocity",
        "velocity_frame_requirement": "real 3D hardware requires calibrated common/anatomical frame transformation",
        "relative_orientation": "conjugate(thigh sensor-to-world) * shank sensor-to-world",
        "knee_derivatives": "velocity from calibrated gyro Y difference; acceleration from central interiors, one-sided boundaries",
        "derivative_filter": "none",
        "timestamp_processing": "canonical strict timestamps/sequences; interval tolerance 1e-8 s; no interpolation",
        "filter_beta": BETA,
        "orientation_initialization": "200 zero-gyro gradient iterations using first accelerometer sample; assumes stationary initial pose and common zero yaw",
        "initialization_iterations": INITIAL_TILT_ITERATIONS,
        "insole_processing": "device/API measurements passed through unchanged",
    }
    if calibration_records is not None:
        processed['processing']['sensor_to_segment_calibration'] = 'independent measured static/functional PCA'
        processed['processing'].pop('calibration_transform_wxyz')
        processed['processing']['calibrations'] = calibrations
        processed['processing']['knee_angle_source'] = 'relative calibrated thigh/shank orientation; signed Y pitch'
        processed['processing']['knee_angular_velocity_source'] = 'aligned shank gyro Y minus thigh gyro Y; sagittal model'
        processed['processing']['relative_orientation'] = 'conjugate(thigh segment-to-world) * shank segment-to-world'
    times = [row['timestamp_s'] for row in raw['samples']]
    intervals = [b-a for a,b in zip(times,times[1:])]
    processed['synchronization'] = {
        'validation':'PASS','expected_interval_s':1/raw['sampling']['rate_hz'],
        'observed_min_interval_s':min(intervals),'observed_max_interval_s':max(intervals),
        'resampling':'none','sequence_gaps':0,'clock':raw['sampling']['clock'],
        'synchronization_uncertainty_s':raw['sampling'].get('synchronization_uncertainty_s'),
        'synchronization_basis':'input clock metadata; sample timing checked, cross-device offset not independently measured',
    }
    processed['samples'] = []
    for i,row in enumerate(raw['samples']):
        output = {key:row[key] for key in ('sequence','timestamp_s')}
        for side in ('left','right'):
            canonical = sides[side]['samples'][i][side]
            output[side] = {
                'orientation':{name+'_wxyz':tuple(q) for name,q in canonical['orientation'].items()},
                'knee':copy.deepcopy(canonical['knee']),
                'insole':copy.deepcopy(row[side]['insole']),
            }
        processed['samples'].append(output)
    return processed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_path", type=Path)
    parser.add_argument("--output", type=Path, help="Optional processed JSON destination")
    args = parser.parse_args()
    raw = json.loads(args.session_path.read_text())
    processed = process_session(raw)
    validate_processed(raw, processed)
    stem = args.session_path.stem
    stem = stem[:-4] if stem.endswith("_raw") else stem
    output = args.output or ROOT / "data" / "processed" / f"{stem}_processed.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(processed, indent=2, allow_nan=False) + "\n")
    assert json.loads(output.read_text()) == json.loads(json.dumps(processed))
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
