"""Descriptive comparisons of computed metrics, never a second signal pipeline.

Absolute asymmetry = abs(L-R) / mean(L,R) * 100 (existing Kintra helper).
Signed difference and signed asymmetry use RIGHT minus LEFT. Undefined mean
remains null. A failed knee gate nulls ALL numeric comparison fields.
"""
from statistics import median
from sensor_configuration import SIDES, combined_source
from biomechanical_events import finite

VERSION = 'bilateral-comparison/1.0.0'
KNEE_METRICS = ('rom_deg','peak_flexion_deg','peak_abs_velocity_deg_s',
                'peak_abs_acceleration_deg_s2','time_to_peak_flexion_s')
FOOT_METRICS = ('peak_plantar_normal_force_n','peak_force_bw','impulse_n_s','contact_time_s')
FIELDS = ('left','right','signed_difference_right_minus_left','absolute_difference',
          'asymmetry_percent','signed_asymmetry_percent')


def asymmetry_percent(left, right):
    """Return absolute bilateral asymmetry, or None when undefined."""
    denominator = (left + right) / 2
    return abs(left - right) / denominator * 100 if denominator != 0 else None

def comparison(left=None, right=None, percent=True):
    result = dict.fromkeys(FIELDS)
    if not finite(left) or not finite(right):
        return result
    mean = (left+right)/2
    return {**result,'left':left,'right':right,'signed_difference_right_minus_left':right-left,
            'absolute_difference':abs(left-right),
            'asymmetry_percent':asymmetry_percent(left,right) if percent else None,
            'signed_asymmetry_percent':(right-left)/mean*100 if percent and mean != 0 else None}


def result_shell(names, reasons, sources):
    return {'status':'unavailable' if reasons else 'ready','version':VERSION,'reasons':sorted(set(reasons)),
            'source':combined_source(sources.values()),'sources':sources,
            'metrics':{name:comparison() for name in names},'events':[],
            'formula':'abs(left-right)/((left+right)/2)*100',
            'signed_convention':'right_minus_left','zero_denominator':'null',
            'measurement_reliability':{'status':'reliability_not_established','mdc':None,
                'change_exceeds_measurement_error':None},'medical_inference':False}


def paired_events(left, right, pairs):
    """Join precomputed contacts by shared sample indices; no signal estimation."""
    joined = []
    for pair in pairs:
        a = next((e for e in left if e['onset_index']==pair['left_onset_index']),None)
        b = next((e for e in right if e['onset_index']==pair['right_onset_index']),None)
        if a is not None and b is not None:
            joined.append((a,b))
    return joined


