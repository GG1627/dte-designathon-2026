from test_baseline_simulation import ROOT
from run_kintra_pipeline_demo import build_demo,mounting_validation


def test_demo_scenarios_and_fixed_reference():
    demo=build_demo()
    standard=demo['standard']['stages']
    assert standard['activity_svm']['episode']['raw_svm_prediction']=='repeated_jump_landing'
    assert standard['temporal_model']['windows'][0]['temporal_model_prediction']=='repeated_jump_landing'
    assert standard['personal_reference']['status']=='ready'
    assert demo['wrong_sport']['stages']['personal_reference']['status']=='insufficient_reference'
    assert demo['movement_correction']['comparison']['status']=='insufficient_reference'
    assert demo['movement_correction']['record']['confirmation_history'][-1]['confirmed_movement']=='repeated_jump_landing'
    assert demo['reference_remained_fixed']
    assert demo['longitudinal_shift'][-1]['stages']['longitudinal']['direction']=='increased'
    assert standard['reliability']['status']=='reliability_not_established'
    assert all(r['mdc'] is None and r['change_exceeds_mdc'] is None for r in standard['reliability']['results'])
    assert standard['spc']['spc_status']=='reference_limits_not_established'
    assert 'synthetic data' in demo['claim_boundary']
