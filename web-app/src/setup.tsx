import { useEffect, useState, type Dispatch, type SetStateAction } from 'react';
import { activities, createMockSetup, movementLabels, sensorLabels, type SetupData, type Movement, type TaskKey, type Activity } from '../../rn-app/src/data/setup';
import { Badge } from './ui';

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
  squat_check: ['squat_like_repetitions', 'other'], landing_check: ['repeated_jump_landing', 'other'],
};
export function Setup({ setup, setSetup, active, onClose }: { setup: SetupData; setSetup: Dispatch<SetStateAction<SetupData>>; active: boolean; onClose: () => void }) {
  const [running, setRunning] = useState(false);
  const step = setup.step, key = taskKeys[step], task = key ? setup[key] : null;
  const done = step === 2 ? setup.fit_check.seconds >= 10 : !!task && task.completed >= task.target;
  useEffect(() => {
    if (!active || !running || done) return;
    const timer = setInterval(() => setSetup((current) => {
      if (step === 2) return { ...current, fit_check: { seconds: Math.min(10, current.fit_check.seconds + 1), status: 'pending' } };
      return key ? { ...current, [key]: { ...current[key], completed: Math.min(current[key].target, current[key].completed + 1) } } : current;
    }), 1000);
    return () => clearInterval(timer);
  }, [active, running, done, step, key, setSetup]);
  function go(next: number) { setRunning(false); setSetup((current) => ({ ...current, step: next })); }
  function next() {
    setRunning(false);
    setSetup((current) => ({ ...current,
      step: Math.min(7, step + 1), setup_status: step === 7 ? 'complete' : 'in_progress',
      ...(step === 1 ? { sensors: createMockSetup().sensors } : {}),
      ...(step === 2 ? { fit_check: { seconds: 10, status: 'complete' as const } } : {}),
      ...(key && current[key].status !== 'skipped' ? { [key]: { ...current[key], completed: current[key].target, status: 'complete', confirmed_movement: current[key].confirmed_movement ?? current[key].predicted_movement ?? 'other' } } : {}),
      ...(step === 6 ? { confirmed_activity: current.confirmed_activity ?? 'strength_training', personal_reference: { status: 'provisional' as const } } : {}),
    }));
    if (step === 7) onClose();
  }
  return <div className="stack setup-screen">
    <div className="row"><span className="label">Kintra setup</span><button className="text-button" onClick={() => { setRunning(false); onClose(); }}>Save & close</button></div>
    <div className="row wrap"><span className="muted small">Step {step + 1} of 8</span><Badge>Demo setup</Badge></div>
    <div className="setup-steps" aria-hidden="true">{titles.map((title, i) => <span key={title} className={i <= step ? 'complete' : ''}/>)}</div>
    <h1>{titles[step]}</h1><p className="muted">{instructions[step]}</p>
    {step === 0 ? <section className="panel"><h2>Fit. Move. Confirm.</h2><p className="muted">Simulated checks and an example personal history. No waiting required.</p></section> : null}
    {step === 1 || step === 2 ? <section className="panel">{Object.entries(sensorLabels).map(([id, label]) => <div className="row wrap" key={id}><strong>{label}</strong><span className={setup.sensors[id as keyof typeof sensorLabels] === 'connected' ? 'muted' : 'warning'}>{setup.sensors[id as keyof typeof sensorLabels] === 'connected' ? step === 2 ? 'Signal ready' : 'Connected' : 'Demo sensor unavailable'}</span></div>)}</section> : null}
    {step === 2 || task ? <section className="panel"><h3>{step === 2 ? done ? 'Fit check complete' : 'Stand naturally' : step === 3 ? 'Walking calibration · steps' : 'Movement check · reps'}</h3><progress aria-label={step === 2 ? 'Fit check' : 'Movement check'} max={step === 2 ? 10 : task!.target} value={step === 2 ? setup.fit_check.seconds : task!.completed}/><span className="muted small">{step === 2 ? `${setup.fit_check.seconds} / 10 seconds` : task!.status === 'skipped' ? 'Jump / landing check skipped' : `${task!.completed} / ${task!.target}`}</span>
      {task && key && task.status !== 'skipped' ? <><label>Confirm movement<select aria-describedby="movement-demo-note" value={task.confirmed_movement ?? task.predicted_movement ?? 'other'} onChange={(e) => setSetup((current) => ({ ...current, [key]: { ...current[key], confirmed_movement: e.target.value as Movement } }))}>{options[key].map((movement) => <option value={movement} key={movement}>{movementLabels[movement]}</option>)}</select></label><p id="movement-demo-note" className="muted small">These counts are for the setup demo.</p></> : null}
      {!done && task?.status !== 'skipped' ? <button onClick={() => setRunning(!running)}>{running ? 'Pause demo timer' : 'Play demo timer'}</button> : null}
    </section> : null}
    {step === 5 ? <button onClick={() => { setRunning(false); setSetup((current) => ({ ...current, step: 6, landing_check: { ...current.landing_check, status: 'skipped', completed: 0, confirmed_movement: null } })); }}>Skip this step</button> : null}
    {step === 6 ? <fieldset className="intent-check"><legend>Activity</legend><div className="activity-options">{Object.entries(activities).map(([value, label]) => <label key={value} className={`radio-choice ${(setup.confirmed_activity ?? 'strength_training') === value ? 'selected' : ''}`}><input type="radio" name="setup-activity" value={value} checked={(setup.confirmed_activity ?? 'strength_training') === value} onChange={() => setSetup((current) => ({ ...current, confirmed_activity: value as Activity }))}/>{label}</label>)}</div></fieldset> : null}
    {step === 7 ? <section className="panel"><h2>Example history</h2><p>{activities[setup.confirmed_activity ?? 'strength_training']}</p><p className="muted">This preview uses earlier simulated sessions. Setup checks do not learn a personal baseline.</p>{setup.landing_check.status === 'skipped' ? <p className="muted small">Jump / landing check skipped. You can try it another time.</p> : null}</section> : null}
    <div className="actions"><button className="primary" onClick={next}>{step === 0 ? 'Start setup' : step === 7 ? 'Start using Kintra' : 'Continue'}</button>{step > 0 ? <button onClick={() => go(step - 1)}>Back</button> : null}</div>
    <p className="muted small">Simulated data · no hardware connection{step >= 1 && step <= 5 ? ' · Continue completes this demo step immediately.' : ''}</p>
  </div>;
}
