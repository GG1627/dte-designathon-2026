"""Adapter from one-knee canonical events into the existing session median/MAD learner.

No new scalar baseline estimator. Contact-window impulse has a distinct metric
name and processing context; legacy annotated-window histories cannot be mixed.
"""
import copy
from statistics import median
from baseline_simulation import Rules, digest, fit_baseline, compare_evaluations
from athlete_confirmation import TRUSTED
from signal_preprocessing import finite

VERSION = 'confirmed-contact-reference-adapter/1.0.0'


def metric_source(record, metric, side):
    sources = record.get('measurement_sources', {})
    return sources.get('knee') if metric.startswith('knee_') else sources.get('insoles', {}).get(side)


def complete_confirmation(record):
    c = record.get('confirmation',{})
    return (c.get('status')=='confirmed' and c.get('movement_source') in TRUSTED and c.get('source') in TRUSTED
            and all(isinstance(c.get(k),str) and c[k].strip() for k in ('confirmed_movement','confirmed_activity')))


def context_key(record, sensor_configuration, processing_configuration):
    c = record.get('confirmation',{})
    complete = complete_confirmation(record)
    return {'participant_id':record['participant_id'],'joint':'knee','side':record['side'],
            'activity':c.get('confirmed_activity') if complete else None,
            'confirmed_activity':c.get('confirmed_activity') if complete else None,
            'confirmed_movement':c.get('confirmed_movement') if complete else None,
            'configuration_id':sensor_configuration['profile'],
            'configuration_signature':digest(sensor_configuration),
            'processing_version':VERSION,'processing_signature':digest(processing_configuration)}


def scalar_session(record, role='evaluation', rules=Rules()):
    if role not in ('reference','evaluation'): raise ValueError('Explicit reference/evaluation role required')
    context = record['context']
    summaries, event_metrics = [], []
    for name,value in record['biomechanics']['session_metrics'].items():
        side = 'left' if name.startswith('left_') else 'right' if name.startswith('right_') else record['side']
        metric = name.removeprefix(f'{side}_')
        unit = 'rad' if metric=='knee_rom_rad' else 'BW*s' if 'impulse' in metric else 'BW'
        values = []
        for event in record['biomechanics']['events']:
            if metric=='knee_rom_rad':
                wave = event['knee_flexion_waveform_rad']
                observed = max(wave)-min(wave)
            elif metric=='peak_plantar_normal_force_bw':
                observed = event['loading'][side]['peak_force_bw']
            else:
                impulse = event['loading'][side]['impulse_n_s']
                bw = record.get('body_weight_n')
                observed = impulse/bw if finite(impulse) and finite(bw) and bw>0 else None
            valid = finite(observed)
            event_metrics.append({'event_id':event['event_id'],'side':side,'metric':metric,
                'value':observed,'status':'accepted' if valid else 'rejected',
                'reasons':[] if valid else ['metric_unavailable'],'unit':unit})
            if 'measurement_sources' in record:
                event_metrics[-1]['source'] = metric_source(record,metric,side)
            if valid: values.append(observed)
        eligible = len(values)>=rules.min_valid_events
        center = median(values) if eligible else None
        reasons = [] if eligible else ['insufficient_valid_events']
        if not complete_confirmation(record): reasons.append('movement_and_activity_confirmation_required')
        summaries.append({'side':side,'metric':metric,'unit':unit,
            'status':'accepted' if eligible and complete_confirmation(record) else 'unavailable',
            'median':center,'event_mad':median(abs(v-center) for v in values) if eligible else None,
            'valid_event_count':len(values),'total_event_count':len(record['biomechanics']['events']),
            'valid_event_ids':[e['event_id'] for e in record['biomechanics']['events']],
            'reasons':reasons,'rejected_events':[]})
        if 'measurement_sources' in record:
            summaries[-1]['source'] = metric_source(record,metric,side)
    return {'session_id':record['session_id'],'synthetic':record.get('synthetic',False),
            'metadata':{'role':role,'activity_context':{'confirmation':copy.deepcopy(record.get('confirmation',{}))}},
            'context':copy.deepcopy(context),'processing':{'version':VERSION,'rules':{
                'min_valid_events':rules.min_valid_events}},'session_metrics':summaries,'event_metrics':event_metrics}


def fit_personal_reference(records, rules=Rules()):
    result = fit_baseline([scalar_session(r,'reference',rules) for r in records],rules)
    if records and all('measurement_sources' in r for r in records):
        result['synthetic'] = all(r.get('synthetic') is True for r in records)
        result['contains_synthetic_measurements'] = any(
            'synthetic_demo' in (r['measurement_sources']['knee'],*r['measurement_sources']['segments'].values(),
                               *r['measurement_sources']['insoles'].values()) for r in records)
    for metric in result['metrics']:
        match = next((r for r in records if r['context']==metric['context']), None)
        if match is not None and 'measurement_sources' in match:
            metric['source'] = metric_source(match,metric['metric'],metric['side'])
    return result


def compare_personal_reference(record, reference):
    if not complete_confirmation(record):
        return {'status':'requires_confirmation','version':VERSION,
                'reasons':['confirmed_movement_and_activity_required'],'comparisons':[]}
    if reference is None:
        return {'status':'insufficient_reference','version':VERSION,'reasons':['no_matching_confirmed_history'],'comparisons':[]}
    result = compare_evaluations(reference,[scalar_session(record,'evaluation',Rules(**reference['rules']))])[0]
    comparisons = result['comparisons']
    if 'measurement_sources' in record:
        for comparison in comparisons:
            comparison['source'] = metric_source(record,comparison['metric'],comparison['side'])
            match = next((m for m in reference['metrics'] if m['context']==record['context'] and
                m['metric']==comparison['metric'] and m['side']==comparison['side']), None)
            comparison['reference_source'] = match.get('source') if match else None
    ready = bool(comparisons) and all(c['comparison_availability']=='available' for c in comparisons)
    return {'status':'ready' if ready else 'insufficient_reference','version':VERSION,
            'reasons':sorted({reason for c in comparisons for reason in c['reasons']}) if not ready else [],
            'comparisons':comparisons,'reference_status':'provisional_reference' if ready else 'insufficient_reference',
            'reference_updating':'fixed','insights':result['insights']}
