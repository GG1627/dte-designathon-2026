import copy
import numpy as np
import pytest
from test_baseline_simulation import ROOT
from generate_raw_sensor_fixture import generate_fixture
from signal_preprocessing import FilterConfig, filter_signal, preprocess, validate_signals


def test_disabled_filter_preserves_ideal_samples():
    raw = generate_fixture()
    result, quality = preprocess(raw)
    assert quality['status'] == 'ready'
    assert result == raw and result is not raw
    assert FilterConfig().metadata()['method'] == 'none'


@pytest.mark.parametrize('mode', ['offline_zero_phase', 'causal'])
def test_butterworth_explicit_modes_finite(mode):
    config = FilterConfig(True, 4, 8, mode, provenance='engineering_demo_parameter')
    values = np.sin(np.arange(1000)/20) + .2*np.cos(np.arange(1000)*2)
    result = filter_signal(values, 100, config)
    assert np.isfinite(result).all()
    assert config.metadata()['causal'] == (mode == 'causal')
    assert np.std(result-values) > .05


@pytest.mark.parametrize('kwargs', [{'order': 0}, {'order': True}, {'enabled': True},
    {'cutoff_hz': float('nan')}, {'cutoff_hz': -1}, {'mode': 'magic'}, {'provenance': ''}])
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        FilterConfig(**kwargs)


def test_nyquist_short_and_missing_fail():
    for values, config in [([0]*100, FilterConfig(True, 4, 50)),
                           ([0]*3, FilterConfig(True, 4, 8)),
                           ([0, float('nan')], FilterConfig())]:
        with pytest.raises(ValueError):
            filter_signal(values, 100, config)


@pytest.mark.parametrize('fault', ['gap', 'quality', 'channel', 'time', 'foot'])
def test_input_quality_no_replacement(fault):
    raw = generate_fixture()
    before = copy.deepcopy(raw)
    row = raw['samples'][100]
    if fault == 'gap': del raw['samples'][100]
    elif fault == 'quality': row['right']['imu']['shank']['quality'] = {'valid': False}
    elif fault == 'channel': row['right']['imu']['shank']['gyro_rad_s']['x'] = None
    elif fault == 'time': row['right']['imu']['shank']['timestamp_s'] = 2
    else: row['left']['insole']['plantar_normal_force_n'] = None
    original = copy.deepcopy(raw)
    result, quality = preprocess(raw)
    assert result is None and quality['status'] == 'invalid_input' and quality['reasons']
    assert raw == original and raw != before


def test_one_pair_fallback_does_not_require_other_knee_or_feet():
    raw = generate_fixture()
    for row in raw['samples']:
        row.pop('left')
        row['right'].pop('insole')
    assert validate_signals(raw, profile='imu_pair_only')['status'] == 'ready'


@pytest.mark.parametrize('fault',['geometry','pressures','fraction','cop','mass','source'])
def test_required_pressure_and_acquisition_channels_fail_clearly(fault):
    raw=generate_fixture()
    if fault=='geometry': raw.pop('insole_geometry')
    elif fault=='mass': raw['participant']['mass_kg']=None
    elif fault=='source': raw['sources']['right'].pop('knee')
    else:
        name={'pressures':'cell_pressures_pa','fraction':'medial_fraction','cop':'cop_m'}[fault]
        raw['samples'][125]['right']['insole'].pop(name)
    original=copy.deepcopy(raw)
    filtered,quality=preprocess(raw)
    assert filtered is None and quality['status']=='invalid_input' and quality['reasons']
    assert raw==original
