"""Deterministic engineering validation; does not train on real athletes or rewrite mocks."""
import copy
import json
import math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

from generate_mock_data import session as mock_session, knee
from generate_raw_sensor_fixture import to_raw_session
from baseline_simulation import generate_reference_history
from activity_svm import MovementModel
from activity_temporal import synthetic_temporal_model
from synthetic_movement import training_records,held_out_records,ideal_calibration_records,movement_fixture
from sensor_to_segment_calibration import calibrate_pair
from aligned_kinematics import orientations,reconstruct
from kintra_pipeline import PipelineConfig,run_pipeline
from contextual_reference import fit_personal_reference,compare_personal_reference
from waveform_similarity import fit_waveform_reference
from athlete_confirmation import confirm_record

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'data/baseline_demo/modular_pipeline/demo.json'


def primary_raw(source):
    raw = to_raw_session(source)
    raw['sources']['left'].pop('knee',None)
    for row in raw['samples']:
        row['left'].pop('imu')
        row.pop('ground_truth',None)
    return raw


def mounting_validation():
    """Truth is used ONLY here for validation; calibration consumes measured arrays."""
    results = []
    # A +15 degree sagittal mounting offset gives a visible neutral-angle error.
    # The separate cosine-pulse tests also cover the subtler +15 degree X mount.
    setups = [('ideal',(0,0,0),(0,0,0)),('thigh_rotated',(0,15,0),(0,0,0)),
              ('shank_rotated',(0,0,0),(25,10,-20)),('both_rotated',(15,-10,12),(-25,15,-30))]
    for name,thigh,shank in setups:
        raw = movement_fixture('repeated_jump_landing',4)
        records = ideal_calibration_records()
        for segment,angles in (('thigh',thigh),('shank',shank)):
            mounting = Rotation.from_euler('xyz',angles,degrees=True).as_matrix()
            for row in raw['samples']:
                packet = row['right']['imu'][segment]
                for channel in ('gyro_rad_s','accel_m_s2'):
                    vector = mounting.T @ [packet[channel][a] for a in 'xyz']
                    packet[channel] = dict(zip('xyz',vector.tolist()))
            for channel in ('static_accel','positive_flexion_gyro'):
                records[segment][channel] = (np.array(records[segment][channel]) @ mounting).tolist()
        calibrated = calibrate_pair(records)
        naive = orientations(raw)
        aligned = reconstruct(raw,calibrated)['samples']
        truth = [knee(row['timestamp_s'],'right')['flexion_rad'] for row in raw['samples']]
        rms = lambda values: math.degrees(float(np.sqrt(np.mean(np.square(values)))))
        naive_rmse = rms([row['knee']['flexion_rad']-value for row,value in zip(naive,truth)])
        aligned_rmse = rms([row['right']['knee']['flexion_rad']-value for row,value in zip(aligned,truth)])
        assert aligned_rmse < 1  # software regression tolerance, not hardware accuracy
        if name!='ideal': assert naive_rmse > 2*aligned_rmse
        results.append({'fixture':name,'synthetic_mounting_euler_xyz_deg':{'thigh':thigh,'shank':shank},
                        'naive_angle_rmse_deg':naive_rmse,'calibrated_angle_rmse_deg':aligned_rmse,
                        'interpretation':'synthetic_software_regression_only_not_hardware_accuracy'})
    return results


