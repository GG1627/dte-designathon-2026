import copy
import itertools
import numpy as np
import pytest
from test_baseline_simulation import ROOT
from activity_svm import STATES, MovementModel
from activity_temporal import MovementHMM, synthetic_temporal_model
from synthetic_movement import training_records, held_out_records


def model_fixture():
    sequences=[{'group':s,'states':[s]*8,'observations':[s]*8} for s in STATES]
    return MovementHMM.fit(sequences)


def test_viterbi_matches_exhaustive_maximum_not_majority_vote():
    hmm=model_fixture()
    observations=['running_like','walking_like','running_like']
    actual=hmm.decode(observations)
    def likelihood(path):
        indices=[STATES.index(s) for s in path]
        score=np.log(hmm.initial[indices[0]])
        score+=sum(np.log(hmm.emission[s,STATES.index(o)]) for s,o in zip(indices,observations))
        score+=sum(np.log(hmm.transition[a,b]) for a,b in zip(indices,indices[1:]))
        return score
    assert likelihood(actual)==pytest.approx(max(likelihood(path) for path in itertools.product(STATES,repeat=3)))
    assert actual==hmm.decode(observations)


def test_hmm_normalized_and_preserves_raw_predictions():
    hmm=model_fixture()
    for matrix in (hmm.transition,hmm.emission):
        assert np.isfinite(matrix).all() and np.allclose(matrix.sum(axis=1),1)
    output={'status':'ready','reasons':[],'windows':[{'raw_svm_prediction':'running_like','model_decision_scores':{'running_like':2}}]*3}
    original=copy.deepcopy(output)
    result=hmm.smooth(output)
    assert output==original
    assert all(w['raw_svm_prediction']=='running_like' and w['athlete_confirmed_movement'] is None for w in result['windows'])
    assert result['model_metadata']['provenance']=='synthetic_software_demo_temporal_parameters'
    assert not result['prediction_is_confirmation']


def test_training_cv_and_temporal_groups_do_not_touch_test():
    train,test=training_records(),held_out_records()
    heldout=[r['group'] for r in test]
    svm=MovementModel().fit(train,heldout)
    hmm=synthetic_temporal_model(svm,train,heldout)
    assert not set(hmm.metadata['emission_training_groups']) & set(heldout)
    assert not set(hmm.metadata['training_groups']) & set(heldout)
    assert 'cross_validated' in hmm.metadata['emission_construction']
    # A six-second clip can start during a jump bout, without preceding quiet windows.
    assert hmm.decode(['repeated_jump_landing'])==['repeated_jump_landing']
    assert 'five_start_states' in hmm.metadata['sequence_start_policy']


@pytest.mark.parametrize('fault',['probabilities','unknown','overlap'])
def test_invalid_hmm_inputs(fault):
    hmm=model_fixture()
    with pytest.raises(ValueError):
        if fault=='probabilities':
            metadata=copy.deepcopy(hmm.metadata)
            metadata['transition_matrix'][0][0]=float('nan')
            MovementHMM(metadata)
        elif fault=='unknown': hmm.decode(['basketball'])
        else: MovementHMM.fit([{'group':'same','states':list(STATES),'observations':list(STATES)}],held_out_groups=['same'])
