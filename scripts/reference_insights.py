"""Transparent descriptive rules over derived comparisons; no sensor/scenario access."""
import math

ROM = 'knee_rom_rad'
FORCE = 'peak_plantar_normal_force_bw'
IMPULSE = 'landing_window_impulse_bw_s'


def build_insights(comparisons):
    """Only available, provisional, compatible comparisons can support statements.

    Directions come from the Python comparator's numerical tolerance, not a
    clinical deadband. A pattern requires all four movement/peak-force inputs.
    A generic description is used when the exact pattern does not apply.
    """
    usable = [c for c in comparisons if c.get('comparison_availability') == 'available'
              and c.get('status') in ('compared', 'partial')
              and not c.get('reasons') and c.get('reference_status') == 'provisional_reference'
              and c.get('direction') in ('increased', 'decreased', 'near_reference')
              and all(isinstance(c.get(key), (int, float)) and not isinstance(c[key], bool)
                      and math.isfinite(c[key]) for key in
                      ('evaluation_median', 'reference_median', 'signed_difference'))]
    if not usable:
        return []
    # Never combine evidence from distinct athletes/activities/configurations.
    contexts = {tuple(sorted(c['context'].items())) for c in usable}
    if len(contexts) != 1 or len({(c['side'], c['metric']) for c in usable}) != len(usable):
        return []
    lookup = {(c['side'], c['metric']): c for c in usable}
    required = [lookup.get((side, metric)) for metric in (FORCE, ROM) for side in ('left', 'right')]
    pattern = 'descriptive_comparison'
    evidence = usable
    if all(required):
        left_force, right_force, left_rom, right_rom = required
        forces = [left_force['direction'], right_force['direction']]
        movement = [left_rom['direction'], right_rom['direction']]
        evidence = required
        if forces == ['increased', 'increased'] and movement == ['near_reference', 'near_reference']:
            pattern = 'bilateral_loading_increase'
            title = 'Landing load increased on both sides'
            summary = ('Peak external plantar force increased on both sides relative to your personal '
                       'reference while knee movement range remained near its reference pattern.')
        elif forces == ['near_reference', 'near_reference'] and movement == ['decreased', 'decreased']:
            pattern = 'rom_decrease'
            title = 'Knee movement range decreased'
            summary = ('Knee movement range decreased relative to your personal reference while '
                       'peak external plantar force remained near its reference level.')
        elif forces == ['near_reference', 'increased'] and movement == ['near_reference', 'near_reference']:
            pattern = 'right_loading_increase'
            title = 'Right-side landing load increased'
            summary = ('Right-side peak external plantar force increased relative to your personal '
                       'reference while left-side peak force and knee movement range remained near their references.')
    if pattern == 'descriptive_comparison':
        title = 'This session compared with your reference'
        labels = {ROM: 'knee movement range', FORCE: 'peak external plantar force', IMPULSE: 'landing impulse'}
        descriptions = [f"{c['side'].capitalize()} {labels[c['metric']]} "
                        + ('remained near its reference' if c['direction'] == 'near_reference'
                           else f"{c['direction']} relative to its reference")
                        for c in usable if c['metric'] in labels]
        if not descriptions:
            return []
        summary = '; '.join(descriptions) + '.'
    magnitudes = [f"{c['side'].capitalize()} {'movement range' if c['metric'] == ROM else 'peak force'} "
                  f"was about {abs(c['percent_difference']):.1f}% "
                  f"{'above' if c['direction'] == 'increased' else 'below'} your personal reference."
                  for c in evidence if c['direction'] != 'near_reference' and c['metric'] in (ROM, FORCE)
                  and c.get('percent_difference') is not None]
    return [{'title': title, 'summary': ' '.join([summary, *magnitudes]), 'pattern': pattern,
             'activity': usable[0]['context']['activity'],
             'side': 'bilateral' if {c['side'] for c in evidence} == {'left', 'right'} else evidence[0]['side'],
             'evidence': [{'metric': c['metric'], 'side': c['side'], 'unit': c['unit'],
                           'current': c['evaluation_median'], 'reference': c['reference_median'],
                           'signed_difference': c['signed_difference'], 'percent_difference': c['percent_difference'],
                           'direction': c['direction']} for c in evidence],
             'context': usable[0]['context'], 'reference_status': 'provisional_reference',
             'rule_version': 'descriptive-reference/1.0.0', 'medical_inference': False}]
