"""Canonical contact-window metrics using the existing audited analyzer arithmetic.

These are contact-window metrics, NOT replacements for annotated-window reports.
No opposite knee is reconstructed from foot data.
"""
import copy
import math
from statistics import mean, median
from biomechanical_events import finite, contact_sample_indices, EventProtocol
from generate_mock_data import reconstructed_force, PRESSURE_FORCE_REL_TOL, PRESSURE_FORCE_ABS_TOL_N

VERSION = 'contact-window-biomechanics/1.0.0'


CONTACT_THRESHOLD_N = EventProtocol().contact_threshold_n
KINEMATIC_KEYS = (
    "minimum_deg", "maximum_deg", "rom_deg",
    "peak_abs_velocity_deg_s", "peak_abs_acceleration_deg_s2",
)
LOADING_KEYS = (
    "peak_plantar_normal_force_n", "peak_force_bw", "contact_time_s",
    "impulse_n_s", "average_loading_rate_n_s",
)
PRESSURE_KEYS = ("mean_medial_fraction", "mean_lateral_fraction", "cop_at_peak_force_m")


valid_number = finite

def unavailable(keys, reasons):
    return {**dict.fromkeys(keys), "quality": {"valid": False, "reasons": reasons}}


def summarize_knee(samples, side):
    """Convert knee signals to degrees and summarize a nonempty window."""
    angles = [math.degrees(sample[side]["knee"]["flexion_rad"]) for sample in samples]
    velocities = [math.degrees(sample[side]["knee"]["angular_velocity_rad_s"])
                  for sample in samples]
    accelerations = [math.degrees(sample[side]["knee"]["angular_acceleration_rad_s2"])
                     for sample in samples]
    minimum = min(angles)
    maximum = max(angles)
    return {
        "minimum_deg": minimum,
        "maximum_deg": maximum,
        "rom_deg": maximum - minimum,
        "peak_abs_velocity_deg_s": max(abs(value) for value in velocities),
        "peak_abs_acceleration_deg_s2": max(abs(value) for value in accelerations),
    }


def average_loading_rate(window, foot, onset, peak):
    """Average observed onset-to-peak dF/dt; shared by both window policies."""
    elapsed = window[peak]['timestamp_s']-window[onset]['timestamp_s']
    return ((window[peak][foot]['insole']['plantar_normal_force_n']
             -window[onset][foot]['insole']['plantar_normal_force_n'])/elapsed) if elapsed>0 else None


