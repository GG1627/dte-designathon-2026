"""Side orchestration above the existing reusable knee worker (schema v2).

One designated knee supplies the UNCHANGED SVM/HMM feature representation.
Foot contacts/metrics are independent of either knee's presence or calibration.
"""
import copy
from dataclasses import replace

from sensor_configuration import SIDES, combined_source, source_reasons
from signal_preprocessing import validate_signals
from biomechanical_events import extract_events
from event_biomechanics import plantar_metrics
from bilateral_comparison import compare_knees, compare_plantar
from athlete_confirmation import confirmation_record
from pipeline_interpretation import act_verify

SCHEMA_VERSION = 'kintra-bilateral-session/2.0.0'


def annotate_measurements(knee, sources):
    """Provenance additions only; measurements and estimator arithmetic unchanged."""
    foot_stages = ('activity_features','activity_svm','temporal_model','events','biomechanics','personal_reference','reliability','interpretation')
    for name,value in knee.items():
        if isinstance(value,dict) and 'status' in value:
            value['source'] = combined_source([sources['knee'],*sources['insoles'].values()]) if name in foot_stages else sources['knee']
            value['measurement_sources'] = copy.deepcopy(sources)
    biomech = knee['biomechanics']
    for row in knee['kinematics'].get('samples',[]):
        row[knee['input_quality']['monitored_knee_side']]['knee']['source'] = sources['knee']
    biomech['metric_sources'] = {name:sources['knee'] if name=='knee_rom_rad' else
        sources['insoles']['left' if name.startswith('left_') else 'right']
        for name in biomech.get('session_metrics',{})}
    for event in biomech.get('events',[]):
        event['kinematics']['source'] = sources['knee']
        event['waveform_source'] = sources['knee']
        for side in SIDES:
            for name in ('loading','pressure'):
                event[name][side]['source'] = sources['insoles'][side]
    if knee.get('record') is not None:
        knee['record']['biomechanics'] = copy.deepcopy(biomech)
        knee['record']['metric_sources'] = copy.deepcopy(biomech['metric_sources'])
        reference_sources = knee['waveform_reference'].get('reference_sources',[])
        knee['waveform_reference']['source'] = combined_source([r['source'] for r in reference_sources]) if reference_sources else 'unavailable'
        knee['waveform_comparison']['source'] = sources['knee']
        knee['waveform_comparison']['reference_source'] = next((r['source'] for r in reference_sources
            if r['context']==knee['record']['context']),None)
        metric = knee['longitudinal'].get('metric','knee_rom_rad')
        knee['longitudinal']['source'] = sources['knee'] if metric.startswith('knee_') else sources['insoles']['left' if metric.startswith('left_') else 'right']


