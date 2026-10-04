import { useEffect, useState, lazy, Suspense } from 'react';
import { Live } from './live';
import { HomeMovementFeedback } from './home-movement-feedback';
import { Setup } from './setup';
import { Guide, Welcome } from './guide';
import { createMockSetup, type SetupData } from '../../rn-app/src/data/setup';
import { Badge, Icon, Modal, RangeBars } from './ui';
import { average, demoDate, formatDate, jointSessions, joints, observations, rom, sessions, type Activity, type Joint, type Session } from './shared';

const Landing = lazy(() => import('./landing'));
type Tab = 'Home' | 'Trends' | 'Joints' | 'Live';
type Route = Tab | 'Welcome' | 'Guide' | 'Setup';
const tabs: Tab[] = ['Home', 'Trends', 'Joints', 'Live'];
const routes: Route[] = [...tabs, 'Welcome', 'Guide', 'Setup'];
const fromHash = (): Route => routes.find((t) => `#${t.toLowerCase()}` === location.hash) ?? 'Welcome';
export function App() {
  const [tab, setTab] = useState<Route>(fromHash);
  const [setup, setSetup] = useState(createMockSetup);
  const [guideVisit, setGuideVisit] = useState(0);
  const [detail, setDetail] = useState<Session | Joint | 'devices' | 'other' | null>(null);
  useEffect(() => { const listener = () => setTab(fromHash()); window.addEventListener('hashchange', listener); return () => window.removeEventListener('hashchange', listener); }, []);
  function navigate(next: Route) { if (next === 'Guide') setGuideVisit((n) => n + 1); location.hash = next.toLowerCase(); setTab(next); window.scrollTo(0, 0); }
  return <><header className="site-header"><a className="brand" href="#home" aria-label="Kintra Home"><svg width="28" height="32" viewBox="0 0 28 32" aria-hidden="true"><path d="M4 2v28M24 2 9 16l15 14" fill="none" stroke="var(--orange)" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"/></svg><span>kintra</span></a><span className="header-note">Your movement, understood.</span></header>
    {tabs.includes(tab as Tab) ? <nav aria-label="Main navigation" className="navigation">{tabs.map((name) => <a key={name} href={`#${name.toLowerCase()}`} aria-current={tab === name ? 'page' : undefined}><Icon name={name}/><span>{name}</span></a>)}</nav> : null}
    <main id="main"><div hidden={tab !== 'Welcome'}><Welcome onStart={() => navigate('Guide')}/></div><div hidden={tab !== 'Guide'}><Guide key={guideVisit} onFinish={() => navigate('Home')}/></div><div hidden={tab !== 'Setup'}><Setup setup={setup} setSetup={setSetup} active={tab === 'Setup'} onClose={() => navigate('Home')}/></div><div hidden={tab !== 'Home'}><Home setup={setup} onSetup={() => navigate('Setup')} onGuide={() => navigate('Guide')} onLive={() => navigate('Live')} onHistory={() => navigate('Trends')} onDetail={setDetail}/></div><div hidden={tab !== 'Trends'}><Trends onDetail={setDetail}/></div><div hidden={tab !== 'Joints'}><Joints onDetail={setDetail}/></div><div hidden={tab !== 'Live'}><Live active={tab === 'Live'}/></div></main>
    {detail ? <Modal title={detail === 'devices' ? 'Devices' : detail === 'other' ? 'Other joints' : 'activity' in detail ? detail.activity : detail.name} onClose={() => setDetail(null)}>
      <Badge>Synthetic demonstration</Badge>{detail === 'devices' ? <><p>These device assignments belong to the mobile demo. Connect a real device in Live → USB serial.</p><div className="stack">{['Pod 01 · Right thigh', 'Pod 02 · Right lower leg', 'Pod 03 · Right shoe'].map((v) => <div className="panel" key={v}>{v}<p className="muted small">Demo device · no hardware connection</p></div>)}</div></> : detail === 'other' ? <><p className="muted">No devices or recordings are assigned to these joints.</p>{joints.filter((j) => !j.monitored).map((j) => <button className="record-row plain" key={j.id} onClick={() => setDetail(j)}>{j.name}<span className="muted">Not monitored ↗</span></button>)}</> : 'activity' in detail ? <><p>{formatDate(detail.date)} · {detail.minutes} min recorded</p><div className="metrics">{joints.filter((j) => j.monitored).map((j) => <div className="panel" key={j.id}><span className="muted">{j.name} range</span><strong className="metric-small orange">{rom(j, detail)}°</strong></div>)}</div><p>Valid coverage: {detail.coverage}% · {detail.cycles.toLocaleString()} movement cycles.</p><p className="muted">Frozen synthetic observations; separate from serial recordings and live knee-bend sets.</p></> : <><p className="muted">{detail.monitored ? 'Recorded motion · synthetic observations' : 'Not monitored · no data'}</p>{detail.monitored ? <><div className="row"><span>Latest running range</span><strong className="metric-small orange">{rom(detail, sessions[0])}°</strong></div><p>{detail.devices.length} demo devices assigned.</p><button onClick={() => { setDetail(null); navigate('Trends'); }}>View trends</button></> : null}{detail.placement.map((v) => <p key={v}>{v}</p>)}</>}
    </Modal> : null}
  </>;
}
function SessionRow({ session, onClick }: { session: Session; onClick: () => void }) {
  return <button className="panel record-row" onClick={onClick}><span className="activity-symbol" aria-hidden="true"><Icon name="Trends"/></span><span className="grow"><strong>{session.activity}</strong><span className="muted small">{formatDate(session.date)} · {session.minutes} min recorded</span></span><span className="muted">Details ↗</span></button>;
}
function Home({ setup, onSetup, onGuide, onLive, onHistory, onDetail }: { setup: SetupData; onSetup: () => void; onGuide: () => void; onLive: () => void; onHistory: () => void; onDetail: (value: Session | Joint | 'devices') => void }) {
  const today = sessions.filter((s) => s.offset === 0), latest = today[0];
  const ready = setup.setup_status === 'complete';
  return <div className="stack"><div><h1>Today</h1><p className="muted">{formatDate(demoDate, true)} · Synthetic demonstration</p></div>
    {!ready ? <><div className="row wrap"><span className="muted small">Start tracking your movement</span><button className="text-button" onClick={onSetup}>{setup.setup_status === 'in_progress' ? 'Resume setup' : 'Set up Kintra'}</button></div><div className="empty-home stack"><h2>Your movement starts here</h2><p className="muted">Complete the demo setup to explore readings, a personal baseline, and your next step.</p></div></> : <>
    <HomeMovementFeedback onLive={onLive}/>
    <section className="stack"><div className="row"><h2>Your joints</h2><button className="text-button" onClick={() => onDetail('devices')}>Devices</button></div><p className="muted small">Movement range · today’s running</p><div className="panel joint-measurements">{joints.filter((j) => j.monitored).map((joint) => <button className="plain joint-reading" onClick={() => onDetail(joint)} key={joint.id}><span><strong>{joint.name}</strong><span className="muted small">Recorded movement</span></span><span className="metric-small orange">{rom(joint, latest)}°</span><span className="muted">↗</span></button>)}</div></section>
    <section className="stack"><div className="row"><h2>Latest recording</h2><button className="text-button" onClick={onHistory}>History</button></div><SessionRow session={latest} onClick={() => onDetail(latest)}/></section><p className="muted small">{today.reduce((n, s) => n + s.minutes, 0)} min recorded · {today.length} demo recordings today</p>
    </>}
    <div className="actions"><button className="text-button" onClick={onGuide}>Knee guide</button>{ready ? <button className="text-button" onClick={onSetup}>Review setup</button> : null}</div>
  </div>;
}
function Joints({ onDetail }: { onDetail: (value: Joint | 'devices' | 'other') => void }) {
  return <div className="stack"><h1>Your joints</h1><div className="row"><h2>Monitored</h2><button className="text-button" onClick={() => onDetail('devices')}>Devices</button></div>{joints.filter((j) => j.monitored).map((j) => <button className="panel record-row" onClick={() => onDetail(j)} key={j.id}><span className="grow"><strong>{j.name}</strong><span className="muted small">{j.devices.length} devices · recorded motion</span></span><Badge>Demo</Badge><span className="muted">↗</span></button>)}<button onClick={() => onDetail('other')}>Other joints</button><p className="muted small">Synthetic joint history. Hardware inspection is available in Live.</p></div>;
}
function Trends({ onDetail }: { onDetail: (value: Session) => void }) {
  const [jointId, setJointId] = useState('right-knee'), [activity, setActivity] = useState('Running');
  const [days, setDays] = useState('7'), [details, setDetails] = useState(false);
  const joint = joints.find((j) => j.id === jointId)!;
  const records = observations(joint, activity as Activity, Number(days));
  const previous = observations(joint, activity as Activity, Number(days), true);
  const current = average(records.map((s) => rom(joint, s))), prior = average(previous.map((s) => rom(joint, s)));
  const excluded = jointSessions(joint).filter((s) => s.offset < Number(days) && s.activity === activity && s.coverage < 80).length;
  return <div className="stack"><div className="row wrap"><h1>Trends</h1><Badge>Synthetic observations</Badge></div><div className="form-grid"><label>Joint<select value={jointId} onChange={(e) => { setJointId(e.target.value); if (activity === 'Landings' && e.target.value !== 'right-knee') setActivity('Running'); }}>{joints.filter((j) => j.monitored).map((j) => <option value={j.id} key={j.id}>{j.name}</option>)}</select></label><label>Activity<select value={activity} onChange={(e) => setActivity(e.target.value)}>{['Running', 'Walking', ...(joint.anatomy === 'Knee' ? ['Landings'] : [])].map((a) => <option key={a}>{a}</option>)}</select></label></div>
    {activity === 'Landings' ? <Suspense fallback={<p className="muted">Loading landing comparison…</p>}><Landing/></Suspense> : <><div className="segmented" aria-label="Period">{[['7', 'Past week'], ['30', 'Past month']].map(([value, label]) => <button key={value} aria-pressed={days === value} onClick={() => setDays(value)}>{label}</button>)}</div><section className="panel"><div className="row wrap"><div><span className="label">{joint.name} · movement range</span><div className="metric orange">{current === null ? '—' : `${current.toFixed(1)}°`}</div></div><span className="muted">Average · {activity.toLowerCase()}</span></div><RangeBars values={records.slice().reverse().map((s) => rom(joint, s))} labels={records.slice().reverse().map((s) => new Date(`${s.date}T12:00:00Z`).getUTCDate().toString())}/>{current !== null && prior !== null ? <p>{Math.abs(current - prior).toFixed(1)}° {current >= prior ? 'higher' : 'lower'} than the previous {days} days.</p> : null}</section><div className="row wrap"><span className="muted small">{records.length} recordings{excluded ? ` · ${excluded} excluded` : ''}</span><button onClick={() => setDetails(true)}>Recording details</button></div><h2>Recent recordings</h2>{records.slice(0, 3).map((s) => <SessionRow session={s} key={s.id} onClick={() => onDetail(s)}/>)}</>}
    {details ? <Modal title="Recording details" onClose={() => setDetails(false)}><Badge>Synthetic observations</Badge><p>{joint.name} · {activity} · past {days} days</p><p>Only recordings with at least 80% valid coverage are included. {excluded} excluded.</p><p className="muted">Running and walking have no learned reference. Landing comparisons use a separate activity-specific reference.</p><div className="table-wrap"><table><thead><tr><th>Date</th><th>Range</th><th>Minutes</th><th>Coverage</th><th>Cycles</th></tr></thead><tbody>{records.map((s) => <tr key={s.id}><td>{formatDate(s.date)}</td><td>{rom(joint, s)}°</td><td>{s.minutes}</td><td>{s.coverage}%</td><td>{s.cycles}</td></tr>)}</tbody></table></div></Modal> : null}
  </div>;
}