def summarize_side(samples, side, body_weight_n, window_reasons, cells):
    motion = [sample[side]["knee"] for sample in samples]
    feet = [sample[side]["insole"] for sample in samples]
    knee_reasons = list(window_reasons)
    if any(not row["quality"]["valid"] or not all(valid_number(row[key]) for key in (
        "flexion_rad", "angular_velocity_rad_s", "angular_acceleration_rad_s2"
    )) for row in motion):
        knee_reasons.append("invalid_knee_samples")
    if any(not valid_number(row.get("timestamp_s", sample["timestamp_s"]))
           or abs(row.get("timestamp_s", sample["timestamp_s"]) - sample["timestamp_s"]) > 1e-8
           for sample, row in zip(samples, motion)):
        knee_reasons.append("unaligned_knee_timestamp")
    kinematics = (unavailable(KINEMATIC_KEYS, knee_reasons) if knee_reasons else {
        **summarize_knee(samples, side), "quality": {"valid": True, "reasons": []},
    })
    force_reasons = list(window_reasons)
    for sample, row in zip(samples, feet):
        force = row["plantar_normal_force_n"]
        if not row["quality"]["valid"] or not valid_number(force) or force < 0:
            force_reasons.extend(row["quality"]["reasons"] or ["invalid_insole_samples"])
        packet_time = row.get("timestamp_s", sample["timestamp_s"])
        if not valid_number(packet_time) or abs(packet_time - sample["timestamp_s"]) > 1e-8:
            force_reasons.append("unaligned_insole_timestamp")
        if row["quality"]["valid"]:
            try:
                reconstructed = reconstructed_force(row.get("cell_pressures_pa"), cells)
                if valid_number(force) and not math.isclose(reconstructed, force,
                        rel_tol=PRESSURE_FORCE_REL_TOL, abs_tol=PRESSURE_FORCE_ABS_TOL_N):
                    force_reasons.append("inconsistent_pressure_force")
            except ValueError as error:
                force_reasons.append(str(error))
    if force_reasons:
        reasons = sorted(set(force_reasons))
        return {"kinematics": kinematics, "loading": unavailable(LOADING_KEYS, reasons),
                "pressure": unavailable(PRESSURE_KEYS, reasons)}

    times = [sample["timestamp_s"] for sample in samples]
    forces = [row["plantar_normal_force_n"] for row in feet]
    peak_index = max(range(len(forces)), key=forces.__getitem__)
    peak = forces[peak_index]
    contacts = contact_sample_indices(samples, side, CONTACT_THRESHOLD_N)
    # Integrate the entire annotated window, including sub-threshold forces.
    impulse = sum((forces[i] + forces[i + 1]) / 2 * (times[i + 1] - times[i])
                  for i in range(len(samples) - 1))
    contact_time = 0.0
    loading_rate = None
    reasons = []
    if contacts:
        onset = contacts[0]
        # Each above-threshold sample starts a contact interval to the next sample.
        contact_time = sum(times[i + 1] - times[i] for i in contacts if i + 1 < len(times))
        if onset == 0 or contacts[-1] == len(times) - 1:
            contact_time = None
            reasons.append("contact_crosses_window_boundary")
        elif contacts != list(range(onset, contacts[-1] + 1)):
            reasons.append("multiple_contacts_in_window")
        elif times[peak_index] > times[onset]:
            loading_rate = average_loading_rate(samples, side, onset, peak_index)
        else:
            reasons.append("zero_time_to_peak")
    else:
        reasons.append("no_contact")
    normalized_peak = peak / body_weight_n if body_weight_n is not None else None
    if body_weight_n is None:
        reasons.append("invalid_participant_mass")
    loading = dict(zip(LOADING_KEYS, (peak, normalized_peak, contact_time, impulse, loading_rate)))
    loading["quality"] = {"valid": not reasons, "reasons": reasons}

    pressure = dict.fromkeys(PRESSURE_KEYS)
    pressure_reasons = []
    for region in ("medial", "lateral"):
        values = [feet[i][f"{region}_fraction"] for i in contacts]
        if values and all(valid_number(value) and 0 <= value <= 1 for value in values):
            pressure[f"mean_{region}_fraction"] = mean(values)
        else:
            pressure_reasons.append(f"unavailable_{region}_fractions")
    cop = feet[peak_index]["cop_m"]
    if contacts and cop is not None and all(valid_number(cop[key]) for key in ("x_m", "y_m")):
        pressure["cop_at_peak_force_m"] = cop
    else:
        pressure_reasons.append("unavailable_cop_at_peak")
    pressure["quality"] = {"valid": not pressure_reasons, "reasons": pressure_reasons}
    return {"kinematics": kinematics, "loading": loading, "pressure": pressure}

def canonical_loading(window, foot, loading, contact, window_onset_index, protocol):
    """Shared audited onset-to-peak dF/dt and observed contact duration."""
    loading['canonical_contact_time_s'] = contact['contact_time_s'] if contact else None
    loading['contact_protocol'] = copy.deepcopy(protocol)
    if contact is None:
        return
    onset = contact['onset_index']-window_onset_index
    peak = max(range(len(window)),key=lambda i:window[i][foot]['insole']['plantar_normal_force_n'])
    elapsed = window[peak]['timestamp_s']-window[onset]['timestamp_s']
    loading['contact_time_s'] = contact['contact_time_s']
    loading['average_loading_rate_n_s'] = average_loading_rate(window, foot, onset, peak)
    loading['quality']['reasons'] = [r for r in loading['quality']['reasons']
                                     if r!='contact_crosses_window_boundary']
    if elapsed<=0: loading['quality']['reasons'].append('zero_time_to_peak')
    loading['quality']['valid'] = not loading['quality']['reasons']


