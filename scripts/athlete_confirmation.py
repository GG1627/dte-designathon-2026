"""Explicit two-part athlete context; predictions never grant confirmation."""
import copy

VERSION = 'athlete-movement-activity-confirmation/1.0.0'
TRUSTED = ('user_confirmed','user_corrected','manually_selected')


def confirmation_record(movement=None, activity=None, movement_source=None, activity_source=None):
    for value,source in ((movement,movement_source),(activity,activity_source)):
        if value is not None and (not isinstance(value,str) or not value.strip() or source not in TRUSTED):
            raise ValueError('A selection requires a nonempty value and explicit athlete provenance')
    complete = movement is not None and activity is not None
    return {'status':'confirmed' if complete else 'requires_confirmation',
            'confirmed_movement':movement,'confirmed_activity':activity,
            'movement_source':movement_source,'source':activity_source,
            'version':VERSION,'provenance':'explicit_athlete_selection; demo selections are scripted'}


def confirmed_movement(session):
    metadata = session.get('metadata',session.get('baseline_demo',{}))
    record = metadata.get('activity_context',{}).get('confirmation',{})
    value = record.get('confirmed_movement')
    if (record.get('status')!='confirmed' or record.get('movement_source') not in TRUSTED or
        not isinstance(value,str) or not value.strip()):
        return None
    return value


def confirm_record(record,movement=None,activity=None,movement_source=None,activity_source=None):
    """Copy metrics and all model output unchanged; append previous selection history."""
    result = copy.deepcopy(record)
    history = result.setdefault('confirmation_history',[])
    if 'confirmation' in result:
        history.append(copy.deepcopy(result['confirmation']))
    result['confirmation'] = confirmation_record(movement,activity,movement_source,activity_source)
    if 'context' in result:
        complete = result['confirmation']['status']=='confirmed'
        result['context'].update(activity=activity if complete else None,
                                 confirmed_activity=activity if complete else None,
                                 confirmed_movement=movement if complete else None)
    return result
