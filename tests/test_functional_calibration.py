import copy
import math
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from test_baseline_simulation import ROOT
from madgwick import relative_flexion_y_rad
from aligned_kinematics import reconstruct, orientations
from sensor_to_segment_calibration import calibrate_pair, calibrate_segment


def mounting_fixture(thigh_rotation=(0,0,0), shank_rotation=(0,0,0)):
    """Independent synthetic calibration sweeps and a 4 s test recording."""
    matrices = {s: Rotation.from_euler('xyz', v, degrees=True).as_matrix()
                for s,v in [('thigh',thigh_rotation),('shank',shank_rotation)]}
    calibration = {}
    for s, matrix in matrices.items():
        calibration[s] = {'static_accel': [(matrix.T @ [0,0,9.80665]).tolist()]*30,
                          'positive_flexion_gyro': [(matrix.T @ [0,v,0]).tolist()
                                                   for v in np.linspace(.1,1,60)]}
    samples, truth = [], []
    for i in range(401):
        t = i/100
        angle = math.radians(45)*(1-math.cos(math.pi*t/2))/2
        velocity = math.radians(45)*math.pi/4*math.sin(math.pi*t/2)
        row = {'timestamp_s':t,'sequence':i,'right':{'imu':{}}}
        for s in matrices:
            a,v = (angle,velocity) if s == 'shank' else (0,0)
            gyro = matrices[s].T @ [0,v,0]
            accel = matrices[s].T @ [-9.80665*math.sin(a),0,9.80665*math.cos(a)]
            row['right']['imu'][s] = {'gyro_rad_s':dict(zip('xyz',gyro.tolist())),
                                     'accel_m_s2':dict(zip('xyz',accel.tolist())),
                                     'quality':{'valid':True}}
        samples.append(row)
        truth.append(angle)
    return {'samples':samples,'sampling':{'rate_hz':100},'session_id':'mounting_test',
            'participant':{'id':'synthetic_athlete','mass_kg':75},'synthetic':True}, calibration, truth


@pytest.mark.parametrize('thigh,shank', [((0,0,0),(0,0,0)),((15,0,0),(0,0,0)),
    ((0,0,0),(25,10,-20)),((15,-10,12),(-25,15,-30))])
def test_mounting_recovery(thigh,shank):
    raw, records, truth = mounting_fixture(thigh,shank)
    original = copy.deepcopy(raw)
    calibration = calibrate_pair(records)
    for result in calibration.values():
        matrix = np.array(result['R_sensor_to_segment'])
        assert np.allclose(matrix@matrix.T,np.eye(3),atol=1e-10)
        assert np.linalg.det(matrix) == pytest.approx(1)
    naive = orientations(raw)
    aligned = reconstruct(raw,calibration)['samples']
    rmse = math.degrees(np.sqrt(np.mean([(r['right']['knee']['flexion_rad']-t)**2
                                        for r,t in zip(aligned,truth)])))
    naive_rmse = math.degrees(np.sqrt(np.mean([(r['knee']['flexion_rad']-t)**2
                                              for r,t in zip(naive,truth)])))
    assert rmse < .5
    if thigh != (0,0,0) or shank != (0,0,0): assert naive_rmse > rmse*2
    assert raw == original
    assert all('left' not in r for r in aligned)
    for r in aligned:
        for q in r['right']['orientation'].values():
            assert np.isfinite(q).all() and np.linalg.norm(q) == pytest.approx(1)


def test_calibration_truth_independence():
    raw,records,_ = mounting_fixture((15,0,0),(20,10,30))
    expected = calibrate_pair(records)
    records['ground_truth_mounting'] = 'poisoned'
    raw['ground_truth'] = 'poisoned'
    assert calibrate_pair(records) == expected
    assert 'ground_truth' not in reconstruct(raw,expected)


@pytest.mark.parametrize('fault', ['zero_static','zero_gyro','ambiguous_sign','parallel'])
def test_degenerate_calibration_requires_protocol(fault):
    static = np.tile([0,0,9.8],(30,1))
    gyro = np.array([[0,v,0] for v in np.linspace(.1,1,60)])
    if fault == 'zero_static': static *= 0
    elif fault == 'zero_gyro': gyro *= 0
    elif fault == 'ambiguous_sign': gyro -= gyro.mean(axis=0)
    else: gyro = gyro[:,[0,2,1]]
    with pytest.raises(ValueError): calibrate_segment(static,gyro)
