"""Bilateral and one-knee engineering demo; no hardware/clinical validation."""
import copy
import json
from pathlib import Path

from kintra_pipeline import run_pipeline
from synthetic_bilateral import bilateral_fixture, fixture_config, SCENARIOS
from contextual_reference import fit_personal_reference
from waveform_similarity import fit_waveform_reference
from synthetic_movement import training_records
from activity_svm import MovementModel
from activity_temporal import synthetic_temporal_model
from sensor_configuration import SIDES

OUTPUT = Path(__file__).resolve().parents[1]/'data/baseline_demo/bilateral_pipeline/demo.json'


def build_demo():
    training = training_records()
    svm = MovementModel().fit(training)
    hmm = synthetic_temporal_model(svm,training)
    history = {s:[] for s in SIDES}
    for i in range(5):
        raw = bilateral_fixture(session_id=f'synthetic_bilateral_reference_{i+1}')
        result = run_pipeline(raw,fixture_config(raw,chronological_index=i+1))
        for side in SIDES:
            history[side].append(result['knees'][side]['record'])
    scalar = {s:fit_personal_reference(history[s]) for s in SIDES}
    wave = {s:fit_waveform_reference(history[s]) for s in SIDES}
    before = copy.deepcopy((scalar,wave))
    results = {}
    shifts = {s:[] for s in SIDES}
    for index,scenario in enumerate(SCENARIOS):
        raw = bilateral_fixture(scenario)
        options = {s:{'scalar_reference':scalar[s],'waveform_reference':wave[s],
            'longitudinal_history':tuple(shifts[s])} for s in SIDES}
        result = run_pipeline(raw,fixture_config(raw,scenario,side_options=options,
            movement_model=svm,temporal_model=hmm,chronological_index=6+index))
        results[scenario] = result
        if scenario in ('symmetric','right_rom_reduced'):
            for side in SIDES:
                shifts[side].append(result['knees'][side]['record'])
    fixed = before == (scalar,wave)
    assert fixed
    return {'synthetic':True,'validation':'engineering_only_not_hardware_or_clinical_validation',
        'reference_maturity':'provisional_reference; five synthetic sessions are software fixtures',
        'references':scalar,'waveform_references':wave,'reference_remained_fixed':fixed,'scenarios':results}


def display(value, unit=''):
    return f'{value:.2f}{unit}' if value is not None else 'unavailable'


def main():
    demo = build_demo()
    print('Kintra bilateral pipeline — synthetic engineering validation only')
    print('All fixture sensors are synthetic_demo; this is not a hardware trial.')
    for name,result in demo['scenarios'].items():
        print(f'\n{name} | {result["configuration"]["mode"]}')
        for side in SIDES:
            knee = result['knees'][side]
            print(f'  {side.capitalize()} knee: {knee["status"]} | source: {knee["source"]}')
            for c in knee['personal_reference'].get('comparisons',[]):
                if c['metric']=='knee_rom_rad':
                    print(f'    Own-side ROM reference deviation: {display(c["percent_difference"], " %")}')
            wave = knee['waveform_comparison']
            print(f'    Own-side DTW: {display(wave.get("session_median_distance"))}; EWMA: {knee["longitudinal"].get("direction") or "unavailable"}')
        for channel,metric in (('knee_kinematics','rom_deg'),('plantar_loading','peak_force_bw')):
            comparison = result['bilateral'][channel]
            print(f'  {channel}: {comparison["status"]} | source: {comparison["source"]}')
            print(f'    {metric} asymmetry: {display(comparison["metrics"][metric]["asymmetry_percent"], " %")}')
            if comparison['reasons']:
                print('    Reasons: '+', '.join(comparison['reasons']))
    assert demo['scenarios']['missing_left']['bilateral']['knee_kinematics']['status']=='unavailable'
    assert demo['scenarios']['missing_left']['bilateral']['plantar_loading']['status']=='ready'
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(demo,indent=2,allow_nan=False)+'\n')
    print('\nFixed references preserved. MDC/measurement error not established.')
    print(f'JSON: {OUTPUT}')


if __name__=='__main__':
    main()
