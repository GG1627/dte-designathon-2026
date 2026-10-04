import { useEffect, useRef, useState } from 'react';
import { analyzeBends, movementPresets, simulateSample, SAMPLE_INTERVAL_MS, type LiveSample, type MovementPreset, type BendGoal, type BendSet } from './shared';
import { SerialConnection, SERIAL_ASSUMPTIONS, serialSupport, type SerialRecord, type SerialState } from './serial';
import { Badge, KneeDiagram, Modal, RawReadings } from './ui';
import { Feedback } from './feedback';
import { downloadJson, loadSets, saveSets } from './storage';

type Capture = { source: LiveSample['source']; preset: MovementPreset; goal: BendGoal; samples: LiveSample[]; records: SerialRecord[]; startedAt: string };
type Review = Capture & { endedAt: string; set: BendSet | null };
const LIMIT = 6000;

export function Live({ active }: { active: boolean }) {
  const [source, setSource] = useState<LiveSample['source']>('simulated');
  const [preset, setPreset] = useState<MovementPreset>('slow');
  const [sample, setSample] = useState<LiveSample | null>(() => simulateSample('slow', 0));
  const [playing, setPlaying] = useState(false), [recording, setRecording] = useState(false);
  const [review, setReview] = useState<Review | null>(null), [detail, setDetail] = useState(false);
  const [serialState, setSerialState] = useState<SerialState>('disconnected');
  const [notice, setNotice] = useState<string | null>(null), [serialError, setSerialError] = useState<string | null>(null);
  const [zero, setZero] = useState(0), [goalKind, setGoalKind] = useState<BendGoal['kind']>('observe');
  const [target, setTarget] = useState(''), [saved, setSaved] = useState(false);
  const [stored, setStored] = useState(loadSets);
  const [events, setEvents] = useState<SerialRecord[]>([]), [received, setReceived] = useState(0);
  const [visible, setVisible] = useState(!document.hidden);
  const connection = useRef<SerialConnection | null>(null), capture = useRef<Capture | null>(null);
  const sequence = useRef(0), lastTick = useRef(Date.now()), latestHardware = useRef<LiveSample | null>(null);
  const journal = useRef<SerialRecord[]>([]), packetCount = useRef(0);
  const finishRef = useRef<() => void>(() => {});
  const support = serialSupport();

  function finish() {
    const captured = capture.current;
    if (!captured) return;
    capture.current = null; setRecording(false); setPlaying(false);
    const set: BendSet | null = captured.source === 'simulated' ? {
      id: crypto.randomUUID(), createdAt: captured.startedAt, preset: captured.preset, goal: captured.goal,
      checkIn: { setup: 'unknown', effort: 'unknown' }, analysis: analyzeBends(captured.samples),
    } : null;
    setReview({ ...captured, endedAt: new Date().toISOString(), set }); setSaved(false);
  }
  finishRef.current = finish;
  useEffect(() => {
    const listener = () => setVisible(!document.hidden);
    document.addEventListener('visibilitychange', listener);
    return () => document.removeEventListener('visibilitychange', listener);
  }, []);
  useEffect(() => {
    if (source !== 'simulated' || !playing || !active || !visible) return;
    const timer = setInterval(() => {
      const now = Date.now();
      sequence.current += Math.max(1, Math.round((now - lastTick.current) / SAMPLE_INTERVAL_MS)); lastTick.current = now;
      const next = simulateSample(preset, sequence.current); setSample(next);
      if (capture.current?.source === 'simulated') {
        capture.current.samples.push(next);
        if (capture.current.samples.length >= LIMIT) { finishRef.current(); setNotice('The 6,000-sample limit was reached. Your set is ready to review.'); }
      }
    }, SAMPLE_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [source, playing, preset, active, visible]);
  useEffect(() => {
    if (source !== 'hardware') return;
    const timer = setInterval(() => { setSample(latestHardware.current); setEvents([...journal.current]); setReceived(packetCount.current); }, 100);
    return () => clearInterval(timer);
  }, [source]);
  useEffect(() => () => { void connection.current?.dispose(); }, []);

  function reset(next: MovementPreset = preset) {
    setPlaying(false); sequence.current = 0; lastTick.current = Date.now(); setPreset(next);
    setSample(source === 'simulated' ? simulateSample(next, 0) : latestHardware.current); setZero(0); setNotice(null);
  }
  function switchSource(next: LiveSample['source']) {
    setSource(next); setReview(null); setSaved(false); setPlaying(false); setZero(0); setNotice(null);
    sequence.current = 0; lastTick.current = Date.now();
    setSample(next === 'simulated' ? simulateSample(preset, 0) : latestHardware.current);
  }
  async function connect() {
    if (!support.api) return;
    if (!connection.current) connection.current = new SerialConnection(support.api, (record) => {
      journal.current = [...journal.current.slice(-99), record];
      if (record.sample) { latestHardware.current = record.sample; packetCount.current++; }
      if (capture.current?.source === 'hardware') {
        capture.current.records.push(record);
        if (record.sample) capture.current.samples.push(record.sample);
        if (capture.current.samples.length >= LIMIT || capture.current.records.length >= LIMIT * 2) {
          finishRef.current(); setNotice('Recording limit reached. All captured packets remain available for export.');
        }
      }
    }, (state, message) => {
      setSerialState(state); setSerialError(message ?? null);
      if (['disconnected', 'error'].includes(state)) {
        latestHardware.current = null;
        if (capture.current?.source === 'hardware') { finishRef.current(); setNotice('Connection ended. Review and export the interrupted recording.'); }
      }
    });
    await connection.current.connect();
  }
  function start() {
    const chosen = goalKind === 'observe' ? null : Number(target);
    if (source === 'simulated' && goalKind !== 'observe' && (!target.trim() || !Number.isFinite(chosen) || chosen! <= 0 || (goalKind === 'depth' && chosen! > 180))) {
      setNotice('Enter a positive target. Bend-depth targets must be 180° or less.'); return;
    }
    reset(); setReview(null); setSaved(false);
    capture.current = { source, preset, goal: { kind: source === 'hardware' ? 'observe' : goalKind, target: source === 'hardware' ? null : chosen },
      samples: source === 'simulated' ? [simulateSample(preset, 0)] : [], records: [], startedAt: new Date().toISOString() };
    setRecording(true); if (source === 'simulated') setPlaying(true);
  }
  function exportReview() {
    if (!review) return;
    downloadJson({ schema: 'kintra.web.inspection/1', ...review, assumptions: review.source === 'hardware' ? SERIAL_ASSUMPTIONS : undefined,
      canonicalSession: false, interpretation: review.source === 'hardware' ? 'blocked: calibration, angle estimation and segmentation unvalidated' : 'simulated descriptive feedback' }, `kintra-${review.source}-${review.startedAt.replace(/[:.]/g, '-')}.json`);
  }
  const angle = sample && sample.thigh.valid && sample.shank.valid ? sample.shank.angleDeg - sample.thigh.angleDeg - zero : null;
  const hardware = source === 'hardware';
  return <div className="stack"><div className="row wrap"><h1>Live movement</h1><Badge hardware={hardware}>{hardware ? 'Hardware · inspection only' : 'Simulated data'}</Badge></div>
    <div className="row wrap"><div className="segmented" aria-label="Data source">{(['simulated', 'hardware'] as const).map((v) => <button key={v} aria-pressed={source === v} disabled={recording || ['connecting', 'disconnecting'].includes(serialState)} onClick={() => switchSource(v)}>{v === 'simulated' ? 'Simulation' : 'USB serial'}</button>)}</div><span className="muted">{review ? 'Set complete · Review' : recording ? hardware || playing && active && visible ? 'Recording set' : 'Set paused' : hardware ? serialState : playing && active && visible ? 'Preview playing' : 'Preview paused'}</span></div>
    {notice ? <p role="status" className="warning">{notice}</p> : null}
    {hardware ? <section className="panel"><div className="row wrap"><h2>Serial device</h2><Badge hardware>{serialState}</Badge></div><p className="muted">115200 baud · newline-delimited JSON</p><p>Hardware exercise feedback is blocked until calibration, angle estimation, and segmentation are validated.</p><p className="warning">Device units are unconfirmed: timestamps in ms, acceleration in g, gyro in °/s. Confirm against firmware on the actual device.</p><div className="actions"><button className="primary" disabled={!support.api || !['disconnected', 'error'].includes(serialState)} onClick={() => void connect()}>Connect device</button><button disabled={serialState === 'disconnected' || serialState === 'disconnecting'} onClick={() => void connection.current?.disconnect()}>Disconnect</button><button onClick={() => setDetail(true)}>Packet details</button></div>{support.reason ? <p className="warning">{support.reason}</p> : null}{serialError ? <p role="alert" className="warning">{serialError}</p> : null}</section> : null}
    {review ? <>
      {review.set ? <Feedback set={review.set} history={stored.sets} saved={saved} error={stored.error} onCheckIn={(checkIn) => setReview({ ...review, set: { ...review.set!, checkIn } })} onSave={() => {
        const next = [review.set!, ...stored.sets.filter((s) => s.id !== review.set!.id)].slice(0, 30);
        const error = saveSets(next); setStored({ sets: error ? stored.sets : next, error }); setSaved(!error);
      }} onNew={() => { setReview(null); reset(); }}/> : <section className="panel accent-panel"><Badge hardware>Hardware recording</Badge><h2>Movement estimate needs validation</h2><p>Use the sensor display for inspection. Validate calibration, angle estimation, and segmentation before using exercise feedback.</p><p>{review.samples.length} received samples · {review.records.filter((r) => r.kind === 'error' || r.kind === 'interruption' || r.message).length} error or interruption records</p><p className="muted">Raw timestamps, source fields, invalid readings, and packet errors are retained in the export. No exercise metrics or personal comparisons are produced.</p><div className="actions"><button onClick={() => setDetail(true)}>Recording evidence</button><button onClick={() => { setReview(null); reset(); }}>New set</button></div></section>}
      <button onClick={exportReview}>Export {review.source === 'hardware' ? 'hardware recording' : 'simulated set'} JSON</button>
    </> : <div className="live-grid"><section className="panel angle-panel"><div className="row wrap"><span className="label">{hardware ? 'Relative debug angle' : 'Knee flexion'}</span><span className="muted small">{hardware ? 'Unvalidated estimate' : 'Simulated angle'}</span></div><button className="plain angle-reading" onClick={() => setDetail(true)} aria-label="Explain the current knee angle"><strong className="metric orange">{angle === null || !Number.isFinite(angle) ? '—' : `${angle.toFixed(1)}°`}</strong><span className="orange small">Reading details ↗</span></button><KneeDiagram sample={sample}/><div className="row small muted"><span className="blue">Thigh</span><span className="orange">Shank</span></div></section>
      <div className="stack">{!hardware ? <section className="panel"><label>Movement<select value={preset} disabled={recording} onChange={(e) => reset(e.target.value as MovementPreset)}>{movementPresets.map((p) => <option value={p.id} key={p.id}>{p.label}</option>)}</select></label></section> : null}
      <section className="panel"><h2>{recording ? 'Your set is recording' : hardware ? 'Record sensor packets' : 'Set focus'}</h2>{!recording && !hardware ? <><label>Focus<select value={goalKind} onChange={(e) => { setGoalKind(e.target.value as BendGoal['kind']); setTarget(''); }}><option value="observe">Observe my movement</option><option value="depth">My chosen bend depth</option><option value="pace">My chosen rep pace</option></select></label>{goalKind !== 'observe' ? <label>{goalKind === 'depth' ? 'Deepest bend target (degrees)' : 'Rep duration target (seconds)'}<input inputMode="decimal" type="number" min="0" max={goalKind === 'depth' ? 180 : undefined} value={target} onChange={(e) => setTarget(e.target.value)}/><span className="muted small">Use a target from your exercise plan.</span></label> : null}</> : null}
      <p className="muted">{recording ? `${capture.current?.samples.length ?? 0} samples captured${hardware ? '' : ' · finish after complete bends'}` : hardware ? 'Records stay in this visit until you export them. Reconnects start a new recording.' : 'Complete a bend and return, then finish the set to review.'}</p><button className="primary" disabled={hardware && serialState !== 'connected' && !recording} onClick={recording ? finish : start}>{recording ? 'Finish set' : 'Start set'}</button></section>
      {!hardware ? <section className="panel"><h3>Preview controls</h3><div className="actions"><button onClick={() => {
        if (!playing && !recording) lastTick.current = Date.now();
        setPlaying(!playing);
      }}>{playing ? 'Pause' : 'Play'}</button><button disabled={recording} onClick={() => setZero(sample!.shank.angleDeg - sample!.thigh.angleDeg)}>Zero knee</button><button disabled={recording} onClick={() => reset()}>Reset</button></div><p className="muted small">Zeroing changes the display only. Analysis uses the original segment angles.</p></section> : <section className="panel"><h3>Packet stream</h3><p>{received.toLocaleString()} packets received</p><p className="muted small">Receiver sequence and field checks do not establish measured hardware quality.</p>{events.filter((e) => e.kind === 'error' || e.kind === 'interruption' || e.message).slice(-3).map((e, i) => <p className="warning small" key={i}>{e.message}</p>)}</section>}
      </div></div>}
    {!hardware && !recording && stored.sets.length ? <section className="stack"><h2>Saved knee-bend sets</h2>{stored.sets.slice(0, 5).map((set) => <button className="panel record-row" key={set.id} onClick={() => { setPlaying(false); setSaved(true); setReview({ source: 'simulated', preset: set.preset, goal: set.goal, startedAt: set.createdAt, endedAt: set.createdAt, samples: [], records: [], set }); }}><span><strong>{movementPresets.find((p) => p.id === set.preset)?.label} · {set.analysis.reps.length} bends ↗</strong><span className="muted small">{new Date(set.createdAt).toLocaleString()} · Simulated</span></span><span className="orange">{set.analysis.medianRangeDeg === null ? '—' : `${set.analysis.medianRangeDeg.toFixed(0)}°`}</span></button>)}</section> : null}
    {detail ? <Modal title={hardware ? 'Hardware recording evidence' : 'Knee angle details'} onClose={() => setDetail(false)}><Badge hardware={hardware}>{hardware ? 'Hardware · debug estimate' : 'Simulated readings'}</Badge><p>{hardware ? 'Complementary-filter orientation is an inspection estimate, not a validated anatomical angle. Timestamp gaps reset the filter. Missing sequence and quality fields are unknown, not measured.' : `Shank angle minus thigh angle, minus display offset (${zero.toFixed(1)}°). This instant angle differs from the range of a complete bend.`}</p><RawReadings sample={hardware && review ? review.samples.at(-1) ?? null : sample}/>{hardware ? <><h3>Packet evidence</h3><p className="muted">{review ? 'Captured recording records' : 'Latest 100 connection records; start a set to retain and export a recording.'}</p><div className="packet-log">{(review?.records ?? events).slice(-100).map((e, i) => <details key={i}><summary>{e.kind} · {e.receivedAt.slice(11, 23)} {e.message ?? ''}</summary><pre>{JSON.stringify(e, (_key, v) => typeof v === 'number' && !Number.isFinite(v) ? null : v, 2)}</pre></details>)}</div></> : null}</Modal> : null}
  </div>;
}
