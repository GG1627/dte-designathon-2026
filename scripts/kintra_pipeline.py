"""Canonical modular Kintra software pipeline; no hardware/clinical validation.

Legacy annotated-window analyzers remain separate. Legacy inputs are ONE knee
pair and BOTH feet; explicit sensor configuration enables bilateral orchestration.
Every stage carries status, version, provenance, reasons.
"""
import copy
from dataclasses import dataclass, field

from signal_preprocessing import FilterConfig, validate_signals, preprocess, PROFILES, finite
from sensor_to_segment_calibration import calibrate_pair, VERSION as CALIBRATION_VERSION
from aligned_kinematics import orientations, reconstruct, VERSION as KINEMATICS_VERSION
from biomechanical_events import EventProtocol, extract_events
from event_biomechanics import event_metrics
from activity_windows import WindowConfig, window_predictions
from athlete_confirmation import confirm_record
from contextual_reference import context_key, compare_personal_reference
from waveform_similarity import compare_waveforms
from longitudinal_monitoring import EWMAConfig, session_ewma
from measurement_reliability import measurement_change_reliability
from pipeline_interpretation import interpretation, act_verify

VERSION = 'kintra-modular-pipeline/1.0.0'
STAGES = ('input_quality','filtering','orientation','calibration','kinematics','events',
          'activity_features','activity_svm','temporal_model','confirmation','biomechanics',
          'personal_reference','waveform_reference','waveform_comparison','longitudinal',
          'spc','reliability','interpretation','act','verify')


@dataclass(frozen=True)
class PipelineConfig:
    side: str = 'right'
    profile: str = 'imu_pair_plus_insole'
    filter: FilterConfig = field(default_factory=FilterConfig)
    window: WindowConfig = field(default_factory=WindowConfig)
    event_protocol: EventProtocol = field(default_factory=EventProtocol)
    beta: float = .1
    calibration_records: dict | None = None
    movement_model: object = None
    temporal_model: object = None
    confirmed_movement: str | None = None
    confirmed_activity: str | None = None
    movement_source: str | None = None
    activity_source: str | None = None
    scalar_reference: dict | None = None
    waveform_reference: dict | None = None
    chronological_index: int = 1
    longitudinal_history: tuple = ()
    ewma_lambda: float = .3
    trend_metric: str = 'right_peak_plantar_normal_force_bw'
    reliability_evidence: tuple = ()
    acquisition_context: dict = field(default_factory=dict)
    sensor_configuration: object = None
    side_options: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.side not in ('left','right') or self.profile not in PROFILES:
            raise ValueError('One monitored knee side and explicit supported sensor profile required')
        if not finite(self.beta) or self.beta < 0 or not finite(self.ewma_lambda) or not 0 < self.ewma_lambda <= 1:
            raise ValueError('Finite nonnegative beta and EWMA factor in (0,1] required')
        if type(self.chronological_index) is not int or self.chronological_index < 1:
            raise ValueError('Positive explicit chronological index required')
        if self.sensor_configuration is not None:
            from sensor_configuration import SensorConfiguration
            if not isinstance(self.sensor_configuration, SensorConfiguration):
                raise ValueError('Explicit SensorConfiguration required')
        if set(self.side_options)-{'left','right'}:
            raise ValueError('Side options must be keyed by left/right')


def stage(payload, provenance='module_output'):
    result = copy.deepcopy(payload)
    result.setdefault('version',VERSION)
    result.setdefault('reasons',[])
    result.setdefault('provenance',provenance)
    return result


def unavailable(reason, status='unavailable'):
    return stage({'status':status,'reasons':[reason]})


def run_pipeline(raw_session, config=PipelineConfig()):
    """Legacy contract is unchanged; explicit sensors select bilateral schema v2."""
    if config.sensor_configuration is not None:
        from bilateral_pipeline import run_bilateral_pipeline
        return run_bilateral_pipeline(raw_session, config)
    return _run_knee_pipeline(raw_session, config)


