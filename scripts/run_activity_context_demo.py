"""Generate offline judge choices using one signal episode and Python reference matching."""
import json
from pathlib import Path

from activity_context import ACTIVITIES, detect_movement_episodes, with_activity_confirmation
from baseline_simulation import (compare_evaluations, evaluation_fixture, extract_session,
                                 fit_baseline, generate_reference_history, summarize_session)
from generate_raw_sensor_fixture import generate_fixture, to_raw_session
from process_sensor_session import process_session

ROOT = Path(__file__).resolve().parents[1]


def build_activity_demo():
    references = [with_activity_confirmation(process_session(to_raw_session(s)),
                  'basketball_training', 'manually_selected') for s in generate_reference_history()]
    summaries = [summarize_session(extract_session(s)) for s in references]
    baseline = fit_baseline(summaries)
    session = evaluation_fixture(process_session(generate_fixture()), 6)
    detection = detect_movement_episodes(session)
    # Explicitly replace the legacy task declaration with unconfirmed detector provenance.
    session['baseline_demo']['activity_context'] = detection
    before = json.dumps(session['samples'], sort_keys=True)
    states = []
    for activity in [None, *ACTIVITIES]:
        current = session if activity is None else with_activity_confirmation(
            session, activity, 'user_confirmed' if activity in detection['episodes'][0]['candidate_activities']
            else 'user_corrected')
        extracted = summarize_session(extract_session(current))
        result = compare_evaluations(baseline, [extracted])[0]
        matching = [m for m in baseline['metrics'] if m['context']['activity'] == activity]
        states.append({'activity': activity, 'confirmation': current['baseline_demo']['activity_context']['confirmation'],
                       'comparisons': result['comparisons'], 'insights': result['insights'],
                       'reference_status': matching[0]['reference_status'] if matching else 'insufficient_reference',
                       'eligible_session_count': matching[0]['eligible_session_count'] if matching else 0,
                       'contributing_event_count': matching[0]['contributing_event_count'] if matching else 0})
        assert json.dumps(current['samples'], sort_keys=True) == before
    return {'synthetic': True, 'mode': 'offline_generated_confirmation_choices',
            'detection': detection, 'activity_options': [{'id': key, 'label': label} for key, label in ACTIVITIES.items()],
            'states': states, 'reference_activity': 'basketball_training'}


def main():
    result = build_activity_demo()
    targets = [ROOT / 'data/baseline_demo/activity_context/demo.json',
               ROOT / 'rn-app/src/data/activity-context-results.json']
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print('Synthetic movement-pattern candidate detector — not validated sport recognition.')
    for episode in result['detection']['episodes']:
        print(f"{episode['episode_id']}: {episode['detected_movement']}; "
              f"{episode['features']['event_count']} complete contact cycles per side")
    for state in result['states'][:3]:
        print(f"{state['activity'] or 'Unconfirmed'}: {state['reference_status']}; "
              f"{state['eligible_session_count']} compatible sessions; "
              f"{state['comparisons'][0]['reasons']}")
    print('No metrics changed and no reference updated. Offline choices exported for the app.')


if __name__ == '__main__':
    main()