def compare_knees(knees, pairs):
    from contextual_reference import complete_confirmation
    reasons = []
    sources = {s:knees[s]['source'] for s in SIDES}
    for side in SIDES:
        knee = knees[side]
        if knee['status'] != 'ready':
            reasons.extend(knee['reasons'] or [f'{side}_knee_not_ready'])
        for name in ('input_quality','calibration','events','biomechanics'):
            if knee[name]['status'] != 'ready':
                reasons.append(f'{side}_{name}_not_ready')
        if any(knee['calibration'].get('segments',{}).get(segment,{}).get('status') != 'ready'
               for segment in ('thigh','shank')):
            reasons.append(f'{side}_thigh_and_shank_calibration_required')
        record = knee.get('record')
        if record is None or not complete_confirmation(record):
            reasons.append(f'{side}_confirmed_movement_and_activity_required')
        elif record.get('side') != side or record['context'].get('side') != side:
            reasons.append(f'{side}_incompatible_side_context')
        elif any(record['context'].get(k) != record['confirmation'].get(v) for k,v in
                 (('activity','confirmed_activity'),('confirmed_movement','confirmed_movement'))):
            reasons.append(f'{side}_incompatible_confirmation_context')
    records = [knees[s].get('record') for s in SIDES]
    if all(records):
        if records[0]['session_id'] != records[1]['session_id']:
            reasons.append('different_acquisition_sessions')
        if any(records[0]['context'].get(k) != records[1]['context'].get(k) for k in
               ('participant_id','joint','activity','confirmed_movement')):
            reasons.append('incompatible_confirmed_context')
        if records[0]['processing_configuration'] != records[1]['processing_configuration']:
            reasons.append('incompatible_processing')
        if knees['left']['comparison_configuration'] != knees['right']['comparison_configuration']:
            reasons.append('incompatible_sensor_configuration')
    joined = paired_events(knees['left']['events'].get('landings',[]),
                           knees['right']['events'].get('landings',[]),pairs)
    if not joined or len(joined) != len(knees['left']['events'].get('landings',[])) or len(joined) != len(knees['right']['events'].get('landings',[])):
        reasons.append('complete_compatible_bilateral_events_required')
    values = []
    for a,b in joined:
        event_values = []
        for side,event in zip(SIDES,(a,b)):
            metric = next((e for e in knees[side]['biomechanics'].get('events',[])
                           if e['event_id']==event['event_id']),None)
            k = metric['kinematics'] if metric else {}
            measured = {'rom_deg':k.get('rom_deg'),'peak_flexion_deg':k.get('maximum_deg'),
                'peak_abs_velocity_deg_s':k.get('peak_abs_velocity_deg_s'),
                'peak_abs_acceleration_deg_s2':k.get('peak_abs_acceleration_deg_s2'),
                'time_to_peak_flexion_s':event['peak_flexion_s']-event['start_s']}
            if k.get('quality',{}).get('valid') is not True or not all(finite(v) for v in measured.values()):
                reasons.append(f'{side}_required_event_metrics_unavailable')
            event_values.append(measured)
        values.append((a,b,*event_values))
    output = result_shell(KNEE_METRICS,reasons,sources)
    if reasons:
        return output
    for a,b,left,right in values:
        output['events'].append({'left_event_id':a['event_id'],'right_event_id':b['event_id'],
            'metrics':{name:comparison(left[name],right[name],name not in ('peak_flexion_deg','time_to_peak_flexion_s'))
                       for name in KNEE_METRICS}})
    for name in KNEE_METRICS:
        output['metrics'][name] = comparison(median(v[2][name] for v in values),median(v[3][name] for v in values),
                                             name not in ('peak_flexion_deg','time_to_peak_flexion_s'))
    return output


def compare_plantar(insoles, pairs):
    reasons = [f'{s}_insole_not_ready' for s in SIDES if insoles[s]['status']!='ready']
    if not insoles['left'].get('session_id') or insoles['left']['session_id'] != insoles['right'].get('session_id'):
        reasons.append('different_acquisition_sessions')
    joined = paired_events(insoles['left'].get('events',[]),insoles['right'].get('events',[]),pairs)
    if not joined or any(len(joined)!=len(insoles[s].get('events',[])) for s in SIDES):
        reasons.append('complete_bilateral_foot_contacts_required')
    if any(e['loading']['quality']['valid'] is not True or
           not all(finite(e['loading'].get(name)) for name in FOOT_METRICS)
           for pair in joined for e in pair):
        reasons.append('required_plantar_metrics_unavailable')
    output = result_shell(FOOT_METRICS,reasons,{s:insoles[s]['source'] for s in SIDES})
    if reasons:
        return output
    for left,right in joined:
        output['events'].append({'left_event_id':left['event_id'],'right_event_id':right['event_id'],
            'metrics':{name:comparison(left['loading'][name],right['loading'][name],name!='contact_time_s')
                       for name in FOOT_METRICS}})
    for name in FOOT_METRICS:
        output['metrics'][name] = comparison(median(pair[0]['loading'][name] for pair in joined),
            median(pair[1]['loading'][name] for pair in joined),name!='contact_time_s')
    return output
