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
  'Before your first session, Kintra needs a short setup so it can understand how your sensors are positioned and how you move.',
  'Check that all four sensors are ready.', 'Stand naturally and stay still for 10 seconds.',
  'Walk 20 comfortable steps at your normal pace.', 'Complete 5 comfortable squats.',
  'Complete 5 comfortable jump-landings.', 'What activity are you setting up Kintra for?',
  'Kintra is ready to record your sessions. Your personal movement reference will become more useful as Kintra collects more confirmed sessions.',
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
  const canContinue = step === 1 ? sensorsReady : step === 2 ? done && sensorsReady : task ? !!task.confirmed_movement && done && sensorsReady : step === 6 ? !!setup.confirmed_activity : true;
  return <Screen>
    <Row><Text type="label">Kintra setup</Text><Action onPress={() => { setRunning(false); if (router.canGoBack()) router.back(); else router.replace('/home'); }}>Save & close</Action></Row>
    <Row><Text type="small" themeColor="textSecondary">Step {step + 1} of 8</Text><Badge muted>Demo setup</Badge></Row>
    <View style={{ flexDirection: 'row', gap: s.one }}>{titles.map((title, index) => <View key={title} style={{ flex: 1, height: 3, borderRadius: 2, backgroundColor: index <= step ? c.accent : c.backgroundSelected }} />)}</View>
    <Text accessibilityRole="header" type="title">{titles[step]}</Text>
    <Text themeColor="textSecondary">{instructions[step]}</Text>
    {step === 0 ? <><Panel><Text type="subtitle">Fit. Move. Confirm.</Text><Text themeColor="textSecondary">A short setup now. A personal reference learned over future sessions.</Text></Panel><Text type="small" themeColor="textSecondary">Takes about 2–3 minutes. This preview uses simulated sensors and movement counts.</Text></> : null}
    {step === 1 ? <SensorStatusList sensors={setup.sensors} /> : null}
    {step === 2 ? <><TaskProgress value={setup.fit_check.seconds} target={10} label={done ? 'Fit check complete ?' : 'Stand naturally'} counter={done ? '10 / 10' : `${10 - setup.fit_check.seconds}s remaining`} /><SensorStatusList sensors={setup.sensors} quality /></> : null}
    {task && key ? <>
      {task.status === 'skipped' ? <Panel><Text>Jump / landing check skipped.</Text><Action onPress={() => setSetup(current => ({ ...current, landing_check: { ...createMockSetup().landing_check } }))}>Try this step</Action></Panel> : <>
        <TaskProgress value={task.completed} target={task.target} label={step === 3 ? 'Walking calibration · steps' : 'Movement check · reps'} />
        {done ? <MovementConfirmation key={key} predicted={task.predicted_movement} confirmed={task.confirmed_movement} options={options[key]} onConfirm={confirm} /> : <Text type="small" themeColor="textSecondary">{step === 3 ? 'Keep walking normally.' : 'Move at a comfortable pace.'}</Text>}
      </>}
      <Text type="small" themeColor="textSecondary">These counts are for the setup demo.</Text>
    </> : null}
    {step >= 1 && step <= 5 && !sensorsReady ? <Panel><Text>Check sensor fit and connection before continuing.</Text></Panel> : null}
    {(step === 2 || task) && !done && task?.status !== 'skipped' ? <SetupButton disabled={!sensorsReady || running} onPress={() => setRunning(true)}>{running ? 'Simulating movement…' : step === 2 ? 'Start fit check demo' : 'Start movement demo'}</SetupButton> : null}
    {step === 5 ? <Action onPress={() => {
      setRunning(false);
      setSetup(current => ({ ...current, step: 6, landing_check: { ...current.landing_check, status: 'skipped', completed: 0, confirmed_movement: null } }));
    }}>Skip this step</Action> : null}
    {step === 6 ? <ActivitySelection selected={setup.confirmed_activity} onSelect={activity => setSetup(current => ({ ...current, confirmed_activity: activity }))} /> : null}
    {step === 7 ? <SetupSummary setup={setup} /> : null}
    <SetupButton disabled={!canContinue && !(task?.status === 'skipped')} onPress={() => {
      if (step === 7) { setSetup(current => ({ ...current, setup_status: 'complete' })); router.replace('/home'); }
      else go(step + 1);
    }}>{step === 0 ? 'Start setup' : step === 7 ? 'Start using Kintra' : 'Continue'}</SetupButton>
    {step > 0 ? <Action onPress={() => go(step - 1)}>Back</Action> : null}
    <Text type="small" themeColor="textSecondary">Simulated data · no hardware connection</Text>
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
