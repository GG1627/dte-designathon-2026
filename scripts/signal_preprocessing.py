"""Strict, non-interpolating signal validation and explicit Butterworth SOS filters."""
import copy
import math
from dataclasses import asdict, dataclass

import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi, sosfiltfilt
from generate_mock_data import (reconstructed_force, CONTACT_THRESHOLD_N,
                                PRESSURE_FORCE_REL_TOL, PRESSURE_FORCE_ABS_TOL_N)

VERSION = 'signal-preprocessing/1.0.0'
PROFILES = ('imu_pair_plus_insole', 'imu_pair_only')


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


@dataclass(frozen=True)
class FilterConfig:
    enabled: bool = False
    order: int = 4
    cutoff_hz: float | None = None
    mode: str = 'offline_zero_phase'
    signal_type: str = 'imu'
    provenance: str = 'ideal_synthetic_filter_none'

    def __post_init__(self):
        if type(self.enabled) is not bool or type(self.order) is not int or self.order < 1:
            raise ValueError('Filter enabled must be boolean and order a positive integer')
        if self.mode not in ('offline_zero_phase', 'causal') or self.signal_type != 'imu':
            raise ValueError('Supported filter modes: offline_zero_phase/causal; signal_type: imu')
        if not self.provenance or (self.cutoff_hz is not None and
                                  (not finite(self.cutoff_hz) or self.cutoff_hz <= 0)):
            raise ValueError('Explicit provenance and positive finite cutoff required')
        if self.enabled and self.cutoff_hz is None:
            raise ValueError('Enabled filtering requires an explicit cutoff_hz')

    def metadata(self):
        return {**asdict(self), 'method': 'Butterworth SOS' if self.enabled else 'none',
                'causal': self.mode == 'causal' if self.enabled else None,
                'version': VERSION}


def filter_signal(values, rate_hz, config=FilterConfig()):
    if not finite(rate_hz) or rate_hz <= 0 or not len(values):
        raise ValueError('Positive sampling rate and nonempty signal required')
    array = np.asarray(values, dtype=float)
    if not np.isfinite(array).all():
        raise ValueError('Invalid values remain missing; filtering cannot bridge dropout')
    if not config.enabled:
        return array.copy()
    if config.cutoff_hz >= rate_hz / 2:
        raise ValueError('cutoff_hz must be below Nyquist')
    sos = butter(config.order, config.cutoff_hz, fs=rate_hz, output='sos')
    if config.mode == 'offline_zero_phase':
        # SciPy checks its default pad length; do not shorten padding to hide short input.
        result = sosfiltfilt(sos, array, axis=0)
    else:
        zi = sosfilt_zi(sos)
        if array.ndim == 2:
            zi = zi[:, :, None] * array[0]
        else:
            zi = zi * array[0]
        result, _ = sosfilt(sos, array, axis=0, zi=zi)
    if not np.isfinite(result).all():
        raise ValueError('Nonfinite filter output')
    return result


