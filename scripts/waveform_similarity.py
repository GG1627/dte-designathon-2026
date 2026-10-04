"""Descriptive DTW shape distances and a context-conditioned event medoid.

Standard endpoint-constrained dynamic programming: squared local cost, allowed
steps diagonal/right/down, deterministic ties. Report RMS cost along optimal
minimum-total-cost path. No clinical distance threshold or composite score.
"""
import copy
import numpy as np
from baseline_simulation import Rules, digest
from contextual_reference import complete_confirmation

VERSION = 'dtw-shape-medoid/1.0.0'
WAVEFORM = 'knee_flexion_rad_during_canonical_contact'


def normalize_waveform(values):
    array = np.asarray(values,float)
    if array.ndim!=1 or len(array)<3 or not np.isfinite(array).all():
        raise ValueError('At least three finite waveform samples required; no interpolation')
    try:
        with np.errstate(over='raise',invalid='raise',divide='raise'):
            scale = float(array.std())
            center = float(array.mean())
    except FloatingPointError as error:
        raise ValueError('Waveform normalization exceeded finite numerical range') from error
    if scale <= 1e-12:
        raise ValueError('Constant waveform has no identifiable z-normalized shape')
    return (array-center)/scale


def dtw_distance(first, second):
    a,b = normalize_waveform(first),normalize_waveform(second)
    costs = np.full((len(a)+1,len(b)+1),np.inf)
    lengths = np.zeros_like(costs,dtype=int)
    costs[0,0] = 0
    for i in range(1,len(a)+1):
        for j in range(1,len(b)+1):
            parents = ((i-1,j-1),(i-1,j),(i,j-1))
            parent = min(parents,key=lambda p:costs[p])
            costs[i,j] = costs[parent]+(a[i-1]-b[j-1])**2
            lengths[i,j] = lengths[parent]+1
    distance = float(np.sqrt(costs[-1,-1]/lengths[-1,-1]))
    return {'status':'ready','version':VERSION,'waveform_type':WAVEFORM,
            'normalization':'per_event_z_score_population_SD',
            'preprocessing':'upstream_recorded_filter; no_resampling_or_interpolation',
            'number_of_samples':{'current':len(a),'reference':len(b)},
            'method':'endpoint_constrained_DTW_squared_cost_RMS_over_optimal_path',
            'path_length':int(lengths[-1,-1]),'distance':distance,
            'interpretation':'descriptive_shape_distance; no established athlete thresholds'}


def fit_waveform_reference(records, rules=Rules()):
    ids = [r['session_id'] for r in records]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate waveform reference sessions')
    groups = {}
    excluded = []
    for record in records:
        if not complete_confirmation(record):
            excluded.append({'session_id':record['session_id'],'reason':'requires_confirmation'})
            continue
        c = record['confirmation']
        if (record['context']['confirmed_movement']!=c['confirmed_movement'] or
            record['context']['activity']!=c['confirmed_activity']):
            excluded.append({'session_id':record['session_id'],'reason':'incompatible_confirmation_context'})
            continue
        waves = []
        for event in record['biomechanics']['events']:
            try:
                normalize_waveform(event['knee_flexion_waveform_rad'])
                waves.append({'session_id':record['session_id'],'event_id':event['event_id'],
                              'values':copy.deepcopy(event['knee_flexion_waveform_rad'])})
            except ValueError:
                excluded.append({'session_id':record['session_id'],'event_id':event['event_id'],'reason':'invalid_waveform'})
        if len(waves)<rules.min_valid_events:
            excluded.append({'session_id':record['session_id'],'reason':'insufficient_valid_events'})
            continue
        key = digest(record['context'])
        group = groups.setdefault(key,{'context':copy.deepcopy(record['context']),'waves':[],'session_ids':[]})
        if 'measurement_sources' in record:
            group['source'] = record['measurement_sources']['knee']
        group['waves'].extend(waves)
        group['session_ids'].append(record['session_id'])
    references = []
    for group in groups.values():
        waves = group['waves']
        ready = len(group['session_ids'])>=rules.min_reference_sessions
        medoid = None
        distances = None
        if ready:
            distances = np.zeros((len(waves),len(waves)))
            for i in range(len(waves)):
                for j in range(i):
                    distances[i,j] = distances[j,i] = dtw_distance(waves[i]['values'],waves[j]['values'])['distance']
            index = int(np.argmin(distances.sum(axis=1)))
            medoid = copy.deepcopy(waves[index])
        references.append({'status':'ready' if ready else 'insufficient_reference', 'context':group['context'],
            'reasons':[] if ready else ['insufficient_confirmed_reference_sessions'],
            'reference_status':'provisional_reference' if ready else 'insufficient_reference',
            'medoid':medoid,'selection':'event_medoid_minimum_total_pairwise_DTW',
            'eligible_session_count':len(group['session_ids']),'contributing_session_ids':group['session_ids'],
            'contributing_event_count':len(waves),'pairwise_distances':distances.tolist() if ready else None})
        if 'source' in group:
            references[-1]['source'] = group['source']
    return {'version':VERSION,'status':'ready' if any(r['status']=='ready' for r in references) else 'insufficient_reference',
            'references':references,'excluded':excluded,'updating':'fixed','waveform_type':WAVEFORM,
            'normalization':'per_event_z_score_population_SD','scalar_reference':'separate_unchanged'}


def compare_waveforms(record, reference):
    if not complete_confirmation(record):
        return {'status':'requires_confirmation','version':VERSION,'reasons':['confirmed_movement_and_activity_required'],'events':[]}
    if (record['context']['confirmed_movement']!=record['confirmation']['confirmed_movement'] or
        record['context']['activity']!=record['confirmation']['confirmed_activity']):
        return {'status':'invalid_input','version':VERSION,'reasons':['incompatible_confirmation_context'],'events':[]}
    if reference is None:
        return {'status':'insufficient_reference','version':VERSION,'reasons':['no_waveform_reference'],'events':[]}
    if record['session_id'] in {sid for ref in reference['references'] for sid in ref['contributing_session_ids']}:
        raise ValueError('Reference/evaluation waveform session overlap')
    match = next((ref for ref in reference['references'] if ref['context']==record['context'] and ref['status']=='ready'),None)
    if match is None:
        return {'status':'insufficient_reference','version':VERSION,'reasons':['no_compatible_confirmed_waveform_reference'],'events':[]}
    events = []
    for event in record['biomechanics']['events']:
        try:
            events.append({'event_id':event['event_id'],**dtw_distance(event['knee_flexion_waveform_rad'],match['medoid']['values'])})
        except ValueError as error:
            events.append({'event_id':event['event_id'],'status':'unavailable','distance':None,'reasons':[str(error)]})
    usable = [e['distance'] for e in events if e['status']=='ready']
    ready = bool(events) and len(usable)==len(events)
    return {'status':'ready' if ready else 'unavailable','version':VERSION,
            'reasons':[] if ready else ['invalid_or_missing_current_waveforms'],'events':events,
            'session_median_distance':float(np.median(usable)) if ready else None,
            'reference_medoid':{'session_id':match['medoid']['session_id'],'event_id':match['medoid']['event_id']},
            'scalar_reference':'separate_unchanged','interpretation':'descriptive; thresholds not established'}
