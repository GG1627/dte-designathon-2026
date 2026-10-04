"""Deterministic FOUR-IMU engineering fixtures; no hardware validation."""
import math

from generate_mock_data import session
from generate_raw_sensor_fixture import to_raw_session
from synthetic_movement import ideal_calibration_records
from sensor_configuration import SensorConfiguration, SIDES
from signal_preprocessing import FilterConfig
from kintra_pipeline import PipelineConfig

SCENARIOS = ('symmetric','right_rom_reduced','right_force_increased',
             'left_calibration_invalid','right_knee_absent','incompatible_processing','missing_left')


def bilateral_fixture(scenario='symmetric', session_id=None):
    if scenario not in SCENARIOS:
        raise ValueError('Unknown bilateral engineering scenario')
    landings = [{'start_s':t,'end_s':t+.6,'flexion_offset_s':{s:.25 for s in SIDES},
                 'flexion_sigma_s':.18,
                 'flexion_amplitude_rad':{s:math.radians(36)*(.8 if s=='right' and scenario=='right_rom_reduced' else 1) for s in SIDES},
                 'force_scale':{s:1.2 if s=='right' and scenario=='right_force_increased' else 1 for s in SIDES}}
                for t in (1.,3.,5.)]
    raw = to_raw_session(session('balanced',landings))
    raw['session_id'] = session_id or f'synthetic_bilateral_{scenario}'
    # Programmed labels and analytic truth never enter the pipeline.
    for key in ('annotations','scenario','activity','processing'):
        raw.pop(key,None)
    missing = 'left' if scenario=='missing_left' else 'right' if scenario=='right_knee_absent' else None
    for row in raw['samples']:
        row.pop('ground_truth',None)
        for side in SIDES:
            for packet in (*row[side]['imu'].values(),row[side]['insole']):
                packet.update(source='synthetic_demo',synthetic=True)
            if side == missing:
                row[side].pop('imu')
    if missing:
        raw['sources'][missing].pop('knee')
    return raw


def fixture_config(raw, scenario='symmetric', **kwargs):
    """Scripted confirmation and calibration acquisitions are explicitly synthetic."""
    mode = 'single_knee_plus_mock_insoles' if scenario=='missing_left' else 'bilateral_knees_plus_insoles'
    options = {s:{'calibration_records':ideal_calibration_records()} for s in SIDES}
    if scenario=='left_calibration_invalid':
        options['left']['calibration_records']['thigh']['positive_flexion_gyro'] = [[0,0,0]]*60
    if scenario=='incompatible_processing':
        options['right']['filter'] = FilterConfig(enabled=True,cutoff_hz=8,provenance='engineering_demo_parameter')
    supplied = kwargs.pop('side_options',{})
    for side, values in supplied.items():
        options[side].update(values)
    defaults = {'sensor_configuration':SensorConfiguration.synthetic(raw,mode),'side_options':options,
        'confirmed_activity':'basketball_training','confirmed_movement':'repeated_jump_landing',
        'movement_source':'manually_selected','activity_source':'manually_selected'}
    return PipelineConfig(**{**defaults,**kwargs})
