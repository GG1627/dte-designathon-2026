import { useState } from 'react';
import { Badge, Modal, RangeBars } from './ui';
import { recordingTrace, type HardwareInspection } from './hardware-recording';
import type { SerialRecord } from './serial';
import { ScriptedFeedback } from './scripted-feedback';

export function SignalTrace({ records }: { records: SerialRecord[] }) {
  const { runs, sampleCount } = recordingTrace(records);
  const values = runs.flatMap((run) => run.map((point) => point.angle));
  if (!values.length) return <p className="muted">Waiting for usable sensor readings.</p>;
  const lower = Math.floor(Math.min(...values) / 10) * 10;
  const upper = Math.max(lower + 10, Math.ceil(Math.max(...values) / 10) * 10);
  const x = (index: number) => 72 + index / Math.max(1, sampleCount - 1) * 552;
  const y = (angle: number) => 136 - (angle - lower) / (upper - lower) * 112;
  return <div className="signal-trace"><svg viewBox="0 0 640 176" role="img" aria-label={`Relative debug angle across ${sampleCount} received samples. ${runs.length} continuous signal sections; breaks are not joined.`}>
    {[lower, (lower + upper) / 2, upper].map((value) => <g key={value}><line x1="72" x2="624" y1={y(value)} y2={y(value)} stroke="var(--border)"/><text x="2" y={y(value) + 4} fill="var(--muted)" fontSize="11">{value}°</text></g>)}
    {runs.map((run, i) => run.length === 1 ? <circle key={i} cx={x(run[0].index)} cy={y(run[0].angle)} r="2" fill="var(--orange)"/> : <path key={i} d={run.map((point, j) => `${j ? 'L' : 'M'}${x(point.index).toFixed(1)},${y(point.angle).toFixed(1)}`).join(' ')} fill="none" stroke="var(--orange)" strokeWidth="2.5"/>) }
    <text x="72" y="165" fill="var(--muted)" fontSize="11">First sample</text><text x="624" y="165" textAnchor="end" fill="var(--muted)" fontSize="11">Latest sample</text>
  </svg><p className="muted small">Relative angle estimate · horizontal axis is packet order. Gaps are not joined.</p></div>;
}

export function HardwareReview({ inspection, records, durationS, sampleCount, onEvidence, onNew }: {
  inspection: HardwareInspection; records: SerialRecord[]; durationS: number; sampleCount: number; onEvidence: () => void; onNew: () => void;
}) {
  const [detail, setDetail] = useState(false);
  const a = inspection.analysis;
  const candidates = a?.source === 'hardware' && a.status === 'unsupported' ? a.reps : [];
  return <div className="stack"><div className="row wrap"><h2>Your recorded movement</h2><Badge hardware>Hardware · Prototype inspection</Badge></div>
    <section className="panel accent-panel"><h2>{candidates.length ? `${candidates.length} candidate bend cycles found` : 'Review your captured signal'}</h2><p>{durationS.toFixed(1)} s recording interval · {sampleCount} received samples</p><p className="muted">These are patterns in the live debug signal, not verified exercise repetitions. Hardware exercise feedback remains blocked pending validation.</p>
      <SignalTrace records={records}/>
      <button className="plain evidence orange" onClick={() => setDetail(true)}>See how this was calculated ↗</button>
    </section>
    {candidates.length && a ? <>
      <div className="metrics"><section className="panel"><span className="muted">Typical signal range</span><strong className="metric-small orange">{a.medianRangeDeg?.toFixed(1)}°</strong><span className="muted small">Unvalidated angle estimate</span></section><section className="panel"><span className="muted">Typical candidate cycle</span><strong className="metric-small">{a.medianDurationS?.toFixed(2)} s</strong><span className="muted small">Assumes device timestamps are ms</span></section></div>
      <section className="panel"><h3>Signal range by candidate cycle</h3><RangeBars values={candidates.map((rep) => rep.rangeDeg)}/>
        {a.firstHalfRangeDeg !== null && a.secondHalfRangeDeg !== null ? <><div className="comparison-labels"><div><span className="muted small">First half</span><strong className="metric-small blue">{a.firstHalfRangeDeg.toFixed(1)}°</strong></div><div><span className="muted small">Last half</span><strong className="metric-small orange">{a.secondHalfRangeDeg.toFixed(1)}°</strong></div></div><p className="muted small">Medians of candidate-cycle signal ranges. An odd middle cycle is excluded. This does not establish a change in anatomical movement or its cause.</p></> : <p className="muted small">At least four candidate cycles are needed for a first/last-half signal comparison.</p>}
      </section>
    </> : <section className="panel"><h3>No candidate cycles to summarize</h3><p className="muted">The shared detector needs a complete rise and return in the signal. Partial cycles, small changes, and cycles crossing known data breaks are excluded. Mounting and angle estimation may also prevent detection.</p></section>}
    {sampleCount > 0 ? <ScriptedFeedback/> : null}
    <section className="panel"><h3>Recording evidence</h3><p>{inspection.packetErrors} packet errors · {inspection.interruptionRecords} interruption records · {a?.invalidSamples ?? 0} invalid or excluded analysis readings</p><p className="muted small">Original packets, timestamps, source fields, and errors are retained. Candidate results are kept out of personal and simulated history.</p><div className="actions"><button onClick={onEvidence}>Packet evidence</button><button className="primary" onClick={onNew}>Record again</button></div></section>
    {detail ? <Modal title="How the recording was processed" onClose={() => setDetail(false)}><Badge hardware>Hardware · Unvalidated estimates</Badge><ol className="processing-steps"><li>Read only the ESP32 packets received between Record movement and Stop &amp; review.</li><li>Convert acceleration and gyro units, then estimate each sensor’s orientation with the viewer’s complementary filter.</li><li>Subtract thigh orientation from shank orientation to form the relative debug signal.</li><li>Run the existing shared bend detector on that signal, then summarize its candidate cycles.</li></ol><p>Detector version: {a?.version ?? 'No samples'}. Source: {a?.source ?? 'hardware'}. Exercise-feedback status: {a?.status ?? 'unsupported'}.</p><p className="muted">The detector’s 6° signal-amplitude and 0.4 s duration gates are prototype engineering rules. The first reading after a packet or filter break is excluded from analysis only; its original validity and data remain in the export. {inspection.excludedBoundarySequences.length} boundary readings excluded.</p><p className="warning">Sensor units, mounting, anatomical angles, and repetition detection must be checked on the wearable. This is the shared bend detector, not the Python personal-baseline pipeline.</p>
      {candidates.length ? <div className="table-wrap"><table><thead><tr><th>Candidate</th><th>Signal range</th><th>Cycle duration</th><th>Raw start / end (ms assumed)</th></tr></thead><tbody>{candidates.map((rep) => <tr key={rep.number}><td>{rep.number}</td><td>{rep.rangeDeg.toFixed(1)}°</td><td>{rep.durationS.toFixed(2)} s</td><td>{rep.startMs} / {rep.endMs}</td></tr>)}</tbody></table></div> : null}
    </Modal> : null}
  </div>;
}