def validate_signals(session, side='right', profile='imu_pair_plus_insole', *, knee_required=True, feet=('left','right')):
    """Validate only the monitored knee pair, and both feet for the insole profile."""
    reasons = set()
    if profile not in PROFILES or side not in ('left', 'right'):
        return {'status': 'invalid_input', 'reasons': ['unsupported_sensor_configuration']}
    rows = session.get('samples', [])
    rate = session.get('sampling', {}).get('rate_hz')
    if not finite(rate) or rate <= 0 or len(rows) < 3:
        return {'status': 'invalid_input', 'reasons': ['invalid_sampling_or_missing_samples']}
    sources = session.get('sources',{})
    pair = sources.get(side,{}).get('knee')
    if knee_required and (not isinstance(pair,list) or len(pair)!=2 or
        not all(isinstance(s,str) and s.strip() for s in pair) or len(set(pair))!=2):
        reasons.add('two_distinct_imu_source_ids_required')
    if profile == 'imu_pair_plus_insole':
        mass = session.get('participant',{}).get('mass_kg')
        if not finite(mass) or mass<=0:
            reasons.add('body_weight_normalization_requires_valid_mass')
        for foot in feet:
            cells = session.get('insole_geometry',{}).get(foot)
            if not isinstance(cells,list) or not cells:
                reasons.add('insole_geometry_required')
            if not isinstance(sources.get(foot,{}).get('insole'),str):
                reasons.add('bilateral_insole_source_ids_required')
    undeclared_quality_count = 0
    for i, row in enumerate(rows):
        t = row.get('timestamp_s')
        seq = row.get('sequence')
        if not finite(t) or type(seq) is not int:
            reasons.add('invalid_timestamp_or_sequence')
        if i:
            previous = rows[i - 1]
            if (not finite(t) or not finite(previous.get('timestamp_s')) or
                not math.isclose(t - previous['timestamp_s'], 1/rate, rel_tol=0, abs_tol=1e-8) or
                type(seq) is not int or type(previous.get('sequence')) is not int or
                seq != previous['sequence'] + 1):
                reasons.add('sample_discontinuity')
        for segment in ('thigh', 'shank') if knee_required else ():
            packet = row.get(side, {}).get('imu', {}).get(segment, {})
            if 'quality' not in packet:
                undeclared_quality_count += 1
            # Legacy ideal fixture packets omit flags. Preserve that existing
            # contract; an explicit invalid flag is never ignored.
            if packet.get('quality', {}).get('valid', True) is not True:
                reasons.add('invalid_imu_quality')
            for channel in ('gyro_rad_s', 'accel_m_s2'):
                if not all(finite(packet.get(channel, {}).get(axis)) for axis in ('x', 'y', 'z')):
                    reasons.add('missing_or_nonfinite_imu_channel')
            time = packet.get('timestamp_s', t)
            if not finite(time) or not finite(t) or abs(time - t) > 1e-8:
                reasons.add('unaligned_imu_timestamp')
        if profile == 'imu_pair_plus_insole':
            for foot in feet:
                packet = row.get(foot, {}).get('insole', {})
                force = packet.get('plantar_normal_force_n')
                if packet.get('quality', {}).get('valid') is not True or not finite(force) or force < 0:
                    reasons.add('invalid_or_missing_insole')
                if packet.get('quality',{}).get('valid') is True:
                    cells = session.get('insole_geometry',{}).get(foot)
                    if isinstance(cells,list) and cells:
                        try:
                            reconstructed = reconstructed_force(packet.get('cell_pressures_pa'),cells)
                            if finite(force) and not math.isclose(reconstructed,force,
                                rel_tol=PRESSURE_FORCE_REL_TOL,abs_tol=PRESSURE_FORCE_ABS_TOL_N):
                                reasons.add('inconsistent_pressure_force')
                        except (ValueError,TypeError,KeyError):
                            reasons.add('invalid_or_missing_pressure_channel_or_geometry')
                    if finite(force) and force>CONTACT_THRESHOLD_N:
                        fractions = [packet.get(k) for k in ('medial_fraction','lateral_fraction')]
                        cop = packet.get('cop_m')
                        if (not all(finite(v) and 0<=v<=1 for v in fractions) or
                            not isinstance(cop,dict) or not all(finite(cop.get(k)) for k in ('x_m','y_m'))):
                            reasons.add('invalid_or_missing_contact_pressure_descriptors')
                time = packet.get('timestamp_s', t)
                if not finite(time) or not finite(t) or abs(time - t) > 1e-8:
                    reasons.add('unaligned_insole_timestamp')
    return {'status': 'invalid_input' if reasons else 'ready', 'reasons': sorted(reasons),
            'version': VERSION, 'profile': profile, 'monitored_knee_side': side,
            'interpolation': 'none', 'interval_tolerance_s': 1e-8,
            'imu_packets_without_declared_quality_flags':undeclared_quality_count,
            'undeclared_flag_policy':'legacy_ideal_fixture_assumed_valid; not hardware verification'}


def preprocess(session, config=FilterConfig(), side='right', profile='imu_pair_plus_insole'):
    quality = validate_signals(session, side, profile)
    if quality['status'] != 'ready':
        return None, quality
    result = copy.deepcopy(session)
    for segment in ('thigh', 'shank'):
        for channel in ('gyro_rad_s', 'accel_m_s2'):
            values = [[row[side]['imu'][segment][channel][a] for a in ('x', 'y', 'z')]
                      for row in session['samples']]
            filtered = filter_signal(values, session['sampling']['rate_hz'], config)
            for row, vector in zip(result['samples'], filtered):
                row[side]['imu'][segment][channel] = dict(zip(('x', 'y', 'z'), vector.tolist()))
    return result, quality
