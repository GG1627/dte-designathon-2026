"""Fail-closed MDC gate; variability statistics are never measurement error."""
import copy
from signal_preprocessing import finite

VERSION = 'empirical-mdc-gate/1.0.0'
SCOPE = ('joint','side','activity','confirmed_movement','configuration_id',
         'configuration_signature','processing_version','processing_signature')


def measurement_change_reliability(current, reference, metric, unit, context, reliability=None):
    output = {'status':'reliability_not_established','version':VERSION,
              'metric':metric,'unit':unit,'change_exceeds_mdc':None,'mdc':None,
              'reasons':['empirically_established_matching_MDC_unavailable'],
              'interpretation':'no conclusion about measurement error or clinical meaning'}
    evidence = reliability or {}
    scoped = evidence.get('context',{})
    if (evidence.get('empirically_established') is not True or not isinstance(evidence.get('source'),str)
        or not evidence['source'].strip() or evidence.get('metric')!=metric or evidence.get('unit')!=unit
        or not finite(evidence.get('mdc')) or evidence['mdc']<=0 or
        any(context.get(k) is None or scoped.get(k)!=context[k] for k in SCOPE)):
        return output
    if not finite(current) or not finite(reference):
        return {**output,'status':'unavailable','reasons':['current_or_reference_metric_unavailable']}
    return {**output,'status':'ready','change_exceeds_mdc':abs(current-reference)>evidence['mdc'],
            'mdc':evidence['mdc'],'absolute_change':abs(current-reference),'reasons':[],
            'evidence':copy.deepcopy(evidence),
            'interpretation':'descriptive comparison with supplied empirical MDC; no clinical or injury inference'}