def run_bilateral_pipeline(raw, config):
    from kintra_pipeline import _run_knee_pipeline, STAGES, stage, unavailable

    sensors = config.sensor_configuration
    metadata = sensors.metadata()
    insoles = {}
    for side in SIDES:
        sensor = sensors.insoles[side]
        output = {'session_id':raw.get('session_id'),'source':sensor.source,'sensor':metadata['insoles'][side],'events':[],
                  'status':'unavailable','reasons':[f'{side}_insole_not_present']}
        if sensor.present:
            quality = validate_signals(raw,profile='imu_pair_plus_insole',knee_required=False,feet=(side,))
            packets = [row.get(side,{}).get('insole',{}) for row in raw.get('samples',[])]
            reasons = quality['reasons'] + source_reasons(raw,sensor,packets,raw.get('sources',{}).get(side,{}).get('insole'))
            if reasons:
                output.update(status='invalid_input',reasons=sorted(set(reasons)))
                if any('source' in r or 'labeled_hardware' in r for r in reasons):
                    output['source'] = 'unavailable'
            else:
                events = extract_events(raw,config.event_protocol,knee_required=False,feet=(side,))
                output.update(plantar_metrics(raw,events,side),input_quality=stage(quality),contact_events=stage(events))
            for event in output['events']:
                event['measurement_source'] = sensor.source
                event['loading']['source'] = event['pressure']['source'] = sensor.source
        insoles[side] = output
    foot_ready = all(insoles[s].get('input_quality',{}).get('status')=='ready' for s in SIDES)
    foot_events = extract_events(raw,config.event_protocol,knee_required=False) if foot_ready else {'bilateral_pairs':[]}
    knees = {}
    for side in SIDES:
        pair = sensors.knees[side]
        source = combined_source([pair.thigh.source,pair.shank.source]) if pair.present else 'unavailable'
        sources = {'knee':source,'segments':{segment:getattr(pair,segment).source for segment in ('thigh','shank')},
                   'insoles':{foot:insoles[foot]['source'] for foot in SIDES}}
        options = config.side_options.get(side,{})
        if set(options) & {'side','profile','sensor_configuration','side_options','movement_model','temporal_model'}:
            raise ValueError('Side options cannot change orchestration or recognition strategy')
        defaults = {'trend_metric':'knee_rom_rad',**options}
        local = replace(config,side=side,profile='imu_pair_plus_insole' if foot_ready else 'imu_pair_only',
                        sensor_configuration=None,side_options={},
                        movement_model=config.movement_model if side==config.side else None,
                        temporal_model=config.temporal_model if side==config.side else None,**defaults)
        reasons = []
        if not pair.present:
            reasons = [f'{side}_knee_not_instrumented']
        else:
            ids = raw.get('sources',{}).get(side,{}).get('knee',[])
            for index,segment in enumerate(('thigh','shank')):
                packets = [row.get(side,{}).get('imu',{}).get(segment,{}) for row in raw.get('samples',[])]
                reasons.extend(source_reasons(raw,getattr(pair,segment),packets,ids[index] if len(ids)>index else None))
        scope = {'mode':sensors.mode,'knee':metadata['knees'][side],
                 'insoles':metadata['insoles'],'knee_protocol':sensors.knee_protocols[side]}
        if reasons:
            stages = {name:unavailable(reasons[0]) for name in STAGES}
            stages['input_quality'] = stage({'status':'invalid_input' if pair.present else 'unavailable','reasons':sorted(set(reasons))})
            record = None
            if pair.present:
                source = sources['knee'] = 'unavailable'
                sources['segments'] = {s:'unavailable' for s in ('thigh','shank')}
        else:
            result = _run_knee_pipeline(raw,local,measurement_sources=sources,sensor_scope=scope)
            stages,record = result['stages'],result['record']
        state = 'ready' if stages['kinematics']['status']=='ready' else (
            'invalid_input' if stages['input_quality']['status']=='invalid_input' or stages['filtering']['status']=='invalid_input'
            or stages['orientation']['status']=='invalid_input' else
            'calibration_required' if stages['calibration']['status']=='calibration_required' else 'unavailable')
        knee = {'status':state,'source':source,'sensors':metadata['knees'][side],
                'reasons':[] if state=='ready' else sorted(set(reasons or next(
                    (stages[name]['reasons'] for name in ('input_quality','filtering','orientation','calibration','kinematics')
                     if stages[name]['status'] not in ('ready','unavailable')),['upstream_not_available']))),
                **stages,'record':record,
                'comparison_configuration':{'mode':sensors.mode,'sampling':copy.deepcopy(raw.get('sampling')),
                    'acquisition_context':copy.deepcopy(local.acquisition_context),
                    'knee_protocol':sensors.knee_protocols[side],'segment_sources':sources['segments']}}
        annotate_measurements(knee,sources)
        knees[side] = knee
    bilateral = {'knee_kinematics':compare_knees(knees,foot_events['bilateral_pairs']),
                 'plantar_loading':compare_plantar(insoles,foot_events['bilateral_pairs'])}
    designated = knees[config.side]
    confirmation = confirmation_record(config.confirmed_movement,config.confirmed_activity,
                                       config.movement_source,config.activity_source)
    statements = [statement for side in SIDES for statement in knees[side]['interpretation'].get('statements',[])]
    loading = bilateral['plantar_loading']
    if loading['status']=='ready':
        signed = loading['metrics']['peak_plantar_normal_force_n']['signed_difference_right_minus_left']
        qualifier = 'simulated insole demo' if loading['source']=='synthetic_demo' else f"{loading['source']} insole comparison"
        statements.append(f"Right plantar loading is {'higher than' if signed>0 else 'lower than' if signed<0 else 'equal to'} left plantar loading in this {qualifier}.")
    statements.append('Measurement-error thresholds are not empirically established; differences have no established clinical meaning.')
    return {'schema_version':SCHEMA_VERSION,'version':SCHEMA_VERSION,'session_id':raw.get('session_id'),
        'synthetic':raw.get('synthetic') is True,'configuration':metadata,
        'contains_synthetic_measurements':any(sensor.source=='synthetic_demo' for sensor in sensors.insoles.values())
            or any(sensor.source=='synthetic_demo' for pair in sensors.knees.values() for sensor in (pair.thigh,pair.shank)),
        'input_quality':{'status':'ready' if all(knees[s]['status']=='ready' for s in SIDES if sensors.knees[s].present)
            and foot_ready else 'partial','knees':{s:knees[s]['input_quality'] for s in SIDES},
            'insoles':{s:{'status':insoles[s]['status'],'reasons':insoles[s]['reasons']} for s in SIDES}},
        'knees':knees,'insoles':insoles,
        'activity':{'motion_source_side':config.side,'feature_strategy':'one_designated_knee_plus_bilateral_feet_unchanged',
            'svm':designated['activity_svm'],'temporal':designated['temporal_model'],'confirmation':confirmation},
        'bilateral':bilateral,'interpretation':{
            'status':'requires_confirmation' if confirmation['status']!='confirmed' else 'ready' if
                any(knees[s]['status']=='ready' or insoles[s]['status']=='ready' for s in SIDES) else 'unavailable',
            'statements':list(dict.fromkeys(statements)),
            'per_side':{s:knees[s]['interpretation'] for s in SIDES},
            'sources':{s:knees[s]['record'].get('measurement_sources') if knees[s]['record'] else None for s in SIDES},
            'medical_inference':False},**act_verify(designated['record']['context'] if designated['record'] else None)}