def plantar_metrics(raw, events, side):
    """Each foot's own complete contacts, independent of knee instrumentation.

    The explicit missing-knee adapter only satisfies summarize_side's interface;
    its null kinematics are discarded. No synthetic knee samples are introduced.
    """
    if events['status'] != 'ready':
        return {'status':'unavailable','reasons':events['reasons'],'events':[]}
    bw = raw['participant']['mass_kg']*9.80665
    output = []
    for contact in events['contacts']:
        if contact['side'] != side:
            continue
        window = copy.deepcopy(raw['samples'][contact['onset_index']:contact['offset_index']+1])
        for row in window:
            row[side]['knee'] = {'flexion_rad':None,'angular_velocity_rad_s':None,
                'angular_acceleration_rad_s2':None,'quality':{'valid':False,'reasons':['not_a_knee_measurement']}}
        summary = summarize_side(window,side,bw,[],raw['insole_geometry'][side])
        canonical_loading(window,side,summary['loading'],contact,contact['onset_index'],events['protocol'])
        output.append({**contact,'loading':summary['loading'],'pressure':summary['pressure']})
    return {'status':'ready' if output else 'unavailable','version':VERSION,
            'reasons':[] if output else ['no_complete_foot_contacts'],'events':output,
            'scope':'own_foot_canonical_contact_windows','body_weight_n':bw}


def event_metrics(processed, events):
    if events['status'] != 'ready':
        return {'status':'unavailable','version':VERSION,'reasons':events['reasons'], 'events':[], 'session_metrics':{}}
    side = processed['monitored_knee_side']
    mass = processed['participant'].get('mass_kg')
    bw = mass*9.80665 if finite(mass) and mass > 0 else None
    output = []
    for event in events['landings']:
        window = copy.deepcopy(processed['samples'][event['onset_index']:event['offset_index']+1])
        # An explicit unavailable knee packet lets the existing analyzer return
        # null opposite-leg kinematics; only its insole results are retained.
        other = 'left' if side == 'right' else 'right'
        for row in window:
            row[other]['knee'] = {'flexion_rad':None,'angular_velocity_rad_s':None,
                                 'angular_acceleration_rad_s2':None,
                                 'quality':{'valid':False,'reasons':['knee_not_instrumented']}}
        summaries = {foot:summarize_side(window,foot,bw,[],processed['insole_geometry'][foot])
                     for foot in ('left','right')}
        # A complete canonical contact starts at its first above-threshold sample.
        # It has an observed onset/offset, unlike a truncated annotated window.
        # Reuse the same dF/dt definition with the canonical onset, preserving
        # the original analyzer's annotated-window policy and arithmetic.
        for foot in summaries:
            matching = [c for c in events['contacts'] if c['side']==foot and
                        c['start_s'] >= event['start_s'] and c['end_s'] <= event['end_s']]
            loading = summaries[foot]['loading']
            canonical_loading(window,foot,loading,matching[0] if len(matching)==1 else None,
                              event['onset_index'],events['protocol'])
        output.append({'event_id':event['event_id'],'start_s':event['start_s'],'end_s':event['end_s'],
                       'event_source':events['version'], 'monitored_knee_side':side,
                       'kinematics':summaries[side]['kinematics'],
                       'loading':{foot:summaries[foot]['loading'] for foot in summaries},
                       'pressure':{foot:summaries[foot]['pressure'] for foot in summaries},
                       'knee_flexion_waveform_rad':[row[side]['knee']['flexion_rad'] for row in window]})
    scalars = {}
    def add(name,values):
        valid = [v for v in values if finite(v)]
        scalars[name] = median(valid) if len(valid)==len(output) and valid else None
    add('knee_rom_rad',[(max(e['knee_flexion_waveform_rad'])-min(e['knee_flexion_waveform_rad'])) for e in output])
    for foot in ('left','right'):
        add(f'{foot}_peak_plantar_normal_force_bw',[e['loading'][foot]['peak_force_bw'] for e in output])
        add(f'{foot}_contact_window_impulse_bw_s',[e['loading'][foot]['impulse_n_s']/bw
            if bw and e['loading'][foot]['impulse_n_s'] is not None else None for e in output])
    return {'status':'ready' if output else 'unavailable','version':VERSION,
            'reasons':[] if output else ['no_complete_monitored_side_contacts'],
            'events':output,'session_metrics':scalars,'event_source':events['version'],
            'scope':'canonical_contact_window_not_legacy_annotated_window',
            'uninstrumented_knee':{'side':other if output else ('left' if side=='right' else 'right'),
                                   'status':'unavailable','reason':'knee_not_instrumented'}}
