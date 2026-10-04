"""Conservative movement-pattern candidate detector and explicit activity provenance.

No sport classifier, probabilities, ML, annotations, or generation metadata.
All decision boundaries are configurable engineering heuristics, not validated
physiological thresholds. Non-contact means plantar force below the existing
contact threshold; it is not proof that the athlete was airborne.
"""
import copy
import math
from dataclasses import asdict, dataclass
from statistics import mean, median, pstdev

from biomechanical_events import contact_indices

DETECTOR_VERSION = 'movement-pattern-candidate/0.1.0'
ACTIVITY_TAXONOMY_VERSION = 'activity-context/0.1.0'
ACTIVITIES = {
    'basketball_training': 'Basketball training', 'volleyball_training': 'Volleyball training',
    'soccer_training': 'Soccer training', 'running': 'Running',
    'plyometric_training': 'Plyometric training', 'strength_training': 'Strength training',
    'rehabilitation_session': 'Rehabilitation session', 'other': 'Other',
}
TRUSTED_SOURCES = ('user_confirmed', 'user_corrected', 'manually_selected')
CANDIDATES = {
    'repeated_jump_landing': ['basketball_training', 'volleyball_training', 'plyometric_training'],
    'running_like': ['running', 'soccer_training'],
    'squat_like_repetitions': ['strength_training', 'rehabilitation_session'],
    'low_activity': [], 'unclassified': [],
}


@dataclass(frozen=True)
class DetectorRules:
    contact_threshold_n: float = 20.0  # Existing Kintra contact definition.
    active_velocity_deg_s: float = 5.0
    quiet_gap_s: float = 3.0
    min_repetitions: int = 3
    substantial_rom_deg: float = 15.0
    low_rom_deg: float = 3.0
    min_noncontact_s: float = 0.1
    bilateral_onset_tolerance_s: float = 0.1
    running_max_contact_s: float = 0.35
    max_interval_cv: float = 0.2
    squat_contact_fraction: float = 0.95
    timestamp_abs_tol_s: float = 1e-8  # Existing extraction continuity tolerance.

    def __post_init__(self):
        if type(self.min_repetitions) is not int or self.min_repetitions < 2:
            raise ValueError('At least two repetitions required to describe repetition')
        for name, value in asdict(self).items():
            if name != 'min_repetitions' and (not finite(value) or value <= 0):
                raise ValueError('Detector boundaries must be positive finite numbers')
        if self.squat_contact_fraction > 1 or self.low_rom_deg >= self.substantial_rom_deg:
            raise ValueError('Invalid fraction or excursion boundaries')


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def confirmation(activity=None, source=None):
    if activity is None:
        return {'status': 'unconfirmed', 'confirmed_activity': None, 'source': source}
    if not isinstance(activity, str) or not activity.strip() or source not in TRUSTED_SOURCES:
        raise ValueError('Activity selection requires an explicit trusted provenance source')
    return {'status': 'confirmed', 'confirmed_activity': activity, 'source': source}


def declared_context(activity):
    """Explicit manual task selection in legacy SYNTHETIC demos, not detector inference."""
    return {'detected_movement': None, 'activity_taxonomy_version': ACTIVITY_TAXONOMY_VERSION,
            'confirmation': confirmation(activity, 'manually_selected')}


def confirmed_activity(session):
    metadata = session.get('metadata', session.get('baseline_demo', {}))
    ctx = metadata.get('activity_context', {})
    record = ctx.get('confirmation', {})
    value = record.get('confirmed_activity')
    if (record.get('status') != 'confirmed' or record.get('source') not in TRUSTED_SOURCES
            or not isinstance(value, str) or not value.strip()):
        return None
    # Whole-session summaries cannot be assigned to conflicting/unconfirmed episodes.
    if any(e.get('confirmation', {}).get('confirmed_activity') != value
           or e.get('confirmation', {}).get('status') != 'confirmed'
           or e.get('confirmation', {}).get('source') not in TRUSTED_SOURCES
           for e in ctx.get('episodes', [])):
        return None
    return value


def with_activity_confirmation(session, activity, source='user_confirmed', detection=None):
    """Return a COPY: change only context/provenance, never signals or event metrics.

    Selection applies to the entire session; all detected episodes get the same
    user-selected context. Mixed-context sessions require future episode metrics.
    """
    result = copy.deepcopy(session)
    metadata = result.setdefault('metadata' if 'event_metrics' in result else 'baseline_demo', {})
    old = metadata.get('activity_context', {})
    ctx = copy.deepcopy(detection if detection is not None else old)
    history = copy.deepcopy(old.get('confirmation_history', []))
    if old.get('confirmation'):
        history.append(copy.deepcopy(old['confirmation']))
    record = confirmation(activity, source)
    ctx.update(confirmation=record, confirmation_history=history,
               activity_taxonomy_version=ACTIVITY_TAXONOMY_VERSION)
    for episode in ctx.get('episodes', []):
        episode['confirmation'] = copy.deepcopy(record)
    metadata['activity_context'] = ctx
    if 'context' in result:  # Previously extracted metrics: rematch context without recomputing.
        result['context']['activity'] = activity
    return result


