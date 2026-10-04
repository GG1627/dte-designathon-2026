"""TEST/DEMO ONLY: deterministic five-class signals, not a real training dataset."""
import copy
import math
import numpy as np
from generate_mock_data import session, insole, knee
from generate_raw_sensor_fixture import imu_packet
from aligned_kinematics import reconstruct
from sensor_to_segment_calibration import calibrate_pair
from activity_svm import STATES


def ideal_calibration_records():
    # Separate synthetic upright-static + positive functional sweep for EACH pod.
    return {segment:{'static_accel':[[0,0,9.80665]]*30,
                     'positive_flexion_gyro':[[0,float(v),0] for v in np.linspace(.1,1,60)]}
            for segment in ('thigh','shank')}


def movement_fixture(label, variant=0, duration_s=6):
    if label not in STATES: raise ValueError('Unknown synthetic movement')
    data=session('balanced',duration_s=duration_s)
    data['session_id']=f'synthetic_{label}_{variant}'
    scale=1 + .02*(variant-4)
    periods={'low_activity':5.,'walking_like':1.,'running_like':.65,
             'squat_like_repetitions':1.8,'repeated_jump_landing':2.}
    period=periods[label]*(1+.015*(variant-4))
    durations={'walking_like':.65*period,'running_like':.3*period,'repeated_jump_landing':.6}
    force_events={}
    for foot in ('left','right'):
        offset=period/2 if foot=='left' and label in ('walking_like','running_like') else 0
        force_events[foot]=[{'start_s':float(t),'end_s':float(t+durations.get(label,.6)),
                            'force_scale':{'left':scale,'right':scale}}
                           for t in np.arange(.8+offset,duration_s,period)]
    raw=[]
    for row in data['samples']:
        t=row['timestamp_s']
        if label=='repeated_jump_landing':
            motion=knee(t,'right')
            angle=motion['flexion_rad']*scale
            velocity=motion['angular_velocity_rad_s']*scale
        else:
            amplitude={'low_activity':.002,'walking_like':.22,'running_like':.35,
                       'squat_like_repetitions':.6}[label]*scale
            omega=2*math.pi/period
            angle=amplitude*(1-math.cos(omega*t))
            velocity=amplitude*omega*math.sin(omega*t)
        frame={'sequence':row['sequence'],'timestamp_s':t,'right':{'imu':{
               'thigh':imu_packet(0,0),'shank':imu_packet(angle,velocity)}},'left':{}}
        for foot in ('left','right'):
            cells=data['insole_geometry'][foot]
            if label=='squat_like_repetitions':
                packet=insole(.3,foot,cells,.3,False,landings=[{'start_s':0,'end_s':.6,'force_scale':{'left':1,'right':1}}])
            else:
                packet=insole(t,foot,cells,1,False,landings=force_events[foot] if label!='low_activity' else [])
            frame[foot]['insole']=packet
        raw.append(frame)
    data['samples']=raw
    # Only one knee pair; source IDs describe the actual two pods plus both feet.
    data['sources']['left'].pop('knee')
    return data


def training_records(variants=range(8)):
    calibration=calibrate_pair(ideal_calibration_records())
    return [{'label':label,'group':f'train_{label}_{variant}',
             'session':reconstruct(movement_fixture(label,variant),calibration)}
            for label in STATES for variant in variants]


def held_out_records(variants=range(8,10)):
    return [{'label':r['label'],'group':r['group'].replace('train_','held_out_'),'session':r['session']}
            for r in training_records(variants)]
