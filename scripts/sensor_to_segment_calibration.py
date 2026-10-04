"""Static + functional PCA calibration, with an explicit signed flexion protocol.

Static pose must put the segment long axis along world +Z. Functional samples
must be a designated POSITIVE flexion sweep; PCA alone cannot identify axis sign.
This restricted protocol is not general anatomical calibration or hardware validation.
"""
import numpy as np

VERSION = 'static-functional-pca/1.0.0'


def vectors(values, minimum):
    result = np.asarray(values, dtype=float)
    if result.ndim != 2 or result.shape[1] != 3 or len(result) < minimum or not np.isfinite(result).all():
        raise ValueError('Finite Nx3 calibration measurements required')
    return result


def unit(vector):
    norm = np.linalg.norm(vector)
    if norm < 1e-10:
        raise ValueError('Degenerate calibration axis')
    return vector / norm


def calibrate_segment(static_accel, positive_flexion_gyro):
    """Only measured arrays enter this function, never fixture/mounting labels.

    Sensor-to-segment matrix rows are anatomical X/Y/Z axes in sensor coordinates.
    +Z comes from upright static specific force; +Y is the dominant centered gyro
    PC signed using the mean of a protocol-designated positive flexion sweep.
    X=Y cross Z; Y=Z cross X. Degenerate/ambiguous motion is rejected.
    """
    static = vectors(static_accel, 3)
    gyro = vectors(positive_flexion_gyro, 6)
    z = unit(static.mean(axis=0))
    centered = gyro - gyro.mean(axis=0)
    _, singular, vt = np.linalg.svd(centered, full_matrices=False)
    if singular[0] < 1e-8 or singular[0] <= 2 * singular[1]:
        raise ValueError('Functional rotation axis is unexcited or ambiguous')
    axis = vt[0]
    sign = float(axis @ gyro.mean(axis=0))
    if abs(sign) < 1e-8:
        raise ValueError('Positive-flexion protocol must resolve PCA axis sign')
    y = axis if sign > 0 else -axis
    x = unit(np.cross(y, z))
    y = unit(np.cross(z, x))
    matrix = np.stack([x, y, z])
    if not np.allclose(matrix @ matrix.T, np.eye(3), atol=1e-10) or not np.isclose(np.linalg.det(matrix), 1):
        raise ValueError('Calibration must be a proper orthonormal rotation')
    return {'status': 'ready', 'version': VERSION, 'R_sensor_to_segment': matrix.tolist(),
            'singular_values': singular.tolist(), 'static_sample_count': len(static),
            'functional_sample_count': len(gyro), 'axis_sign_source': 'designated_positive_flexion_sweep',
            'static_pose': 'upright_segment_long_axis_world_positive_Z',
            'hardware_validated': False, 'provenance': 'measured_static_and_functional_arrays'}


def validate_rotation(matrix):
    matrix = np.asarray(matrix, dtype=float)
    if (matrix.shape != (3, 3) or not np.isfinite(matrix).all() or
        not np.allclose(matrix @ matrix.T, np.eye(3), atol=1e-8) or
        not np.isclose(np.linalg.det(matrix), 1, atol=1e-8)):
        raise ValueError('Invalid sensor-to-segment rotation')
    return matrix


def calibrate_pair(records):
    return {segment: calibrate_segment(records[segment]['static_accel'],
                                      records[segment]['positive_flexion_gyro'])
            for segment in ('thigh', 'shank')}
