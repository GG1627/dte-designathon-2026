import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { View } from 'react-native';
import { Action, Badge, Panel, Row, Screen } from '@/components/monitoring-ui';
import { useSetup } from '@/components/setup-provider';
import { ActivitySelection, MovementConfirmation, SensorStatusList, SetupButton, SetupSummary, TaskProgress } from '@/components/setup-ui';
import { ThemedText as Text } from '@/components/themed-text';
import { Palette as c, Spacing as s } from '@/constants/theme';
import { createMockSetup, type Movement, type TaskKey } from '@/data/setup';

const titles = ['Welcome to Kintra', 'Sensor check', 'Fit check', 'Walk naturally', 'Controlled squats', 'Jump / landing check', 'Activity context', 'Kintra is ready'];
const instructions = [
  'Preview sensor fit and movement checks. Continue at any time to move through the demo.',
  'Check that all four sensors are ready.', 'Stand naturally and stay still for 10 seconds.',
  'Walk 20 comfortable steps at your normal pace.', 'Complete 5 comfortable squats.',
  'Complete 5 comfortable jump-landings.', 'What activity are you setting up Kintra for?',
  'Your demo history is ready. Explore movement readings and feedback based on earlier simulated sessions.',
];
const taskKeys: Record<number, TaskKey> = { 3: 'walking_calibration', 4: 'squat_check', 5: 'landing_check' };
const options: Record<TaskKey, Movement[]> = {
  walking_calibration: ['walking_like', 'running_like', 'other'],
  squat_check: ['squat_like_repetitions', 'other'],
  landing_check: ['repeated_jump_landing', 'squat_like_repetitions', 'other'],
};
export default function SetupScreen() {
  const { setup, setSetup } = useSetup();
  const [running, setRunning] = useState(false);
  const [details, setDetails] = useState(false);
  const step = setup.step;
  const key = taskKeys[step];
  const task = key ? setup[key] : null;
  const sensorsReady = Object.values(setup.sensors).every(status => status === 'connected');
  const done = step === 2 ? setup.fit_check.status === 'complete' : task ? task.completed >= task.target : false;
  useEffect(() => {
    if (!running || !sensorsReady || done) return;
    const timer = setInterval(() => setSetup(current => {
      if (step === 2) {
        const seconds = Math.min(10, current.fit_check.seconds + 1);
        return { ...current, fit_check: { seconds, status: seconds === 10 ? 'complete' : 'pending' } };
      }
      if (!key) return current;
      const completed = Math.min(current[key].target, current[key].completed + 1);
      return { ...current, [key]: { ...current[key], completed } };
    }), step === 3 ? 350 : 1000);
    return () => clearInterval(timer);
  }, [running, sensorsReady, done, step, key, setSetup]);
  const go = (next: number) => {
    setRunning(false);
    setSetup(current => ({ ...current, step: next, setup_status: 'in_progress' }));
  };
  const confirm = (movement: Movement) => {
    if (key) setSetup(current => ({ ...current, [key]: { ...current[key], confirmed_movement: movement, status: 'complete' } }));
  };
  return <Screen>
    <Row><Text type="label">Kintra setup</Text><Action onPress={() => { setRunning(false); if (router.canGoBack()) router.back(); else router.replace('/home'); }}>Save & close</Action></Row>
    <Row><Text type="small" themeColor="textSecondary">Step {step + 1} of 8</Text><Badge muted>Demo setup</Badge></Row>
    <View style={{ flexDirection: 'row', gap: s.one }}>{titles.map((title, index) => <View key={title} style={{ flex: 1, height: 3, borderRadius: 2, backgroundColor: index <= step ? c.accent : c.backgroundSelected }} />)}</View>
    <Text accessibilityRole="header" type="title">{titles[step]}</Text>
    <Text themeColor="textSecondary">{instructions[step]}</Text>
    {step === 0 ? <Panel><Text type="subtitle">Fit. Move. Confirm.</Text><Text themeColor="textSecondary">Simulated checks and an example personal history. No waiting required.</Text></Panel> : null}
    {step === 1 ? <SensorStatusList sensors={setup.sensors} /> : null}
    {step === 2 ? <><TaskProgress value={setup.fit_check.seconds} target={10} label={done ? 'Fit check complete' : 'Stand naturally'} counter={done ? '10 / 10' : `${10 - setup.fit_check.seconds}s remaining`} /><SensorStatusList sensors={setup.sensors} quality /></> : null}
    {task && key ? <>
      {task.status === 'skipped' ? <Panel><Text>Jump / landing check skipped.</Text><Action onPress={() => setSetup(current => ({ ...current, landing_check: { ...createMockSetup().landing_check } }))}>Try this step</Action></Panel> : <>
        <TaskProgress value={task.completed} target={task.target} label={step === 3 ? 'Walking calibration · steps' : 'Movement check · reps'} />
        <MovementConfirmation key={key} predicted={task.predicted_movement} confirmed={task.confirmed_movement} options={options[key]} onConfirm={confirm} />
      </>}
      <Text type="small" themeColor="textSecondary">These counts are for the setup demo.</Text>
    </> : null}
    {step >= 1 && step <= 5 && !sensorsReady ? <Panel><Text>Demo sensor unavailable. Continue previews a restored connection.</Text></Panel> : null}
    {(step === 2 || task) && !done && task?.status !== 'skipped' ? <Action onPress={() => setRunning(value => !value)}>{running ? 'Pause demo timer' : 'Play demo timer'}</Action> : null}
    {step === 5 ? <Action onPress={() => {
      setRunning(false);
      setSetup(current => ({ ...current, step: 6, landing_check: { ...current.landing_check, status: 'skipped', completed: 0, confirmed_movement: null } }));
    }}>Skip this step</Action> : null}
    {step === 6 ? <ActivitySelection selected={setup.confirmed_activity ?? 'strength_training'} onSelect={activity => setSetup(current => ({ ...current, confirmed_activity: activity }))} /> : null}
    {step === 7 ? <SetupSummary setup={setup} /> : null}
    <SetupButton onPress={() => {
      setRunning(false);
      setSetup(current => ({ ...current,
        step: Math.min(7, step + 1), setup_status: step === 7 ? 'complete' : 'in_progress',
        ...(step === 1 ? { sensors: createMockSetup().sensors } : {}),
        ...(step === 2 ? { fit_check: { seconds: 10, status: 'complete' as const } } : {}),
        ...(key && current[key].status !== 'skipped' ? { [key]: { ...current[key],
          completed: current[key].target, status: 'complete',
          confirmed_movement: current[key].confirmed_movement ?? current[key].predicted_movement ?? 'other' } } : {}),
        ...(step === 6 ? { confirmed_activity: current.confirmed_activity ?? 'strength_training',
          personal_reference: { status: 'provisional' as const } } : {}),
      }));
      if (step === 7) router.replace('/home');
    }}>{step === 0 ? 'Start setup' : step === 7 ? 'Start using Kintra' : 'Continue'}</SetupButton>
    {step > 0 ? <Action onPress={() => go(step - 1)}>Back</Action> : null}
    <Text type="small" themeColor="textSecondary">Simulated data · no hardware connection{step >= 1 && step <= 5 ? '\nContinue completes this demo step immediately.' : ''}</Text>
    {step >= 1 && step <= 5 ? <>
      <Action onPress={() => setDetails(value => !value)}>{details ? 'Hide demo controls' : 'Demo controls'}</Action>
      {details ? <Panel>
        <Text type="small" themeColor="textSecondary">Preview connection and recovery states.</Text>
        <Action onPress={() => { setRunning(false); setSetup(current => ({ ...current, sensors: { ...current.sensors, thigh_imu: 'disconnected' } })); }}>Disconnect thigh sensor</Action>
        <Action onPress={() => { setRunning(false); setSetup(current => ({ ...current, sensors: { ...current.sensors, thigh_imu: 'low_quality' } })); }}>Simulate low-quality signal</Action>
        <Action onPress={() => setSetup(current => ({ ...current, sensors: createMockSetup().sensors }))}>Restore sensors</Action>
        {key ? <Action onPress={() => setSetup(current => ({ ...current, [key]: { ...current[key], predicted_movement: null, confirmed_movement: null, status: 'pending' } }))}>Simulate unrecognized movement</Action> : null}
        {(step === 2 || key) ? <Action onPress={() => { setRunning(false); setSetup(current => key ? ({ ...current, [key]: createMockSetup()[key] }) : ({ ...current, fit_check: createMockSetup().fit_check })); }}>Try again</Action> : null}
      </Panel> : null}
    </> : null}
  </Screen>;
}
