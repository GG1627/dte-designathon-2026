"""Categorical HMM learned from labeled synthetic sequences; log-space Viterbi.

No probabilities of athlete truth are exposed. Transition/emission probabilities
describe only the synthetic training construction, with explicit Laplace smoothing.
"""
import copy
import numpy as np
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.base import clone
from activity_svm import STATES, extract_features

VERSION = 'categorical-hmm-viterbi/1.0.0'


def probability_matrix(values, shape):
    array = np.asarray(values,float)
    if array.shape != shape or not np.isfinite(array).all() or np.any(array <= 0) or not np.allclose(array.sum(axis=-1),1):
        raise ValueError('Positive finite normalized HMM probabilities required')
    return array


class MovementHMM:
    def __init__(self, metadata):
        self.metadata = copy.deepcopy(metadata)
        self.states = tuple(metadata['states'])
        if self.states != STATES: raise ValueError('HMM and SVM movement taxonomies must match')
        n = len(self.states)
        self.transition = probability_matrix(metadata['transition_matrix'],(n,n))
        self.emission = probability_matrix(metadata['emission_matrix'],(n,n))
        self.initial = probability_matrix(metadata['initial_probabilities'],(n,))

    @classmethod
    def fit(cls, sequences, pseudocount=1., held_out_groups=(), emission_pairs=None):
        if not np.isfinite(pseudocount) or pseudocount <= 0 or not sequences:
            raise ValueError('Nonempty labeled training sequences and positive pseudocount required')
        groups = {s['group'] for s in sequences}
        if groups & set(held_out_groups): raise ValueError('Temporal train/test group overlap')
        lookup = {state:i for i,state in enumerate(STATES)}
        n = len(STATES)
        transitions = np.full((n,n),pseudocount)
        emissions = np.full((n,n),pseudocount)
        initial = np.full(n,pseudocount)
        seen = set()
        for seq in sequences:
            states,observations = seq['states'],seq['observations']
            if not states or len(states)!=len(observations) or not set(states+observations) <= set(STATES):
                raise ValueError('Aligned known state/observation sequences required')
            seen.update(states)
            initial[lookup[states[0]]] += 1
            for a,b in zip(states,states[1:]): transitions[lookup[a],lookup[b]] += 1
            if emission_pairs is None:
                for state,observation in zip(states,observations): emissions[lookup[state],lookup[observation]] += 1
        if seen != set(STATES): raise ValueError('Training sequences must represent all movement states')
        if emission_pairs is not None:
            for state,observation in emission_pairs:
                emissions[lookup[state],lookup[observation]] += 1
        return cls({'version':VERSION,'states':list(STATES),
            'transition_matrix':(transitions/transitions.sum(axis=1,keepdims=True)).tolist(),
            'emission_matrix':(emissions/emissions.sum(axis=1,keepdims=True)).tolist(),
            'initial_probabilities':(initial/initial.sum()).tolist(),'pseudocount':pseudocount,
            'training_groups':sorted(groups),'held_out_groups':sorted(set(held_out_groups)),
            'transition_construction':'counts_from_labeled_synthetic_training_sequences',
            'emission_construction':'group_cross_validated_training_SVM_confusion' if emission_pairs is not None
                                     else 'labeled_training_state_observation_counts',
            'provenance':'synthetic_software_demo_temporal_parameters', 'validated_on_real_athletes':False,
            'decoder':'standard_log_space_Viterbi_dynamic_programming_numpy_argmax'})

    def decode(self, observations):
        if not observations: return []
        if not set(observations) <= set(self.states): raise ValueError('Unknown HMM observation')
        n = len(self.states)
        lookup = {state:i for i,state in enumerate(self.states)}
        score = np.log(self.initial)+np.log(self.emission[:,lookup[observations[0]]])
        backpointers = []
        for observation in observations[1:]:
            candidates = score[:,None]+np.log(self.transition)
            previous = np.argmax(candidates,axis=0)
            score = candidates[previous,np.arange(n)]+np.log(self.emission[:,lookup[observation]])
            backpointers.append(previous)
        state = int(np.argmax(score))
        path = [state]
        for previous in reversed(backpointers):
            state = int(previous[state])
            path.append(state)
        return [self.states[i] for i in reversed(path)]

    def smooth(self, window_output):
        result = copy.deepcopy(window_output)
        observations = [w['raw_svm_prediction'] for w in result['windows']]
        path = self.decode(observations)
        for window,prediction in zip(result['windows'],path):
            window['temporal_model_prediction'] = prediction
            window['athlete_confirmed_movement'] = None
        return {'status':result['status'],'version':VERSION,'reasons':result['reasons'],
                'windows':result['windows'],'model_metadata':copy.deepcopy(self.metadata),
                'prediction_is_confirmation':False}


def synthetic_temporal_model(model, training, held_out_groups=()):
    """Group CV confusion uses TRAINING groups only, never the held-out test set.

    Synthetic ordered bouts replay measured training windows. Bout durations and
    orders are engineered data construction, not athlete transition probabilities.
    """
    features = [extract_features(r['session'],model.config.profile)['values'] for r in training]
    labels = [r['label'] for r in training]
    groups = [r['group'] for r in training]
    if set(groups)&set(held_out_groups): raise ValueError('Train/test group overlap')
    predictions = cross_val_predict(clone(model.estimator),features,labels,
                                   groups=groups,cv=GroupKFold(n_splits=5))
    order = ['low_activity']*2+['walking_like']*4+['running_like']*4+['low_activity']+['repeated_jump_landing']*4+['squat_like_repetitions']*4
    sequences = []
    for variant in range(8):
        mapping = {r['label']:str(predictions[i]) for i,r in enumerate(training)
                   if r['group'].endswith(f'_{variant}')}
        if set(mapping)!=set(STATES): raise ValueError('Demo temporal training requires variants 0 through 7')
        # A processed clip need not begin at the start of a workout. Include
        # training starts in each class instead of imposing a low-activity prior.
        start = order.index(STATES[variant % len(STATES)])
        sequence_order = order[start:]+order[:start]
        sequences.append({'group':f'synthetic_temporal_train_{variant}','states':sequence_order,
                          'observations':[mapping[s] for s in sequence_order]})
    result = MovementHMM.fit(sequences,held_out_groups=held_out_groups,
                             emission_pairs=list(zip(labels,predictions.tolist())))
    result.metadata['emission_training_groups'] = sorted(set(groups))
    result.metadata['emission_cv'] = 'GroupKFold n_splits=5; scaler fitted separately per fold'
    result.metadata['synthetic_bout_order'] = order
    result.metadata['sequence_start_policy'] = 'rotate_synthetic_bouts_across_all_five_start_states'
    return result
