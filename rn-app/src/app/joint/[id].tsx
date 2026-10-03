import { useLocalSearchParams } from 'expo-router';
import { Stack } from 'expo-router/stack';
import { useState } from 'react';
import { isOnline, useDemo } from '@/components/demo-provider';
import { LandingBaseline } from '@/components/landing-baseline';
import {
  Action,
  Badge,
  DemoHeader,
  DeviceSheet,
  Metric,
  Panel,
  Row,
  Screen,
  Section,
  SessionRow,
} from '@/components/monitoring-ui';
import { ThemedText as Text } from '@/components/themed-text';
import { formatDate, jointSessions, joints, reference, rom } from '@/data/demo';

export default function JointDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [open, setOpen] = useState(false);
  const { online } = useDemo();
  const joint = joints.find((item) => item.id === id);
  if (!joint)
    return (
      <Screen>
        <Text type="subtitle">Joint not found</Text>
        <Action href="/joints">Go to your joints</Action>
      </Screen>
    );
  const history = jointSessions(joint);
  const latest = history[0];
  const baseline = reference(joint, latest?.activity ?? 'Running');
  return (
    <>
      <Stack.Screen options={{ title: joint.name }} />
      <Screen>
        <DemoHeader
          label={
            latest
              ? `Latest recording · ${formatDate(latest.date)}`
              : 'No recordings'
          }
        />
        <Row>
          <Badge muted={!isOnline(joint, online)}>
            {joint.monitored
              ? isOnline(joint, online)
                ? 'Online · demo'
                : 'Offline · demo'
              : 'Not monitored'}
          </Badge>
          <Action onPress={() => setOpen(true)}>View setup</Action>
        </Row>
        {latest ? (
          <>
            <Panel>
              <Text type="smallBold">
                Latest {latest.activity.toLowerCase()} recording
              </Text>
              <Row wrap>
                <Metric
                  label="Movement range"
                  value={String(rom(joint, latest))}
                  unit="°"
                  detail={`The angle range observed during this ${latest.activity.toLowerCase()} recording for the ${joint.name.toLowerCase()}. It is activity-specific movement range, not maximum joint capacity.`}
                />
                <Metric
                  label="Movement cycles"
                  value={latest.cycles.toLocaleString()}
                  detail="Detected activity-specific movement cycles. This derived count describes repetition exposure, not internal tissue stress."
                />
                <Metric
                  label="Activity duration"
                  value={String(latest.minutes)}
                  unit="min"
                  detail="Elapsed duration of the recorded activity. Invalid or missing samples are described separately by recording coverage."
                />
                <Metric
                  label="Valid coverage"
                  value={String(latest.coverage)}
                  unit="%"
                  detail="Percentage of the recording duration with valid samples. Gaps are not filled with zero movement."
                />
              </Row>
            </Panel>
            {joint.anatomy === 'Knee' ? <LandingBaseline initialSide={joint.id.startsWith('left') ? 'left' : 'right'} /> : <Section title="Personal baseline">
              <Panel>
                <Badge muted={baseline === null}>
                  {baseline !== null
                    ? 'Reference available'
                    : 'Still learning'}
                </Badge>
                <Text type="subtitle">
                  {baseline !== null
                    ? `${baseline.low}–${baseline.high}°`
                    : 'Building a comparable history'}
                </Text>
                <Text themeColor="textSecondary">
                  {baseline !== null
                    ? `Illustrative historical movement range for ${latest.activity.toLowerCase()}, with the same joint and pod placement. A usual pattern is a reference, not proof of ideal mechanics.`
                    : 'No learned reference is available for this joint and activity. Keep activity and attachment conditions consistent.'}
                </Text>
              </Panel>
            </Section>}
            <Section title="Functional assessments">
              {joint.anatomy === 'Knee' ? (
                <Panel>
                  <Badge muted>Demo assessment</Badge>
                  <Text type="smallBold">Standardized movement check</Text>
                  <Text type="metric">128°</Text>
                  <Text type="small" themeColor="textSecondary">
                    Sep 29 · example heel-slide check
                  </Text>
                  <Text type="small">
                    Previous: 126° on Sep 22, under the same example conditions.
                  </Text>
                  <Text type="small" themeColor="textSecondary">
                    Assessment results are kept separate from activity movement
                    range.
                  </Text>
                </Panel>
              ) : (
                <Text themeColor="textSecondary">
                  No functional assessments recorded for this joint.
                </Text>
              )}
              <Panel>
                <Text type="smallBold">Strength · unavailable</Text>
                <Text type="small" themeColor="textSecondary">
                  Force or torque requires a calibrated strength-assessment
                  setup. No strength accessory is connected.
                </Text>
              </Panel>
            </Section>
            <Section title="Recent recordings">
              {history.slice(0, 4).map((session) => (
                <SessionRow key={session.id} session={session} />
              ))}
            </Section>
          </>
        ) : (
          <Panel>
            <Text type="subtitle">No measurements yet</Text>
            <Text themeColor="textSecondary">
              This joint has no assigned devices or recorded activity. Its
              range, exposure, and baseline remain unavailable.
            </Text>
            <Action onPress={() => setOpen(true)}>
              See attachment requirements
            </Action>
          </Panel>
        )}
      </Screen>
      <DeviceSheet joint={joint} open={open} onClose={() => setOpen(false)} />
    </>
  );
}
