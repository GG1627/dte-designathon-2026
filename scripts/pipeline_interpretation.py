"""Descriptive downstream view and explicit ACT/VERIFY architectural placeholders."""
import copy

VERSION = 'descriptive-pipeline-interpretation/1.0.0'


def interpretation(record, scalar, waveform, longitudinal, reliability, quality):
    confirmed = record.get('confirmation',{}).get('status')=='confirmed'
    statements = []
    if not confirmed:
        statements.append('Confirm movement and activity before comparing with personal history.')
    for c in scalar.get('comparisons',[]):
        if c['comparison_availability']=='available':
            statements.append(f"{c['side'].capitalize()} {c['metric'].replace('_',' ')} "
                f"is {c['direction'].replace('_',' ')} relative to the confirmed "
                f"{record['confirmation']['confirmed_activity'].replace('_',' ')} / "
                f"{record['confirmation']['confirmed_movement'].replace('_',' ')} reference.")
    for trend in longitudinal:
        if trend['status']=='ready':
            statements.append(f"Session-level EWMA for {trend['metric']} {trend['direction']} across recorded comparable sessions.")
    if any(r['status']=='reliability_not_established' for r in reliability) or not reliability:
        statements.append('Measurement-error thresholds are not empirically established; numerical differences do not establish clinical meaning.')
    return {'status':'ready' if confirmed and quality.get('status')=='ready' else 'requires_confirmation' if not confirmed else 'unavailable',
            'version':VERSION,'reasons':[] if confirmed else ['confirmed_movement_and_activity_required'],
            'confirmed_context':copy.deepcopy(record.get('context')),'statements':statements,
            'scalar_comparison':copy.deepcopy(scalar),'waveform_comparison':copy.deepcopy(waveform),
            'longitudinal_trends':copy.deepcopy(longitudinal),'measurement_reliability':copy.deepcopy(reliability),
            'signal_and_calibration_quality':copy.deepcopy(quality),'medical_inference':False}


def act_verify(context):
    return {'act':{'status':'not_yet_implemented','version':VERSION,'reasons':['no_action_protocol_implemented'],
                   'action_status':'not_yet_implemented'},
            'verify':{'status':'not_yet_implemented','version':VERSION,'reasons':['future_controlled_follow_up_required'],
                      'match_fields':['participant_id','joint','side','activity','confirmed_movement',
                                      'configuration_signature','processing_version','processing_signature'],
                      'target_context':copy.deepcopy(context),'reliability_rules':'same_exact_scope_empirical_MDC_gate',
                      'target_strategy':'explicit_follow_up_goal; do_not_force_return_to_historical_reference'}}
