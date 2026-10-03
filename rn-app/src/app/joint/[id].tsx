import { useLocalSearchParams } from 'expo-router';
import { Stack } from 'expo-router/stack';
import { useState } from 'react';
import { isOnline, useDemo } from '@/components/demo-provider';
import { LandingBaseline } from '@/components/landing-baseline';
import { Action, Badge, DemoHeader, DeviceSheet, Divider, Panel, Row, Screen, Section, SessionRow, Sheet } from '@/components/monitoring-ui';
import { SelectionControl } from '@/components/selection-control';
import { ThemedText as Text } from '@/components/themed-text';
import { Palette as c } from '@/constants/theme';
import { formatDate, jointSessions, joints, rom } from '@/data/demo';

export default function JointDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [setupOpen, setSetupOpen] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [assessmentsOpen, setAssessmentsOpen] = useState(false);
  const [activity, setActivity] = useState('Running');
  const { online } = useDemo();
  const joint = joints.find((item) => item.id === id);
  if (!joint) return <Screen><Text type="subtitle">Joint not found</Text><Action href="/joints">Go to your joints</Action></Screen>;
  const history = jointSessions(joint);
  const latest = history.find((session) => session.activity === activity);
  const landing = activity === 'Landings';
  const activities = ['Running', 'Walking', ...(joint.anatomy === 'Knee' ? ['Landings'] : [])];
  return <>
    <Stack.Screen options={{ title: joint.name }} />
    <Screen>
      <DemoHeader label={landing ? 'Landing comparison' : latest ? `Latest recording · ${formatDate(latest.date)}` : 'No recordings'} />
      {!joint.monitored ? <Panel>
        <Text type="subtitle">No measurements yet</Text>
        <Text themeColor="textSecondary">Connect devices to start recording this joint.</Text>
        <Action onPress={() => setSetupOpen(true)}>View setup</Action>
      </Panel> : <>
        <SelectionControl label="Activity" value={activity} onChange={setActivity}
          options={activities.map((value) => ({ value, label: value }))} />
        {!isOnline(joint, online) ? <Text type="small" themeColor="textSecondary">Device offline · showing recorded data</Text> : null}
        {landing ? <LandingBaseline mode="summary" initialSide={joint.id.startsWith('left') ? 'left' : 'right'} /> : latest ? <>
          <Panel>
            <Row><Text type="smallBold">Movement range</Text><Action onPress={() => setDetailsOpen(true)}>Details</Action></Row>
            <Text type="metric" style={{ color: c.accent }}>{rom(joint, latest)}<Text type="subtitle" themeColor="textSecondary">°</Text></Text>
            <Text type="small" themeColor="textSecondary">{latest.activity} · {latest.minutes} min</Text>
            <Divider />
            <Text type="small" themeColor="textSecondary">No {latest.activity.toLowerCase()} reference available.</Text>
          </Panel>
          <Section title="Recent recordings">
            {history.filter((session) => session.activity === activity).slice(0, 2).map((session) => <SessionRow key={session.id} session={session} />)}
          </Section>
        </> : <Text themeColor="textSecondary">No recordings for this activity.</Text>}
        <Row wrap><Action onPress={() => setAssessmentsOpen(true)}>Assessments</Action><Action onPress={() => setSetupOpen(true)}>Device setup</Action></Row>
      </>}
    </Screen>
    <DeviceSheet joint={joint} open={setupOpen} onClose={() => setSetupOpen(false)} />
    <Sheet title="Recording details" open={detailsOpen} onClose={() => setDetailsOpen(false)}>
      {latest ? <>
        <Text>{joint.name} · {latest.activity} · {formatDate(latest.date)}</Text>
        <Row wrap><Text>Movement cycles</Text><Text>{latest.cycles.toLocaleString()}</Text></Row>
        <Row wrap><Text>Valid coverage</Text><Text>{latest.coverage}%</Text></Row>
        <Text type="small" themeColor="textSecondary">Movement range describes this activity, not maximum joint capacity. Missing samples are not filled with zero.</Text>
      </> : null}
    </Sheet>
    <Sheet title="Assessments" open={assessmentsOpen} onClose={() => setAssessmentsOpen(false)}>
      {joint.anatomy === 'Knee' ? <>
        <Badge muted>Demo movement check</Badge>
        <Text type="subtitle">128°</Text>
        <Text>Heel-slide check · Sep 29</Text>
        <Text type="small">Previous: 126° on Sep 22 under the same example conditions.</Text>
        <Text type="small" themeColor="textSecondary">Assessment range stays separate from activity movement range.</Text>
      </> : <Text>No movement assessments recorded.</Text>}
      <Divider />
      <Text type="smallBold">Strength unavailable</Text>
      <Text type="small" themeColor="textSecondary">Requires a calibrated strength-assessment accessory.</Text>
    </Sheet>
  </>;
}
