import { useState } from 'react';
import { View } from 'react-native';
import { Action, Badge, Divider, Panel, Row, Section } from '@/components/monitoring-ui';
import { ThemedText as Text } from '@/components/themed-text';
import generated from '@/data/activity-context-results.json';
import { formatMetric, metricLabels, type MetricName, type Side } from '@/data/learned-baselines';
import { Spacing as s } from '@/constants/theme';

// Offline Python-generated choices. React selects results; it does not detect or fit.
export function ActivityContextDemo({ side = 'right' }: { side?: Side }) {
  const [activity, setActivity] = useState<string | null>(null);
  const state = generated.states.find((item) => item.activity === activity)!;
  const episode = generated.detection.episodes[0] ?? { detected_movement: 'unclassified',
    features: { duration_s: null, event_count: null }, candidate_activities: [] };
  const label = generated.activity_options.find((item) => item.id === activity)?.label;
  return <Section title="Kintra detected movement">
    <Panel>
      <Badge muted>Synthetic · confirmation prototype</Badge>
      <Text type="smallBold">{episode.detected_movement.replaceAll('_', ' ')}</Text>
      <Text type="small">Recorded {episode.features.duration_s?.toFixed(1) ?? 'unavailable'} seconds with {episode.features.event_count ?? 'unavailable'} complete contact cycles per side.</Text>
      <Text type="small" themeColor="textSecondary">{episode.detected_movement === 'unclassified' || episode.detected_movement === 'low_activity' ? "We recorded a session, but could not classify a structured movement pattern. " : ''}Movement-pattern candidate only. Similar movement can occur in different sports.</Text>
      {episode.candidate_activities.length > 0 && <Text type="small" themeColor="textSecondary">
        Examples to confirm: {episode.candidate_activities.map((id) => generated.activity_options.find((option) => option.id === id)?.label ?? id).join(', ')}.
      </Text>}
      <Text type="smallBold">What were you doing?</Text>
      <Row wrap>
        {generated.activity_options.map((option) => <Action key={option.id}
          label={`Confirm ${option.label}`} onPress={() => setActivity(option.id)}>{option.label}</Action>)}
      </Row>
      {activity === null ? <Text type="small">Confirm the activity to compare this session with your personal reference.</Text> : <>
        <Text type="smallBold">✓ {label} confirmed</Text>
        <Text type="small">Kintra will compare this session only with your other confirmed {label?.toLowerCase()} sessions recorded with a compatible sensor setup.</Text>
        <Badge muted={state.reference_status !== 'provisional_reference'}>
          {state.reference_status === 'provisional_reference' ? 'Provisional reference' : 'Insufficient matching history'}
        </Badge>
        <Text type="small">{state.eligible_session_count} comparable sessions · {state.contributing_event_count} reference landing events</Text>
        {state.reference_status !== 'provisional_reference' && <Text type="small">Basketball history is not used for this activity.</Text>}
        <Action label="Clear demo activity confirmation" onPress={() => setActivity(null)}>Change / clear activity</Action>
      </>}
      <Divider />
      {state.comparisons.filter((item) => item.side === side).map((item) => <View key={item.metric} style={{ gap: s.one }}>
        <Text type="smallBold">{side === 'right' ? 'Right' : 'Left'} · {metricLabels[item.metric as MetricName]}</Text>
        <Text type="small">Current: {formatMetric(item.evaluation_median, item.metric)} · Reference: {formatMetric(item.reference_median, item.metric)}</Text>
        <Text type="small" themeColor="textSecondary">{item.signed_difference === null
          ? activity === null ? 'Confirm activity to enable comparison.' : 'No compatible confirmed reference.'
          : `Change: ${formatMetric(item.signed_difference, item.metric)} (${item.percent_difference?.toFixed(1)}%)`}</Text>
      </View>)}
      <Text type="small" themeColor="textSecondary">These buttons select offline Python-generated outcomes. This prototype does not persist a live recording or refit history.</Text>
    </Panel>
  </Section>;
}
