import { useLocalSearchParams } from 'expo-router';
import { Stack } from 'expo-router/stack';
import {
  Badge,
  DemoHeader,
  Metric,
  Panel,
  Row,
  Screen,
  Section,
} from '@/components/monitoring-ui';
import { ThemedText as Text } from '@/components/themed-text';
import { Palette as c } from '@/constants/theme';
import { formatDate, joints, reference, rom, sessions } from '@/data/demo';

export default function SessionScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const session = sessions.find((item) => item.id === id);
  if (!session)
    return (
      <Screen>
        <Text type="subtitle">Recording not found</Text>
        <Text themeColor="textSecondary">
          Return to the previous screen to choose another recording.
        </Text>
      </Screen>
    );
  const tracked = joints.filter(
    (joint) =>
      joint.monitored && (joint.id === 'right-knee' || session.offset <= 10),
  );
  return (
    <Screen>
      <Stack.Screen options={{ title: session.activity }} />
      <DemoHeader label={formatDate(session.date, true)} />
      <Panel>
        <Text type="label" style={{ color: c.accent }}>
          Activity summary
        </Text>
        <Text type="metric">
          {session.minutes}
          <Text type="subtitle" themeColor="textSecondary">
            {' '}
            min
          </Text>
        </Text>
        <Row wrap>
          <Text type="small" themeColor="textSecondary">
            {session.coverage}% valid recording coverage
          </Text>
          <Badge muted>Activity grouping · demo</Badge>
        </Row>
      </Panel>
      {session.coverage < 80 ? (
        <Panel>
          <Text type="smallBold">Incomplete recording</Text>
          <Text themeColor="textSecondary">
            This session is excluded from trend comparisons because valid
            coverage is below the demo’s 80% rule.
          </Text>
        </Panel>
      ) : null}
      <Section title="Joint measurements">
        {tracked.map((joint) => {
          const baseline = reference(joint, session.activity);
          return (
            <Panel key={joint.id}>
              <Text type="subtitle">{joint.name}</Text>
              <Row wrap>
                <Metric
                  label="Movement range"
                  value={String(rom(joint, session))}
                  unit="°"
                  detail={`Observed angle range during ${session.activity.toLowerCase()}. Derived from relative joint motion in the demo; this is not maximum available range.`}
                />
                <Metric
                  label="Movement cycles"
                  value={session.cycles.toLocaleString()}
                  detail="Activity-specific detected motion cycles. Counts depend on event rules and recording quality."
                />
              </Row>
              <Text type="small" themeColor="textSecondary">
                {joint.baselineReady && baseline !== null && session.coverage >= 80
                  ? `Compared with an illustrative ${baseline.low}–${baseline.high}° reference for this joint and activity.`
                  : session.coverage < 80
                    ? 'Comparison unavailable because this recording is incomplete.'
                    : 'No learned reference for this activity. Landing references stay separate.'}
              </Text>
            </Panel>
          );
        })}
      </Section>
      <Section title="Recording context">
        <Text themeColor="textSecondary">
          {tracked.length} joint configurations · consistent demo placement
        </Text>
        <Text type="small" themeColor="textSecondary">
          {((session.minutes * session.coverage) / 100).toFixed(1)} min of valid
          data out of {session.minutes} min. Missing time is excluded from
          metric calculations.
        </Text>
        <Text type="small" themeColor="textSecondary">
          All values are synthetic. No force, strength, tissue recovery, or
          injury probability is inferred from this motion recording.
        </Text>
      </Section>
    </Screen>
  );
}
