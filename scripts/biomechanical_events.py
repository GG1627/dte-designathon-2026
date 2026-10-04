"""Canonical sample-index contact definitions, independent of annotations/labels."""
import math
from dataclasses import asdict, dataclass
from generate_mock_data import reconstructed_force, PRESSURE_FORCE_REL_TOL, PRESSURE_FORCE_ABS_TOL_N

VERSION = 'biomechanical-events/1.0.0'


def finite(value):
    # Keep the shared event primitive usable by the standard-library legacy path.
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


@dataclass(frozen=True)
class EventProtocol:
    contact_threshold_n: float = 20.0
    source: str = 'existing_Kintra_synthetic_demo_20_N_rule'
    task: str = 'synthetic_contact_and_landing_candidate'
    validated_for_current_hardware: bool = False
    bilateral_pair_tolerance_s: float = .1

    def __post_init__(self):
        if (not finite(self.contact_threshold_n) or self.contact_threshold_n <= 0 or
            not finite(self.bilateral_pair_tolerance_s) or self.bilateral_pair_tolerance_s < 0 or
            not self.source or not self.task):
            raise ValueError('Explicit positive contact threshold and protocol required')


def above_contact_threshold(force, threshold_n=20.0):
    """Shared strict observed-sample contact predicate; no interpolation."""
    return force > threshold_n


def contact_sample_indices(rows, side, threshold_n=20.0):
    """Above-threshold samples for already quality-checked metric windows."""
    return [i for i,row in enumerate(rows)
            if above_contact_threshold(row[side]['insole']['plantar_normal_force_n'],threshold_n)]


def contact_indices(rows, side, threshold_n=20.0):
    """Complete above-threshold onset to first below-threshold offset only.

    No interpolation; boundary-truncated contacts are excluded. Used by both
    the legacy heuristic detector and the modular activity/biomechanics paths.
    """
    intervals, start = [], None
    for i, row in enumerate(rows):
        packet = row[side]['insole']
        force = packet.get('plantar_normal_force_n')
        if not finite(force) or force < 0 or packet.get('quality', {}).get('valid') is not True:
            raise ValueError('Invalid force contact data')
        contact = above_contact_threshold(force, threshold_n)
        if contact and start is None and i > 0 and rows[i-1][side]['insole']['plantar_normal_force_n'] <= threshold_n:
            start = i
        if not contact and start is not None:
            intervals.append((start, i))
            start = None
    return intervals


def extract_events(processed, protocol=EventProtocol(), *, knee_required=True, feet=('left','right')):
    """The same contact primitive can also run on feet without any knee signal."""
    rows = processed.get('samples', [])
    side = processed.get('monitored_knee_side', 'right')
    reasons = set()
    rate = processed.get('sampling', {}).get('rate_hz')
    if len(rows) < 3 or not finite(rate) or rate <= 0:
        reasons.add('invalid_sampling_or_empty_stream')
    for i,row in enumerate(rows):
        t = row.get('timestamp_s')
        if not finite(t) or type(row.get('sequence')) is not int:
            reasons.add('invalid_timestamp_or_sequence')
        if i and (not finite(t) or not finite(rows[i-1].get('timestamp_s')) or not finite(rate) or rate <= 0 or
                  not math.isclose(t-rows[i-1]['timestamp_s'],1/rate,rel_tol=0,abs_tol=1e-8) or
                  type(row.get('sequence')) is not int or type(rows[i-1].get('sequence')) is not int or
                  row['sequence'] != rows[i-1]['sequence']+1):
            reasons.add('sample_discontinuity')
        knee = row.get(side, {}).get('knee', {})
        if knee_required and (knee.get('quality', {}).get('valid') is not True or not finite(knee.get('flexion_rad'))):
            reasons.add('invalid_knee_signal')
        for foot in feet:
            packet = row.get(foot, {}).get('insole', {})
            force = packet.get('plantar_normal_force_n')
            if packet.get('quality', {}).get('valid') is not True or not finite(force) or force < 0:
                reasons.add('invalid_or_missing_insole')
                continue
            pt = packet.get('timestamp_s', t)
            if not finite(pt) or not finite(t) or abs(pt-t) > 1e-8:
                reasons.add('unaligned_insole_timestamp')
            cells = processed.get('insole_geometry', {}).get(foot)
            if cells is not None:
                try:
                    reconstructed = reconstructed_force(packet.get('cell_pressures_pa'),cells)
                    if not math.isclose(force,reconstructed,rel_tol=PRESSURE_FORCE_REL_TOL,abs_tol=PRESSURE_FORCE_ABS_TOL_N):
                        reasons.add('inconsistent_pressure_force')
                except ValueError:
                    reasons.add('invalid_pressure_cells')
    output = {'status': 'unavailable' if reasons else 'ready', 'version': VERSION,
              'reasons': sorted(reasons), 'protocol': asdict(protocol), 'contacts': [],
              'bilateral_pairs': [], 'noncontact_intervals': [], 'landings': [],
              'boundary_policy': 'exclude_truncated_contacts_no_interpolation'}
    if reasons:
        return output
    by_side = {foot: contact_indices(rows,foot,protocol.contact_threshold_n) for foot in feet}
    for foot, intervals in by_side.items():
        for j,(a,b) in enumerate(intervals):
            event = {'event_id': f'{foot}_contact_{j+1}', 'side':foot,'onset_index':a,'offset_index':b,
                     'start_s':rows[a]['timestamp_s'],'end_s':rows[b]['timestamp_s'],
                     'contact_time_s':rows[b]['timestamp_s']-rows[a]['timestamp_s'], 'source': VERSION}
            output['contacts'].append(event)
            if foot == side and knee_required:
                peak = max(range(a,b+1),key=lambda i:rows[i][side]['knee']['flexion_rad'])
                output['landings'].append({**event,'landing_initial_contact_s':event['start_s'],
                    'peak_flexion_index':peak,'peak_flexion_s':rows[peak]['timestamp_s'],
                    'peak_flexion_rad':rows[peak][side]['knee']['flexion_rad'],
                    'interpretation':'contact_with_post_contact_flexion; movement_requires_confirmation'})
        for (_,a),(b,_) in zip(intervals,intervals[1:]):
            output['noncontact_intervals'].append({'side':foot,'start_s':rows[a]['timestamp_s'],
                                                   'end_s':rows[b]['timestamp_s']})
    remaining = list(by_side.get('right', []))
    for a,b in by_side.get('left', []):
        matches = [item for item in remaining if abs(rows[a]['timestamp_s']-rows[item[0]]['timestamp_s']) <= protocol.bilateral_pair_tolerance_s]
        if matches:
            chosen = min(matches,key=lambda item:abs(rows[a]['timestamp_s']-rows[item[0]]['timestamp_s']))
            remaining.remove(chosen)
            output['bilateral_pairs'].append({'left_onset_index':a,'right_onset_index':chosen[0]})
    return output