def _run_knee_pipeline(raw_session, config, *, measurement_sources=None, sensor_scope=None):
    """The same per-side worker serves legacy, bilateral and single-knee modes."""
    output = {'version':VERSION,'session_id':raw_session.get('session_id'),
              'synthetic':raw_session.get('synthetic') is True,
              'sensor_profile':config.profile,'monitored_knee_side':config.side,
              'stages':{name:unavailable('upstream_not_available') for name in STAGES},'record':None}
    stages = output['stages']
    stages.update(act_verify(None))
    stages['act'],stages['verify'] = stage(stages['act']),stage(stages['verify'])
    quality = validate_signals(raw_session,config.side,config.profile)
    if not isinstance(raw_session.get('participant',{}).get('id'),str) or not raw_session['participant']['id'].strip():
        quality = {**quality,'status':'invalid_input','reasons':[*quality['reasons'],'participant_identity_required']}
    stages['input_quality'] = stage(quality,'raw_measurements; no_interpolation')
    if quality['status']!='ready':
        return output
    try:
        filtered,_ = preprocess(raw_session,config.filter,config.side,config.profile)
        stages['filtering'] = stage({'status':'ready','config':config.filter.metadata()})
    except (ValueError,TypeError) as error:
        stages['filtering'] = unavailable(str(error),'invalid_input')
        return output
    try:
        raw_orientation = orientations(filtered,config.side,beta=config.beta)
        stages['orientation'] = stage({'status':'ready','method':'existing_Madgwick_6DOF_wxyz',
            'beta':config.beta,'beta_provenance':'existing_ideal_synthetic_beta',
            'sample_count':len(raw_orientation),'initialization':'stationary_tilt; common_zero_yaw',
            'raw_sensor_orientations_retained':True})
    except (ValueError,TypeError,KeyError) as error:
        stages['orientation'] = unavailable(str(error),'invalid_input')
        return output
    if config.calibration_records is None:
        stages['calibration'] = unavailable('static_and_positive_functional_sweep_required','calibration_required')
        return output
    try:
        calibration = calibrate_pair(config.calibration_records)
        stages['calibration'] = stage({'status':'ready','version':CALIBRATION_VERSION,
                                      'segments':calibration,'hardware_validated':False})
        processed = reconstruct(filtered,calibration,config.side,config.beta,raw_orientation)
        stages['kinematics'] = stage({'status':'ready','version':KINEMATICS_VERSION,
                                     'processing':processed['processing'],'samples':processed['samples']})
    except (ValueError,TypeError,KeyError) as error:
        stages['calibration'] = unavailable(str(error),'calibration_required')
        return output
    events = extract_events(processed,config.event_protocol) if config.profile=='imu_pair_plus_insole' else {
        'status':'unavailable','reasons':['insole_contact_events_unavailable_in_imu_pair_only'],
        'contacts':[],'landings':[]}
    stages['events'] = stage(events)
    biomechanics = event_metrics(processed,events)
    stages['biomechanics'] = stage(biomechanics)
    model_history = {'episode_svm':None,'window_svm':None,'window_hmm':None}
    if config.movement_model is None:
        stages['activity_svm'] = unavailable('trained_movement_model_required')
        stages['activity_features'] = unavailable('trained_movement_model_required')
    elif config.movement_model.config.profile!=config.profile:
        stages['activity_svm'] = unavailable('movement_model_sensor_profile_mismatch','invalid_input')
        stages['activity_features'] = unavailable('movement_model_sensor_profile_mismatch','invalid_input')
    else:
        try:
            episode = config.movement_model.predict(processed,events if config.profile=='imu_pair_plus_insole' else None,
                                                     config.event_protocol)
            windows = window_predictions(processed,config.movement_model,config.window,config.event_protocol)
            stages['activity_features'] = stage({'status':'ready',**episode['features']})
            stages['activity_svm'] = stage({'status':'ready','episode':episode,'windowed':windows,
                                           'model_metadata':config.movement_model.metadata})
            model_history.update(episode_svm=episode,window_svm=windows)
            if config.temporal_model is not None:
                temporal = config.temporal_model.smooth(windows)
                stages['temporal_model'] = stage(temporal)
                model_history['window_hmm'] = temporal
            else:
                stages['temporal_model'] = unavailable('trained_temporal_model_required')
        except (ValueError,TypeError,KeyError) as error:
            stages['activity_svm'] = unavailable(str(error))
            stages['activity_features'] = unavailable(str(error))
    record = {'session_id':raw_session['session_id'],'synthetic':output['synthetic'],
              'participant_id':raw_session['participant']['id'],'side':config.side,
              'chronological_index':config.chronological_index,
              'biomechanics':biomechanics,'model_history':model_history}
    if measurement_sources is not None:
        record['measurement_sources'] = copy.deepcopy(measurement_sources)
    mass = raw_session['participant'].get('mass_kg')
    record['body_weight_n'] = mass*9.80665 if finite(mass) and mass>0 else None
    record = confirm_record(record,config.confirmed_movement,config.confirmed_activity,
                            config.movement_source,config.activity_source)
    stages['confirmation'] = stage({**record['confirmation'],'reasons':[] if record['confirmation']['status']=='confirmed'
                                   else ['confirmed_movement_and_activity_required']})
    if stages['confirmation']['status']=='confirmed': stages['confirmation']['status']='ready'
    sources = raw_session.get('sources',{})
    sensor_configuration = {'profile':config.profile,'monitored_knee_side':config.side,
        'sources':{'knee_imu_pair':copy.deepcopy(sources.get(config.side,{}).get('knee')),
                   'insoles':{foot:sources.get(foot,{}).get('insole') for foot in ('left','right')}
                             if config.profile=='imu_pair_plus_insole' else None},
        'sampling':{key:raw_session['sampling'].get(key)
            for key in ('rate_hz','clock','synchronization_uncertainty_s')},
        'insole_geometry':copy.deepcopy(raw_session.get('insole_geometry')) if config.profile=='imu_pair_plus_insole' else None,
        'acquisition_context':copy.deepcopy(config.acquisition_context)}
    if measurement_sources is not None:
        sensor_configuration['measurement_sources'] = copy.deepcopy(measurement_sources)
        sensor_configuration['declared_sensors'] = copy.deepcopy(sensor_scope)
    processing_configuration = {'version':VERSION,'filter':config.filter.metadata(),
        'kinematics':processed['processing'],'calibration_version':CALIBRATION_VERSION,
        'calibration_protocol':'upright_static_plus_signed_positive_functional_sweep',
        'events':events.get('protocol'),'event_method':'canonical_contact_window'}
    record['context'] = context_key(record,sensor_configuration,processing_configuration)
    record['sensor_configuration'] = sensor_configuration
    record['processing_configuration'] = processing_configuration
    scalar = compare_personal_reference(record,config.scalar_reference)
    stages['personal_reference'] = stage(scalar)
    stages['waveform_reference'] = stage({'status':config.waveform_reference['status'],
        'version':config.waveform_reference['version'],'updating':'fixed'}) if config.waveform_reference else unavailable('no_waveform_reference','insufficient_reference')
    if measurement_sources is not None:
        stages['waveform_reference']['reference_sources'] = [
            {'context':copy.deepcopy(ref['context']),'source':ref.get('source','unavailable')}
            for ref in config.waveform_reference.get('references',[])] if config.waveform_reference else []
    waveform = compare_waveforms(record,config.waveform_reference)
    stages['waveform_comparison'] = stage(waveform)
    record['waveform_comparison'] = waveform
    trends = []
    if record['confirmation']['status']=='confirmed':
        try:
            observations = []
            for session in (*config.longitudinal_history,record):
                value = session.get('waveform_comparison',{}).get('session_median_distance') if config.trend_metric=='knee_flexion_dtw_distance' else session['biomechanics']['session_metrics'].get(config.trend_metric)
                observations.append({'session_id':session['session_id'],'chronological_index':session['chronological_index'],
                    'context':session['context'],'value':value,
                    'status':'ready' if session.get('confirmation',{}).get('status')=='confirmed' and finite(value) else 'unavailable'})
            trend = session_ewma(observations,EWMAConfig(config.ewma_lambda,config.trend_metric,record['context']))
            trends.append(trend)
            stages['longitudinal'] = stage(trend)
        except (ValueError,KeyError) as error:
            stages['longitudinal'] = unavailable(str(error),'invalid_input')
    else:
        stages['longitudinal'] = unavailable('confirmed_movement_and_activity_required','requires_confirmation')
    stages['spc'] = stage({'status':'unavailable','spc_status':'reference_limits_not_established',
                          'reasons':['empirical_reference_limits_not_established'],'athlete_alarm':None})
    reliability = []
    for c in scalar.get('comparisons',[]):
        evidence = next((r for r in config.reliability_evidence if r.get('metric')==c['metric'] and r.get('context',{}).get('side')==c['side']),None)
        # Foot-loading side is metric-specific; monitored knee remains recorded separately.
        scope = {**record['context'],'side':c['side']}
        reliability.append(measurement_change_reliability(c['evaluation_median'],c['reference_median'],
                                                         c['metric'],c['unit'],scope,evidence))
    stages['reliability'] = stage({'status':'ready' if reliability and all(r['status']=='ready' for r in reliability)
                                 else 'reliability_not_established','results':reliability,
                                 'reasons':[] if reliability and all(r['status']=='ready' for r in reliability)
                                            else ['empirically_established_matching_MDC_unavailable'],
                                 'change_exceeds_measurement_error':None})
    stages['interpretation'] = stage(interpretation(record,scalar,waveform,trends,reliability,{'status':'ready',
        'input_quality':quality,'calibration':calibration,
        'limitations':'restricted_sagittal_model; hardware_not_validated; sources_explicit' if measurement_sources is not None
                      else 'synthetic; restricted_sagittal_model'}))
    stages.update({key:stage(value) for key,value in act_verify(record['context']).items()})
    output['record'] = record
    return output
