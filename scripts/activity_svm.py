"""Broad movement candidates using StandardScaler + SVC; never sport or truth."""
from dataclasses import dataclass
import numpy as np
import scipy
import sklearn
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from biomechanical_events import extract_events, EventProtocol
from signal_preprocessing import PROFILES

VERSION = 'movement-svm/1.0.0'
FEATURE_SCHEMA = 'one-knee-motion-bilateral-feet/1.0.0'
STATES = ('low_activity','walking_like','running_like','squat_like_repetitions','repeated_jump_landing')
MOTION_FEATURES = ('knee_rom_rad','knee_mean_rad','knee_velocity_rms_rad_s',
                   'knee_peak_velocity_rad_s','knee_velocity_std_rad_s','dominant_velocity_frequency_hz',
                   'thigh_gyro_rms_rad_s','shank_gyro_rms_rad_s')
FOOT_FEATURES = tuple(f'{side}_{name}' for side in ('left','right') for name in
                     ('mean_force_bw','peak_force_bw','supported_fraction','contacts_per_s','mean_contact_time_s'))
PRIMARY_FEATURES = (*MOTION_FEATURES,*FOOT_FEATURES,'bilateral_pairs_per_s')


@dataclass(frozen=True)
class SVMConfig:
    profile: str = 'imu_pair_plus_insole'
    C: float = 10.0
    gamma: str = 'scale'
    kernel: str = 'rbf'
    provenance: str = 'synthetic_software_demo_model_parameters'

    def __post_init__(self):
        if self.profile not in PROFILES or not np.isfinite(self.C) or self.C <= 0:
            raise ValueError('Valid profile and positive C required')
        if self.gamma != 'scale' or self.kernel != 'rbf' or not self.provenance:
            raise ValueError('This version supports explicit RBF/scale configuration')


def feature_names(profile):
    if profile not in PROFILES:
        raise ValueError('Unknown feature profile')
    return PRIMARY_FEATURES if profile == 'imu_pair_plus_insole' else MOTION_FEATURES


def extract_features(processed, profile='imu_pair_plus_insole', events=None, protocol=EventProtocol()):
    """Only measured samples and acquisition units/rate enter features.

    Window features use the same canonical event output as biomechanics. Labels,
    annotations, session identity, phases and ground truth are never read.
    """
    names = feature_names(profile)
    rows = processed['samples']
    side = processed['monitored_knee_side']
    if len(rows) < 3:
        raise ValueError('Insufficient movement feature samples')
    angles = np.array([r[side]['knee']['flexion_rad'] for r in rows],float)
    velocity = np.array([r[side]['knee']['angular_velocity_rad_s'] for r in rows],float)
    if not np.isfinite(angles).all() or not np.isfinite(velocity).all() or any(
        r[side]['knee'].get('quality',{}).get('valid') is not True for r in rows):
        raise ValueError('Invalid movement samples')
    times = np.array([r['timestamp_s'] for r in rows],float)
    rate = processed['sampling']['rate_hz']
    if not np.isfinite(times).all() or not np.isfinite(rate) or rate <= 0 or not np.allclose(
        np.diff(times),1/rate,rtol=0,atol=1e-8):
        raise ValueError('Movement feature timestamps must be continuous')
    spectral = np.abs(np.fft.rfft(velocity-velocity.mean()))
    frequency = float(np.fft.rfftfreq(len(velocity),1/rate)[np.argmax(spectral)]) if spectral.max() > 1e-10 else 0.
    rms = lambda v: float(np.sqrt(np.mean(np.square(v))))
    features = [float(np.ptp(angles)),float(angles.mean()),rms(velocity),float(np.max(np.abs(velocity))),
                float(velocity.std()),frequency]
    for segment in ('thigh','shank'):
        gyro = np.array([r[side]['segment_gyro_rad_s'][segment] for r in rows],float)
        if not np.isfinite(gyro).all(): raise ValueError('Invalid segment gyro features')
        features.append(rms(gyro))
    event_source = None
    if profile == 'imu_pair_plus_insole':
        events = events if events is not None else extract_events(processed,protocol)
        if events['status'] != 'ready':
            raise ValueError('Canonical events unavailable: '+','.join(events['reasons']))
        event_source = events['version']
        mass = processed['participant'].get('mass_kg')
        if isinstance(mass,bool) or not isinstance(mass,(int,float)) or not np.isfinite(mass) or mass <= 0:
            raise ValueError('Body weight normalization requires valid mass')
        duration = times[-1]-times[0]
        for foot in ('left','right'):
            force = np.array([r[foot]['insole']['plantar_normal_force_n'] for r in rows])/(mass*9.80665)
            contacts = [c for c in events['contacts'] if c['side']==foot]
            features.extend([float(force.mean()),float(force.max()),
                float(np.mean(force*mass*9.80665 > protocol.contact_threshold_n)),len(contacts)/duration,
                float(np.mean([c['contact_time_s'] for c in contacts])) if contacts else 0.])
        features.append(len(events['bilateral_pairs'])/duration)
    if not np.isfinite(features).all(): raise ValueError('Nonfinite feature vector')
    return {'values':features,'names':list(names),'schema_version':FEATURE_SCHEMA,'profile':profile,
            'event_source':event_source,'absence_encoding':'zero_complete_contact_count; never missing-to-zero'}


class MovementModel:
    def __init__(self, config=SVMConfig()):
        self.config = config
        self.estimator = make_pipeline(StandardScaler(),SVC(C=config.C,kernel=config.kernel,
                gamma=config.gamma,probability=False,decision_function_shape='ovr'))
        self.metadata = None

    def fit(self, records, held_out_groups=()):
        groups = [r['group'] for r in records]
        if not records or set(groups) & set(held_out_groups):
            raise ValueError('Train and test session groups must be disjoint')
        labels = [r['label'] for r in records]
        if set(labels) != set(STATES): raise ValueError('Training requires all five broad movement classes')
        features = [extract_features(r['session'],self.config.profile)['values'] for r in records]
        self.estimator.fit(features,labels)
        self.metadata = {'version':VERSION,'feature_schema_version':FEATURE_SCHEMA,
            'feature_names':list(feature_names(self.config.profile)),'profile':self.config.profile,
            'kernel':self.config.kernel,'C':self.config.C,'gamma':self.config.gamma,
            'scaler':'StandardScaler fitted on training groups only','probability':False,
            'provenance':self.config.provenance,'training_groups':sorted(set(groups)),
            'held_out_groups':sorted(set(held_out_groups)), 'training_record_count':len(records),
            'validated_on_real_athletes':False,
            'libraries':{'numpy':np.__version__,'scipy':scipy.__version__,'scikit-learn':sklearn.__version__}}
        return self

    def predict(self, session, events=None, protocol=EventProtocol()):
        if self.metadata is None: raise ValueError('Movement model not fitted')
        features = extract_features(session,self.config.profile,events,protocol)
        scores = self.estimator.decision_function([features['values']])[0]
        return {'status':'ready','version':VERSION,'raw_svm_prediction':str(self.estimator.predict([features['values']])[0]),
            'model_decision_scores':dict(zip(self.estimator.classes_.tolist(),scores.tolist())),
            'features':features,'athlete_confirmed_movement':None,'prediction_is_confirmation':False}
