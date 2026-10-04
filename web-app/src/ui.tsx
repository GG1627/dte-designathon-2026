import { useEffect, useRef, type ReactNode } from 'react';
import type { LiveSample } from './shared';

export function Badge({ children, hardware = false }: { children: ReactNode; hardware?: boolean }) {
  return <span className={`badge ${hardware ? 'hardware' : ''}`}>{children}</span>;
}
export function Modal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { const dialog = ref.current; dialog?.showModal(); return () => dialog?.close(); }, []);
  return <dialog ref={ref} onCancel={onClose} onClick={(event) => { if (event.target === event.currentTarget) onClose(); }} aria-labelledby="detail-title">
    <div className="modal-content"><div className="row"><h2 id="detail-title">{title}</h2><button autoFocus onClick={onClose} aria-label="Close details">Close</button></div>{children}</div>
  </dialog>;
}
export function Icon({ name }: { name: string }) {
  const paths: Record<string, ReactNode> = {
    Home: <><path d="m3 10 9-7 9 7v10H3Z"/><path d="M9 20v-7h6v7"/></>,
    Trends: <><path d="M3 4v16h18"/><path d="m6 15 4-5 4 3 6-8"/></>,
    Joints: <><circle cx="12" cy="4" r="2"/><path d="M4 9h16M12 7v7m0 0-5 7m5-7 5 7"/></>,
    Live: <><circle cx="12" cy="12" r="2"/><path d="M7 7a7 7 0 0 0 0 10m10-10a7 7 0 0 1 0 10M4 4a11 11 0 0 0 0 16M20 4a11 11 0 0 1 0 16"/></>,
  };
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}
export function KneeDiagram({ sample }: { sample: LiveSample | null }) {
  const valid = sample && sample.thigh.valid && sample.shank.valid;
  const thigh = valid ? sample.thigh.angleDeg * Math.PI / 180 : 0;
  const shank = valid ? sample.shank.angleDeg * Math.PI / 180 : 0;
  return <svg className={`knee-diagram ${valid ? '' : 'unavailable'}`} viewBox="0 0 340 310" role="img" aria-label={`${sample?.source === 'hardware' ? 'Debug estimate of' : 'Simulated'} thigh and shank orientation${valid ? '' : ', no valid sample'}`}>
    <line x1="160" y1="42" x2="160" y2="285" stroke="var(--border)" strokeDasharray="4 6" />
    <circle cx="160" cy="165" r="48" fill="none" stroke="var(--border)" />
    <line x1={160 - 95 * Math.sin(thigh)} y1={165 - 95 * Math.cos(thigh)} x2="160" y2="165" stroke="var(--blue)" strokeWidth="18" strokeLinecap="round" />
    <line x1="160" y1="165" x2={160 + 110 * Math.sin(shank)} y2={165 + 110 * Math.cos(shank)} stroke="var(--orange)" strokeWidth="18" strokeLinecap="round" />
    <circle cx="160" cy="165" r="13" fill="var(--surface)" stroke="var(--text)" strokeWidth="3" />
    <text x="38" y="90" fill="var(--blue)" fontSize="12">THIGH</text><text x="38" y="258" fill="var(--orange)" fontSize="12">SHANK</text>
  </svg>;
}
export function RawReadings({ sample }: { sample: LiveSample | null }) {
  if (!sample) return <p className="muted">Waiting for a sensor packet.</p>;
  return <>{(['thigh', 'shank'] as const).map((key) => {
    const reading = sample[key];
    const vector = (v: { x: number; y: number; z: number }) => [v.x, v.y, v.z].map((value) => Number.isFinite(value) ? value.toFixed(3) : 'unavailable').join(', ');
    return <section key={key} className="raw-section"><h3 className={key === 'thigh' ? 'blue' : 'orange'}>{key === 'thigh' ? 'Thigh' : 'Shank'}</h3>
      <p>{reading.valid ? 'Fields usable' : 'Invalid sensor reading'} · {Number.isFinite(reading.angleDeg) ? `${reading.angleDeg.toFixed(1)}°` : 'Angle unavailable'}</p>
      <code>Acceleration: {vector(reading.accelMS2)} m/s²<br/>Gyroscope: {vector(reading.gyroRadS)} rad/s</code></section>;
  })}<p className="muted">Source: {sample.source} · Sequence: {sample.sequence} · Raw timestamp: {sample.timestampMs} ms</p></>;
}
export function RangeBars({ values, labels }: { values: number[]; labels?: string[] }) {
  if (!values.length) return <p className="muted">No complete measurements available.</p>;
  const shown = values.slice(0, 12), max = Math.max(10, ...shown);
  return <><svg className="bars" viewBox="0 0 640 160" role="img" aria-label={shown.map((v, i) => `${labels?.[i] ?? `Rep ${i + 1}`}: ${v.toFixed(1)} degrees`).join('. ')}>
    {[0, 0.5, 1].map((n) => <g key={n}><line x1="40" x2="630" y1={130 - n * 110} y2={130 - n * 110} stroke="var(--border)"/><text x="2" y={134 - n * 110} fill="var(--muted)" fontSize="11">{Math.round(max * n)}°</text></g>)}
    {shown.map((v, i) => <g key={i}><rect x={44 + i * 580 / shown.length} y={130 - v / max * 110} width={Math.max(3, 580 / shown.length - 14)} height={v / max * 110} rx="4" fill="var(--orange)"/><text x={48 + i * 580 / shown.length} y="153" fill="var(--muted)" fontSize="11">{labels?.[i] ?? i + 1}</text></g>)}
  </svg>{values.length > 12 ? <p className="muted">First 12 of {values.length} measurements</p> : null}</>;
}
