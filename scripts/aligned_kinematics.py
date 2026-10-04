"""One-knee sagittal reconstruction, reusing the audited Madgwick and derivatives.

Raw sensor orientations are retained. Anatomical reconstruction uses a second
pass after rotating measured vectors by independently acquired PCA calibration.
This avoids treating unconstrained 6-DOF sensor yaw as anatomical heading.
Assumes sagittal motion, stationary initial tilt and common zero segment yaw.
"""
import copy
import math
import numpy as np

from madgwick import MadgwickIMU, quaternion_relative, relative_flexion_y_rad
from sensor_to_segment_calibration import validate_rotation

VERSION = 'calibrated-sagittal-pair/1.0.0'

INITIAL_TILT_ITERATIONS = 200


def finite_difference(values, times):
    """Secant central differences inside; first-order one-sided at boundaries.

    Interior: (v[i+1]-v[i-1])/(t[i+1]-t[i-1]). Applied once to gyro velocity.
    No smoothing or interpolation; derivative noise is not suppressed here.
    """
    return [
        (values[min(i + 1, len(values) - 1)] - values[max(i - 1, 0)])
        / (times[min(i + 1, len(times) - 1)] - times[max(i - 1, 0)])
        for i in range(len(values))
    ]

def orientations(session, side='right', matrices=None, beta=0.1):
    matrices = matrices or {segment: np.eye(3) for segment in ('thigh', 'shank')}
    filters = {segment: MadgwickIMU(beta) for segment in matrices}
    dt = 1 / session['sampling']['rate_hz']
    for segment, orientation in filters.items():
        packet = session['samples'][0][side]['imu'][segment]
        accel = matrices[segment] @ np.array([packet['accel_m_s2'][a] for a in ('x','y','z')])
        if np.linalg.norm(accel) < 1e-10:
            raise ValueError('Nonzero initial gravity/specific force required')
        for _ in range(INITIAL_TILT_ITERATIONS):
            orientation.update(0, 0, 0, *accel, dt)
    rows = []
    for i, row in enumerate(session['samples']):
        quaternions, gyros = {}, {}
        for segment, orientation in filters.items():
            packet = row[side]['imu'][segment]
            gyro = matrices[segment] @ np.array([packet['gyro_rad_s'][a] for a in ('x','y','z')])
            accel = matrices[segment] @ np.array([packet['accel_m_s2'][a] for a in ('x','y','z')])
            if i:
                orientation.update(*gyro, *accel, row['timestamp_s']-session['samples'][i-1]['timestamp_s'])
            quaternions[segment] = list(orientation.quaternion)
            gyros[segment] = gyro.tolist()
        relative = quaternion_relative(quaternions['thigh'], quaternions['shank'])
        rows.append({'timestamp_s': row['timestamp_s'], 'sequence': row['sequence'],
                     'orientation': {**quaternions, 'relative': list(relative)},
                     'segment_gyro_rad_s': gyros,
                     'knee': {'flexion_rad': relative_flexion_y_rad(relative),
                              'angular_velocity_rad_s': gyros['shank'][1]-gyros['thigh'][1],
                              'quality': {'valid': True, 'reasons': []}}})
    acceleration = finite_difference([r['knee']['angular_velocity_rad_s'] for r in rows],
                                     [r['timestamp_s'] for r in rows])
    for row, value in zip(rows, acceleration):
        row['knee']['angular_acceleration_rad_s2'] = value
    return rows


def reconstruct(session, calibrations, side='right', beta=0.1, raw_orientations=None):
    matrices = {s: validate_rotation(calibrations[s]['R_sensor_to_segment']) for s in ('thigh','shank')}
    raw_rows = raw_orientations if raw_orientations is not None else orientations(session, side, beta=beta)
    aligned = orientations(session, side, matrices, beta)
    # Whitelist only measurements and essential acquisition identity; never truth/programmed labels.
    result = {key: copy.deepcopy(session[key]) for key in
              ('session_id','participant','sampling','sources','insole_geometry','synthetic') if key in session}
    result['processing'] = {'version': VERSION, 'beta': beta, 'frame': 'X forward; Y left; Z up',
                            'flexion': 'signed +Y sagittal pitch', 'gravity': 'static specific force +Z',
                            'orientation_passes': 'raw sensor, then PCA-aligned measured vectors',
                            'velocity': 'aligned shank gyro Y minus thigh gyro Y',
                            'acceleration': 'one finite difference of gyro-derived velocity',
                            'initial_tilt_iterations': INITIAL_TILT_ITERATIONS,
                            'initial_pose_assumption': 'stationary tilt; common zero segment yaw',
                            'model': 'restricted_sagittal_not_general_3D_anatomy'}
    result['monitored_knee_side'] = side
    result['samples'] = []
    for source, row, raw in zip(session['samples'], aligned, raw_rows):
        output = {'timestamp_s': row['timestamp_s'], 'sequence': row['sequence'],
                  side: {k: copy.deepcopy(row[k]) for k in ('knee','orientation','segment_gyro_rad_s')}}
        output[side]['raw_sensor_orientation'] = raw['orientation']
        for foot in ('left','right'):
            if 'insole' in source.get(foot, {}):
                output.setdefault(foot, {})['insole'] = copy.deepcopy(source[foot]['insole'])
        result['samples'].append(output)
    return result
