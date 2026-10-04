import { useState } from 'react';
import { learnedBaselines, formatMetric, metricLabels, type MetricName } from '../../rn-app/src/data/learned-baselines';
import { Badge, Modal } from './ui';
export default function Landing() {
  const [detail, setDetail] = useState<MetricName | null>(null);
  const snapshot = learnedBaselines.participants[0].snapshots.find((s) => s.reference_session_count === 5)!;
  const evaluation = snapshot.evaluations.find((e) => e.scenario === 'balanced')!;
  const reference = snapshot.metrics.find((m) => m.side === 'right' && m.metric === detail);
  const comparison = evaluation.comparisons.find((m) => m.side === 'right' && m.metric === detail);
  return <div className="stack"><h2>Landing comparison</h2><p className="muted small">Right knee · balanced landing session · provisional reference</p>{(Object.keys(metricLabels) as MetricName[]).map((name) => {
    const ref = snapshot.metrics.find((m) => m.side === 'right' && m.metric === name)!;
    const result = evaluation.comparisons.find((m) => m.side === 'right' && m.metric === name)!;
    return <section className="panel" key={name}><div className="row"><h3>{metricLabels[name]}</h3><button onClick={() => setDetail(name)}>Details</button></div><div className="metrics"><div><span className="label">This session</span><strong className="metric-small orange">{formatMetric(result.evaluation_median, name)}</strong></div><div><span className="label">Your reference</span><strong className="metric-small blue">{formatMetric(ref.median, name)}</strong></div></div>{result.signed_difference !== null ? <p>{result.signed_difference >= 0 ? '+' : '−'}{formatMetric(Math.abs(result.signed_difference), name)} from reference</p> : <p>Comparison unavailable</p>}</section>;
  })}{detail ? <Modal title={`${metricLabels[detail]} · reference`} onClose={() => setDetail(null)}><Badge>Synthetic history</Badge><p>This session: {formatMetric(comparison?.evaluation_median ?? null, detail)}</p><p className="blue">Reference: {formatMetric(reference?.median ?? null, detail)}</p><p>Each eligible session contributes one median. MAD describes variation between synthetic session medians, not measurement error.</p>{reference?.session_summaries.map((s) => <p key={s.session_id}>{s.session_id} · {formatMetric(s.median, detail)} · {s.valid_event_count} landings</p>)}<p className="muted">Typical error, SEM and MDC are not empirically established. Plantar loading is not internal knee force. Frozen Python results do not validate a live hardware session.</p><code>{reference?.context.processing_version}</code></Modal> : null}</div>;
}