def contact_intervals(rows, side, rules):
    """Only complete onset-to-offset contacts; boundary-truncated stance is excluded."""
    return contact_indices(rows, side, rules.contact_threshold_n)


def describe_episode(rows, index, rules, invalid=False):
    start, end = rows[0].get('timestamp_s'), rows[-1].get('timestamp_s')
    episode = {'episode_id': f'episode_{index}', 'start_s': start if finite(start) else None,
               'end_s': end if finite(end) else None, 'detector_version': DETECTOR_VERSION,
               'activity_taxonomy_version': ACTIVITY_TAXONOMY_VERSION,
               'confirmation': confirmation(source='detector_only'), 'features': {}, 'reasons': []}
    movement = 'unclassified'
    if invalid:
        episode['reasons'] = ['invalid_or_discontinuous_processed_signals']
        episode['features'] = {'event_count': None, 'duration_s': None,
                               'median_knee_rom_deg': None, 'median_peak_angular_velocity_deg_s': None,
                               'median_contact_time_s': None}
    else:
        contacts = {side: contact_intervals(rows, side, rules) for side in ('left', 'right')}
        angles = {side: [math.degrees(row[side]['knee']['flexion_rad']) for row in rows]
                  for side in contacts}
        velocities = {side: [math.degrees(row[side]['knee']['angular_velocity_rad_s']) for row in rows]
                      for side in contacts}
        ranges = [max(v) - min(v) for v in angles.values()]
        peak_velocity = max(abs(v) for values in velocities.values() for v in values)
        motion_peaks = {side: sum(a > rules.active_velocity_deg_s and b <= rules.active_velocity_deg_s
                                 and angles[side][i] - min(angles[side]) >= rules.substantial_rom_deg
                                 for i, (a, b) in enumerate(zip(v, v[1:])))
                        for side, v in velocities.items()}
        onsets = sorted((rows[a]['timestamp_s'], side) for side, items in contacts.items() for a, _ in items)
        durations = [rows[b]['timestamp_s'] - rows[a]['timestamp_s']
                     for items in contacts.values() for a, b in items]
        pairs = sum(any(abs(rows[a]['timestamp_s'] - rows[b]['timestamp_s'])
                        <= rules.bilateral_onset_tolerance_s for b, _ in contacts['right'])
                    for a, _ in contacts['left'])
        gaps = [rows[b]['timestamp_s'] - rows[a]['timestamp_s']
                for side in contacts for (_, a), (b, _) in zip(contacts[side], contacts[side][1:])]
        both_noncontact = sum(all(row[side]['insole']['plantar_normal_force_n'] <= rules.contact_threshold_n
                                  for side in contacts) for row in rows) / len(rows)
        supported_fraction = sum(all(row[side]['insole']['plantar_normal_force_n'] > rules.contact_threshold_n
                                    for side in contacts) for row in rows) / len(rows)
        steps = [b[0] - a[0] for a, b in zip(onsets, onsets[1:])]
        interval_cv = pstdev(steps) / mean(steps) if steps and mean(steps) > 0 else None
        roms = [max(angles[side][a:b]) - min(angles[side][a:b])
                for side in contacts for a, b in contacts[side]]
        noncontact_runs, onset = [], None
        for i, row in enumerate(rows):
            clear = all(row[side]['insole']['plantar_normal_force_n'] <= rules.contact_threshold_n
                        for side in contacts)
            if clear and onset is None:
                onset = i
            elif not clear and onset is not None:
                if onset > 0:  # Count only complete intervals between contacts.
                    noncontact_runs.append(row['timestamp_s'] - rows[onset]['timestamp_s'])
                onset = None
        event_count = min(len(contacts[side]) for side in contacts)
        episode['features'] = {
            'event_count': event_count, 'duration_s': end - start,
            'median_knee_rom_deg': median(roms) if roms else median(ranges),
            'median_peak_angular_velocity_deg_s': median(
                max(abs(v) for v in velocities[side][a:b]) for side in contacts for a, b in contacts[side])
                if roms else median(max(abs(v) for v in values) for values in velocities.values()),
            'median_contact_time_s': median(durations) if durations else None,
            'bilateral_contact_pair_count': pairs, 'bilateral_noncontact_fraction': both_noncontact,
            'bilateral_supported_fraction': supported_fraction,
            'minimum_noncontact_gap_s': min(gaps) if gaps else None,
            'minimum_bilateral_noncontact_s': min(noncontact_runs) if noncontact_runs else None,
            'onset_interval_cv': interval_cv, 'knee_repetition_count': min(motion_peaks.values()),
        }
        substantial = min(ranges) >= rules.substantial_rom_deg
        if max(ranges) <= rules.low_rom_deg and peak_velocity <= rules.active_velocity_deg_s:
            movement = 'low_activity'
        elif (event_count >= rules.min_repetitions and pairs >= rules.min_repetitions
              and substantial and gaps and min(gaps) >= rules.min_noncontact_s
              and noncontact_runs and min(noncontact_runs) >= rules.min_noncontact_s):
            movement = 'repeated_jump_landing'
        elif (len(onsets) >= 2 * rules.min_repetitions and substantial and durations
              and max(durations) <= rules.running_max_contact_s and interval_cv is not None
              and interval_cv <= rules.max_interval_cv
              and all(a[1] != b[1] and b[0] - a[0] > rules.bilateral_onset_tolerance_s
                      for a, b in zip(onsets, onsets[1:]))):
            movement = 'running_like'
        elif (min(motion_peaks.values()) >= rules.min_repetitions and substantial
              and supported_fraction >= rules.squat_contact_fraction and not onsets):
            movement = 'squat_like_repetitions'
    episode.update(detected_movement=movement,
                   detector_status='candidate' if movement not in ('unclassified', 'low_activity') else movement,
                   candidate_activities=CANDIDATES[movement][:])
    return episode


