"""Session-level EWMA analytics, separate from the fixed personal reference."""
import copy
from dataclasses import dataclass
from signal_preprocessing import finite

VERSION = 'session-ewma/1.0.0'
METRICS = ('knee_rom_rad','left_peak_plantar_normal_force_bw','right_peak_plantar_normal_force_bw',
           'left_contact_window_impulse_bw_s','right_contact_window_impulse_bw_s','knee_flexion_dtw_distance')


@dataclass(frozen=True)
class EWMAConfig:
    lambda_: float
    metric: str
    context: dict
    provenance: str = 'engineering_demo_smoothing_factor'

    def __post_init__(self):
        if (not finite(self.lambda_) or not 0 < self.lambda_ <= 1 or self.metric not in METRICS or
            not self.context.get('confirmed_movement') or not self.context.get('activity') or not self.provenance):
            raise ValueError('EWMA requires explicit factor, selected metric and confirmed context')


def session_ewma(observations, config):
    """Initialize at first valid session value; missing observations stay null.

    Missing sessions do not advance the smoother; resume from last valid state.
    This policy is recorded. It is not interpolation or baseline adaptation.
    """
    ids = [o['session_id'] for o in observations]
    indices = [o['chronological_index'] for o in observations]
    if len(ids)!=len(set(ids)) or any(type(i) is not int for i in indices) or any(b<=a for a,b in zip(indices,indices[1:])):
        raise ValueError('Unique sessions in explicit chronological order required')
    points, previous = [], None
    for observation in observations:
        value = observation.get('value')
        reasons = []
        if observation.get('context')!=config.context:
            reasons.append('incompatible_context')
        if observation.get('status')!='ready' or not finite(value):
            reasons.append('session_metric_unavailable')
        smoothed = None
        if not reasons:
            previous = value if previous is None else config.lambda_*value+(1-config.lambda_)*previous
            smoothed = previous
        points.append({'session_id':observation['session_id'],'chronological_index':observation['chronological_index'],
                       'value':value if finite(value) else None,'ewma':smoothed,
                       'status':'unavailable' if reasons else 'ready','reasons':reasons})
    valid = [p['ewma'] for p in points if p['status']=='ready']
    difference = valid[-1]-valid[0] if len(valid)>=2 else None
    direction = ('increased' if difference>0 else 'decreased' if difference<0 else 'unchanged') if difference is not None else None
    return {'status':'ready' if len(valid)>=2 else 'unavailable','version':VERSION,
            'reasons':[] if len(valid)>=2 else ['insufficient_comparable_session_values'],
            'metric':config.metric,'context':copy.deepcopy(config.context),'lambda':config.lambda_,
            'provenance':config.provenance,'initialization':'first_valid_session_value',
            'missing_policy':'null_point; no_state_update; resume_from_last_valid_state',
            'points':points,'direction':direction,'first_to_last_ewma_difference':difference,
            'reference_updating':'none; analytics_only',
            'spc_status':'reference_limits_not_established','athlete_alarm':None}
