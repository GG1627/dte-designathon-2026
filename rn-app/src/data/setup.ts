export const movementLabels = {
  walking_like: 'Walking', running_like: 'Running',
  squat_like_repetitions: 'Squat / strength movement',
  repeated_jump_landing: 'Jump / Landing', other: 'Other / not sure',
} as const;
export type Movement = keyof typeof movementLabels;
export const activities = {
  basketball_training: 'Basketball', volleyball_training: 'Volleyball', soccer_training: 'Soccer',
  running: 'Running', plyometrics: 'Plyometrics', strength_training: 'Strength training', rehabilitation: 'Rehabilitation', other: 'Other',
} as const;
export type Activity = keyof typeof activities;
export const sensorLabels = { thigh_imu: 'Thigh sensor', shank_imu: 'Shank sensor', left_insole: 'Left insole', right_insole: 'Right insole' } as const;
export type SensorStatus = 'connected' | 'disconnected' | 'low_quality';
export type TaskKey = 'walking_calibration' | 'squat_check' | 'landing_check';
export type MovementTask = {
  status: 'pending' | 'complete' | 'skipped'; target: number; completed: number;
  predicted_movement: Movement | null; confirmed_movement: Movement | null;
};
export type SetupData = {
  setup_status: 'not_started' | 'in_progress' | 'complete'; step: number;
  sensors: Record<keyof typeof sensorLabels, SensorStatus>;
  fit_check: { status: 'pending' | 'complete'; seconds: number };
  walking_calibration: MovementTask; squat_check: MovementTask; landing_check: MovementTask;
  confirmed_activity: Activity | null; personal_reference: { status: 'learning' | 'provisional' };
};
export function createMockSetup(): SetupData {
  const task = (target: number, predicted_movement: Movement): MovementTask => ({ status: 'pending', target, completed: 0, predicted_movement, confirmed_movement: null });
  return {
    setup_status: 'not_started', step: 0,
    sensors: { thigh_imu: 'connected', shank_imu: 'connected', left_insole: 'connected', right_insole: 'connected' },
    fit_check: { status: 'pending', seconds: 0 },
    walking_calibration: task(20, 'walking_like'), squat_check: task(5, 'squat_like_repetitions'), landing_check: task(5, 'repeated_jump_landing'),
    confirmed_activity: null, personal_reference: { status: 'learning' },
  };
}