def build_demo():
    train,test = training_records(),held_out_records()
    heldout = [r['group'] for r in test]
    svm = MovementModel().fit(train,heldout)
    hmm = synthetic_temporal_model(svm,train,heldout)
    defaults = {'calibration_records':ideal_calibration_records(),'movement_model':svm,'temporal_model':hmm,
                'confirmed_movement':'repeated_jump_landing','confirmed_activity':'basketball_training',
                'movement_source':'manually_selected','activity_source':'manually_selected',
                'acquisition_context':{'setup':'synthetic_upright_sagittal_mock_v1'}}
    history = [run_pipeline(primary_raw(s),PipelineConfig(**defaults,chronological_index=i+1))['record']
               for i,s in enumerate(generate_reference_history())]
    scalar = fit_personal_reference(history)
    waveform = fit_waveform_reference(history)
    original_reference = copy.deepcopy(scalar)
    current = primary_raw(json.loads((ROOT/'data/mock/balanced.json').read_text()))
    # Replay this SYNTHETIC recording twice to exercise a temporal sequence.
    # No original JSON or raw sensor packet is rewritten; the demo gets a new ID.
    repeated = copy.deepcopy(current['samples'])
    for row in repeated:
        row['timestamp_s'] += 6
        row['sequence'] += 600
    current['samples'].extend(repeated)
    current['session_id'] = 'synthetic_balanced_two_replays'
    current['sampling']['duration_s'] = 12
    defaults.update(scalar_reference=scalar,waveform_reference=waveform,
                    movement_source='user_confirmed',activity_source='user_confirmed',chronological_index=6)
    standard = run_pipeline(current,PipelineConfig(**defaults))
    wrong_sport = run_pipeline(current,PipelineConfig(**{**defaults,'confirmed_activity':'volleyball_training',
                                                        'activity_source':'user_corrected'}))
    corrected = confirm_record(standard['record'],'squat_like_repetitions','basketball_training',
                               'user_corrected','user_confirmed')
    correction = {'record':corrected,'comparison':compare_personal_reference(corrected,scalar),
                  'sensor_metrics_unchanged':corrected['biomechanics']==standard['record']['biomechanics'],
                  'model_history_unchanged':corrected['model_history']==standard['record']['model_history']}
    unconfirmed = run_pipeline(current,PipelineConfig(**{**defaults,'confirmed_movement':None,
                             'confirmed_activity':None,'movement_source':None,'activity_source':None}))
    shift_outputs,shift_records = [],[]
    for i,scale in enumerate((1.,1.05,1.10,1.15,1.20)):
        # Scaled mock pressure cells and force remain exactly consistent; no force
        # equation is altered and no original fixture is written.
        source = mock_session('balanced')
        source['session_id'] = f'synthetic_longitudinal_shift_{i+1}'
        for row in source['samples']:
            for foot in ('left','right'):
                packet = row[foot]['insole']
                packet['plantar_normal_force_n'] *= scale
                packet['cell_pressures_pa'] = [p*scale for p in packet['cell_pressures_pa']]
        result = run_pipeline(primary_raw(source),PipelineConfig(**{**defaults,
                    'chronological_index':7+i,'longitudinal_history':tuple(shift_records)}))
        shift_records.append(result['record'])
        shift_outputs.append(result)
    assert scalar==original_reference
    assert standard['stages']['personal_reference']['status']=='ready'
    assert standard['stages']['waveform_comparison']['status']=='ready'
    assert wrong_sport['stages']['personal_reference']['status']=='insufficient_reference'
    assert correction['comparison']['status']=='insufficient_reference'
    assert correction['sensor_metrics_unchanged'] and correction['model_history_unchanged']
    assert unconfirmed['stages']['personal_reference']['status']=='requires_confirmation'
    assert shift_outputs[-1]['stages']['longitudinal']['direction']=='increased'
    assert all(s['stages']['reliability']['status']=='reliability_not_established' for s in shift_outputs)
    return {'synthetic':True,'validation':'engineering_integration_only',
            'claim_boundary':"Research supports the feasibility of the sensing and algorithmic methods. Kintra's current implementation demonstrates software integration using synthetic data. The final hardware and trained models require real-athlete and laboratory validation.",
            'model_metadata':{'svm':svm.metadata,'hmm':hmm.metadata},
            'reference':scalar,'waveform_reference':waveform,'standard':standard,
            'wrong_sport':wrong_sport,'movement_correction':correction,'unconfirmed':unconfirmed,
            'mounting_validation':mounting_validation(),'longitudinal_shift':shift_outputs,
            'reference_remained_fixed':scalar==original_reference}


def main():
    result = build_demo()
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('Synthetic Kintra pipeline — engineering validation, not hardware validation.')
    print('Primary configuration: one right-knee IMU pair + bilateral mock smart-insoles.')
    standard = result['standard']['stages']
    print(f"Filter: {standard['filtering']['config']['method']}; beta: {standard['orientation']['beta']:.2f}")
    print(f"A. SVM: {standard['activity_svm']['episode']['raw_svm_prediction']}")
    print('   HMM windows: '+', '.join(w['temporal_model_prediction'] for w in standard['temporal_model']['windows']))
    print('   Athlete confirms: repeated_jump_landing + basketball_training')
    print(f"   Scalar reference: {standard['personal_reference']['status']}; waveform: {standard['waveform_comparison']['status']}")
    print(f"   Complete monitored-knee contacts: {len(standard['events']['landings'])}")
    for c in standard['personal_reference']['comparisons']:
        print(f"   {c['side']} {c['metric']}: {c['evaluation_median']:.4f} {c['unit']}; reference {c['reference_median']:.4f}; change {c['percent_difference']:+.2f}%")
    print(f"   Knee flexion shape DTW: {standard['waveform_comparison']['session_median_distance']:.4f} (z-normalized; descriptive)")
    print(f"B. Volleyball confirmation: {result['wrong_sport']['stages']['personal_reference']['status']}; basketball history rejected.")
    correction = result['movement_correction']
    print(f"C. Squat correction: {correction['comparison']['status']}; predictions and metrics preserved: {correction['model_history_unchanged'] and correction['sensor_metrics_unchanged']}")
    print('D. Synthetic mounting errors (angle RMSE, deg):')
    for item in result['mounting_validation']:
        print(f"   {item['fixture']}: naive {item['naive_angle_rmse_deg']:.3f} -> PCA-aligned {item['calibrated_angle_rmse_deg']:.3f}")
    print('E. Right plantar force/BW session trend (lambda=0.30; engineering demo factor):')
    for p in result['longitudinal_shift'][-1]['stages']['longitudinal']['points']:
        print(f"   {p['session_id']}: value {p['value']:.3f}; EWMA {p['ewma']:.3f}")
    print('   Fixed personal reference unchanged; SPC reference_limits_not_established.')
    print(f"F. MDC: null; {standard['reliability']['status']}; change exceeds measurement error: unavailable.")
    print('Unconfirmed movement/activity: requires_confirmation. ACT/VERIFY: not_yet_implemented.')
    print(f'JSON: {OUTPUT.relative_to(ROOT)}')


if __name__=='__main__':
    main()
