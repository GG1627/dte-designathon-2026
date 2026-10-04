import { useState } from 'react';
import { homeBendFeedback, homeBendHistory, homeBendSet } from '../../rn-app/src/data/home-bend-demo';
import { Badge, Modal } from './ui';

export function HomeMovementFeedback({ onLive }: { onLive: () => void }) {
  const [open, setOpen] = useState(false);
  const [intent, setIntent] = useState<'planned' | 'unexpected' | null>(null);
  const [tired, setTired] = useState(false);
  const a = homeBendSet.analysis;
  const early = a.firstHalfRangeDeg!, late = a.secondHalfRangeDeg!;
  const difference = early - late;
  const nextStep = intent === 'planned'
    ? 'Keep following your planned variation. We’ll treat this change as intentional.'
    : intent === 'unexpected'
      ? tired ? 'You reported feeling tired. Take a break and return to comfortable movement when you feel ready.'
        : 'Check that your sensors stayed in place, then repeat a few comfortable bends with the same setup.'
      : 'Confirm whether this was planned before changing your next set.';
  const leg = (x: number, degrees: number) => {
    const angle = degrees * Math.PI / 180;
    return `M ${x} 17 L ${x} 66 L ${x + 54 * Math.sin(angle)} ${66 + 54 * Math.cos(angle)}`;
  };

  return <section className="stack">
    <h2>Your movement today</h2>
    <div className="row wrap"><span className="muted small">Knee bends · {a.reps.length} complete reps</span><Badge>Simulated</Badge></div>
    <button className="panel evidence movement-story" onClick={() => setOpen(true)} aria-label={`Your bends became shallower near the end. Early ${early.toFixed(0)} degrees, late ${late.toFixed(0)} degrees, ${difference.toFixed(0)} degrees less. Show evidence.`}>
      <h2>Your bends got shallower near the end</h2>
      <svg className="bend-comparison" viewBox="0 0 280 114" aria-hidden="true">
        {[44, 184].map((x) => <line key={x} x1={x} y1="17" x2={x} y2="110" stroke="var(--border)" strokeDasharray="3 5"/>)}
        <path d={leg(44, early)} stroke="var(--blue)" strokeWidth="13" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
        <path d={leg(184, early)} stroke="var(--blue)" strokeWidth="13" strokeLinecap="round" strokeLinejoin="round" fill="none" opacity="0.22"/>
        <path d={leg(184, late)} stroke="var(--orange)" strokeWidth="13" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
        {[44, 184].map((x) => <circle key={x} cx={x} cy="66" r="7" fill="var(--surface)" stroke={x === 44 ? 'var(--blue)' : 'var(--orange)'} strokeWidth="3"/>)}
      </svg>
      <div className="comparison-labels"><div><strong className="blue">Early · {early.toFixed(0)}°</strong><span className="muted small">First three bends</span></div><div><strong className="orange">Late · {late.toFixed(0)}°</strong><span className="muted small">Last three bends</span></div></div>
      <svg className="rep-markers" viewBox="0 0 280 34" role="img" aria-label={a.reps.map((rep) => `Bend ${rep.number}: ${rep.rangeDeg.toFixed(0)} degrees`).join('. ')}>
        {a.reps.map((rep, i) => { const height = rep.rangeDeg / Math.max(...a.reps.map((r) => r.rangeDeg)) * 26;
          return <rect key={rep.number} x={i * 46 + 3} y={30 - height} width="34" height={height} rx="4" fill={i < 3 ? 'var(--blue)' : 'var(--orange)'}/>;
        })}
      </svg>
      <span className="orange">{difference.toFixed(0)}° less movement · See evidence ↗</span>
    </button>
    <fieldset className="intent-check"><legend>Was this intentional?</legend><div className="form-grid">
      {([{ value: 'planned', label: 'Yes, planned' }, { value: 'unexpected', label: 'No, unexpected' }] as const).map((answer) => <label className={`radio-choice ${intent === answer.value ? 'selected' : ''}`} key={answer.value}>
        <input type="radio" name="movement-intent" value={answer.value} checked={intent === answer.value} onChange={() => { setIntent(answer.value); setTired(false); }}/>{answer.label}
      </label>)}
    </div></fieldset>
    {intent === 'unexpected' ? <button className="self-check" aria-pressed={tired} onClick={() => setTired(!tired)}>{tired ? 'Clear tired check-in' : 'I’m feeling tired'}</button> : null}
    <div className="stack next-step" aria-live="polite"><span className="label">{intent ? 'Next step' : 'Your context matters'}</span><p>{nextStep}</p>
      {intent === 'unexpected' && !tired ? <button className="text-button" onClick={onLive}>Try a new set</button> : <button className="text-button" onClick={() => setOpen(true)}>Review movement details</button>}
    </div>
    {open ? <Modal title="Behind your movement reading" onClose={() => setOpen(false)}>
      <Badge>Simulated example set</Badge><p>{homeBendFeedback.observation}</p>
      <p>Each bend’s range is its deepest minus its straightest angle. The first three ranges are {early.toFixed(0)}° each; the last three are {late.toFixed(0)}° each. Their group medians differ by {difference.toFixed(0)}°.</p>
      <p>The leg drawings show a representative bend from each group. The faded blue outline behind the later bend shows the earlier position. These are schematic comparisons, not anatomical images.</p>
      <p className="blue">Recent reference: {homeBendFeedback.referenceRangeDeg!.toFixed(0)}°, from earlier matching set medians of {homeBendHistory.map((set) => `${set.analysis.medianRangeDeg!.toFixed(0)}°`).join(', ')}. The main card compares early and late bends in this set, rather than treating that reference as a target.</p>
      <p className="muted">Setup does not create a real personal baseline. This scripted example does not establish fatigue, injury, or the cause of the change.</p>
      <p>Your check-in: {intent === 'planned' ? 'intentional change' : intent === 'unexpected' ? 'unexpected change' : 'not answered'}{tired ? ' · feeling tired (self-reported)' : ''}. Your answer changes the next step, not the recorded measurements.</p>
      <hr/><h3>Complete bends · {a.reps.length}</h3><p>Typical range · {a.medianRangeDeg!.toFixed(1)}°<br/>Typical rep · {a.medianDurationS!.toFixed(1)} s<br/>Range variation · {a.rangeSpreadDeg!.toFixed(1)}°<br/>Recording · {a.sampleCount} simulated readings, no continuity breaks</p>
      <div className="table-wrap"><table><thead><tr><th>Rep</th><th>Range</th><th>Duration</th><th>Peak speed</th><th>Peak acceleration</th></tr></thead><tbody>{a.reps.map((rep) => <tr key={rep.number}><td>{rep.number}</td><td>{rep.rangeDeg.toFixed(1)}°</td><td>{rep.durationS.toFixed(2)} s</td><td>{rep.peakVelocityDegS.toFixed(1)} °/s</td><td>{rep.peakAccelerationDegS2.toFixed(1)} °/s²</td></tr>)}</tbody></table></div>
      <button onClick={() => { setOpen(false); onLive(); }}>Open Live movement</button>
    </Modal> : null}
  </section>;
}