def detect_movement_episodes(processed, rules=DetectorRules()):
    """Read samples/rate only. Group active samples separated by <= quiet_gap_s.

    Conservative invalid-data policy: return unclassified instead of repairing.
    Segment boundaries retain one neighboring sample for contact transitions.
    """
    rows = processed.get('samples', [])
    rate = processed.get('sampling', {}).get('rate_hz')
    result = {'detector_version': DETECTOR_VERSION, 'activity_taxonomy_version': ACTIVITY_TAXONOMY_VERSION,
              'description': 'movement-pattern candidate detector', 'validated_classifier': False,
              'decision_boundaries': asdict(rules), 'confirmation': confirmation(source='detector_only'), 'episodes': []}
    if not rows:
        return result
    valid = len(rows) >= 2 and finite(rate) and rate > 0
    for i, row in enumerate(rows):
        valid &= finite(row.get('timestamp_s')) and type(row.get('sequence')) is int
        if i and valid:
            valid &= row['sequence'] == rows[i-1]['sequence'] + 1 and math.isclose(
                row['timestamp_s'] - rows[i-1]['timestamp_s'], 1 / rate,
                rel_tol=0, abs_tol=rules.timestamp_abs_tol_s)
        for side in ('left', 'right'):
            for label, keys in (('knee', ('flexion_rad', 'angular_velocity_rad_s')),
                                ('insole', ('plantar_normal_force_n',))):
                signal = row.get(side, {}).get(label, {})
                valid &= signal.get('quality', {}).get('valid') is True and all(finite(signal.get(k)) for k in keys)
                valid &= finite(signal.get('timestamp_s', row.get('timestamp_s')))
                if valid:
                    valid &= abs(signal.get('timestamp_s', row['timestamp_s']) - row['timestamp_s']) <= rules.timestamp_abs_tol_s
                    if label == 'insole':
                        valid &= signal['plantar_normal_force_n'] >= 0
    if not valid:
        result['episodes'] = [describe_episode(rows, 1, rules, invalid=True)]
        return result
    active = [i for i, row in enumerate(rows) if any(
        abs(math.degrees(row[side]['knee']['angular_velocity_rad_s'])) > rules.active_velocity_deg_s
        or row[side]['insole']['plantar_normal_force_n'] > rules.contact_threshold_n
        for side in ('left', 'right'))]
    groups = []
    for index in active:
        if not groups or rows[index]['timestamp_s'] - rows[groups[-1][-1]]['timestamp_s'] > rules.quiet_gap_s:
            groups.append([])
        groups[-1].append(index)
    segments = [rows[max(0, g[0]-1):min(len(rows), g[-1]+2)] for g in groups] if groups else [rows]
    result['episodes'] = [describe_episode(segment, i, rules) for i, segment in enumerate(segments, 1)]
    return result
