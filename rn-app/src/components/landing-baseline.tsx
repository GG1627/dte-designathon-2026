import { useState } from 'react';
import { View } from 'react-native';
import { SelectionControl as Choice } from '@/components/selection-control';
import { Action, Badge, Divider, Panel, Row, Section, Sheet } from '@/components/monitoring-ui';
import { ThemedText as Text } from '@/components/themed-text';
import { Palette as c, Spacing as s } from '@/constants/theme';
import { formatMetric, learnedBaselines, metricLabels, type MetricName, type Side } from '@/data/learned-baselines';

export function LandingBaseline({ initialSide = 'right', mode = 'lab' }: {
  initialSide?: Side; mode?: 'lab' | 'summary';
}) {
  const [participantId, setParticipantId] = useState(learnedBaselines.participants[0].profile.id);
  const [side, setSide] = useState<string>(initialSide);
  const [scenario, setScenario] = useState('balanced');
  const [historyCount, setHistoryCount] = useState('5');
  const [details, setDetails] = useState<MetricName | null>(null);
  const participant = learnedBaselines.participants.find((p) => p.profile.id === participantId);
  const snapshot = participant?.snapshots.find((item) => item.reference_session_count === Number(historyCount));
  const evaluation = snapshot?.evaluations.find((item) => item.scenario === scenario);
  if (!participant || !snapshot || !evaluation) {
    return <Panel><Text type="smallBold">Landing reference unavailable</Text>
      <Text>No matching generated history or evaluation is available.</Text></Panel>;
  }
  const first = snapshot.metrics.find((m) => m.side === side);
  const ready = first?.status === 'ready';
  const selectedMetric = snapshot.metrics.find((m) => m.side === side && m.metric === details);
  const selectedComparison = evaluation.comparisons.find((m) => m.side === side && m.metric === details);
  const selectedSummary = evaluation.session_metrics.find((m) => m.side === side && m.metric === details);
  const compact = mode === 'summary';
  return <Section title={compact ? 'Landing comparison' : 'Reference experiment'}>
    {compact ? <Text type="small" themeColor="textSecondary">
      {side === 'right' ? 'Right' : 'Left'} knee · balanced landing session
    </Text> : <Panel>
      <Row wrap><Badge comparison>Learned · synthetic</Badge>
        <Badge muted={!ready}>{ready ? `${historyCount} reference sessions` : 'Reference developing'}</Badge></Row>
      <Text type="small" themeColor="textSecondary">Bilateral landings · knee. Independent simulated histories; no live devices.</Text>
      <Row wrap>
        <Choice label="Participant" value={participantId} onChange={setParticipantId}
          options={learnedBaselines.participants.map((p) => ({ value: p.profile.id, label: p.profile.label }))} />
        <Choice label="Side" value={side} onChange={setSide}
          options={[{ value: 'right', label: 'Right knee' }, { value: 'left', label: 'Left knee' }]} />
      </Row>
      <Text type="small" themeColor="textSecondary">{participant.profile.description}</Text>
      <Choice label="Evaluation session" value={scenario} onChange={setScenario}
        options={learnedBaselines.scenarios.map((item) => ({ value: item.id, label: item.label }))} />
      <Choice label="Reference history" value={historyCount} onChange={setHistoryCount}
        options={participant.snapshots.map((item) => ({ value: String(item.reference_session_count), label: `${item.reference_session_count} sessions` }))} />
      <Text type="small" themeColor="textSecondary">{learnedBaselines.scenarios.find((item) => item.id === scenario)?.description}</Text>
    </Panel>}
    {(Object.keys(metricLabels) as MetricName[]).map((name) => {
      const reference = snapshot.metrics.find((m) => m.side === side && m.metric === name);
      const comparison = evaluation.comparisons.find((m) => m.side === side && m.metric === name);
      const summary = evaluation.session_metrics.find((m) => m.side === side && m.metric === name);
      if (!reference || !comparison || !summary) return null;
      const difference = comparison.signed_difference;
      if (compact && name !== 'knee_rom_rad') return <View key={name} style={{ gap: s.two }}>
        <Divider />
        <Row wrap>
          <View style={{ flex: 1, gap: s.one }}>
            <Text type="small" themeColor="textSecondary">{name === 'peak_plantar_normal_force_bw' ? 'Peak foot force' : 'Landing impulse'}</Text>
            <Text type="smallBold">{formatMetric(comparison.evaluation_median, name)}</Text>
          </View>
          <Action onPress={() => setDetails(name)} label={`Compare ${metricLabels[name]}`}>Compare</Action>
        </Row>
      </View>;
      return <Panel key={name}>
        <Row wrap><Text type="smallBold">{metricLabels[name]}</Text>
          <Action onPress={() => setDetails(name)} label={`View ${metricLabels[name]} history and quality`}>{compact ? 'Details' : 'History & quality'}</Action></Row>
        <Row wrap>
          <View style={{ gap: s.one }}><Text type="label" themeColor="textSecondary">This session</Text>
            <Text type={compact ? 'metric' : 'subtitle'} style={{ color: c.accent }}>{formatMetric(comparison.evaluation_median, name)}</Text></View>
          <View style={{ gap: s.one }}><Text type="label" themeColor="textSecondary">{compact ? 'Your reference' : 'Learned median'}</Text>
            <Text type={compact ? 'smallBold' : 'subtitle'} style={{ color: c.comparison }}>{formatMetric(reference.median, name)}</Text></View>
        </Row>
        {difference !== null ? <Text type="small">
          {difference >= 0 ? '+' : '−'}{formatMetric(Math.abs(difference), name)} from reference
          {comparison.percent_difference !== null ? ` (${comparison.percent_difference >= 0 ? '+' : ''}${comparison.percent_difference.toFixed(1)}%)` : ''}
        </Text> : <Text type="small" themeColor="textSecondary">
          {comparison.reasons.includes('insufficient_valid_events')
            ? `${summary.valid_event_count} of ${summary.total_event_count} valid landings; ${snapshot.rules.min_valid_events} needed for comparison.`
            : comparison.reasons.includes('insufficient_reference_history')
              ? `${reference.eligible_session_count} comparable sessions; ${snapshot.rules.min_reference_sessions} needed for a reference.`
              : 'Comparison unavailable for this recording context.'}
        </Text>}
        {!compact ? <Text type="small" themeColor="textSecondary">
          {reference.contributing_event_count} reference landings · variability (MAD) {formatMetric(reference.mad, name)}
        </Text> : null}
      </Panel>;
    })}
    {!compact ? <Text type="small" themeColor="textSecondary">References stay frozen during comparison. Differences describe movement and plantar loading, not injury risk or readiness.</Text> : null}
    <Sheet title={details ? `${metricLabels[details]} · reference` : 'Reference'} open={details !== null} onClose={() => setDetails(null)}>
      <Badge muted>Synthetic history</Badge>
      <Row wrap><Text type="small">This session</Text><Text type="smallBold">{formatMetric(selectedComparison?.evaluation_median ?? null, details ?? '')}</Text></Row>
      <Row wrap><Text type="small">Your reference</Text><Text type="smallBold" style={{ color: c.comparison }}>{formatMetric(selectedMetric?.median ?? null, details ?? '')}</Text></Row>
      {selectedComparison?.signed_difference !== null && selectedComparison?.signed_difference !== undefined ? <Text type="small">
        {selectedComparison.signed_difference >= 0 ? '+' : '−'}{formatMetric(Math.abs(selectedComparison.signed_difference), details ?? '')} from reference
        {selectedComparison.percent_difference !== null ? ` (${selectedComparison.percent_difference >= 0 ? '+' : ''}${selectedComparison.percent_difference.toFixed(1)}%)` : ''}
      </Text> : <Text type="small" themeColor="textSecondary">{selectedComparison?.reasons.join(', ').replaceAll('_', ' ')}</Text>}
      {details && details !== 'knee_rom_rad' ? <Text type="small" themeColor="textSecondary">BW is body-weight units. These measurements describe plantar loading, not internal knee force.</Text> : null}
      <Divider />
      <Text type="small">Each eligible session contributes one median, regardless of landing count. MAD describes variation between those session medians.</Text>
      <Text type="smallBold">As reference history grows</Text>
      {participant.snapshots.map((item) => {
        const metric = item.metrics.find((m) => m.side === side && m.metric === details);
        return <Row key={item.reference_session_count} wrap>
          <Text type="small">{item.reference_session_count} sessions</Text>
          <Text type="small">{formatMetric(metric?.median ?? null, details ?? '')} · MAD {formatMetric(metric?.mad ?? null, details ?? '')}</Text>
        </Row>;
      })}
      <Text type="small" themeColor="textSecondary">Small histories can produce unstable variability estimates. More sessions do not guarantee accuracy.</Text>
      <Divider />
      <Text type="smallBold">Contributing sessions</Text>
      {selectedMetric?.session_summaries.map((item) => <Row key={item.session_id} wrap>
        <Text type="small" style={{ flexShrink: 1 }}>{item.session_id}</Text>
        <Text type="small">{formatMetric(item.median, details ?? '')} · {item.valid_event_count} landings</Text>
      </Row>)}
      <Divider />
      <Text type="smallBold">Evaluation quality</Text>
      <Text type="small">{selectedSummary?.valid_event_count} of {selectedSummary?.total_event_count} landings accepted.</Text>
      {selectedSummary?.rejected_events.map((event) => <Text key={event.event_id} type="small" themeColor="textSecondary">
        {event.event_id}: {event.reasons.join(', ').replaceAll('_', ' ')}
      </Text>)}
      <Text type="small">Standardized difference: {selectedComparison?.robust_standardized_difference?.toFixed(2) ?? 'Unavailable'}</Text>
      <Text type="small" themeColor="textSecondary">Relative to reference MAD, not an injury probability. {selectedComparison?.standardized_difference_reasons.join(', ').replaceAll('_', ' ')}</Text>
    </Sheet>
  </Section>;
}
