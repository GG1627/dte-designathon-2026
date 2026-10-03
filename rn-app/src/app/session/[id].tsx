import { useLocalSearchParams } from 'expo-router';
import { Stack } from 'expo-router/stack';
import { useState } from 'react';
import { Action, DemoHeader, Divider, Panel, Row, Screen, Section, Sheet } from '@/components/monitoring-ui';
import { ThemedText as Text } from '@/components/themed-text';
import { Palette as c } from '@/constants/theme';
import { formatDate, joints, rom, sessions } from '@/data/demo';

export default function SessionScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [open, setOpen] = useState(false);
  const session = sessions.find((item) => item.id === id);
  if (!session) return <Screen><Text type="subtitle">Recording not found</Text><Action href="/home">Go home</Action></Screen>;
  const tracked = joints.filter((joint) => joint.monitored && (joint.id === 'right-knee' || session.offset <= 10));
  return <>
    <Stack.Screen options={{ title: session.activity }} />
    <Screen>
      <DemoHeader label={formatDate(session.date, true)} />
      <Panel>
        <Row><Text type="smallBold">Recorded activity</Text><Action onPress={() => setOpen(true)}>Details</Action></Row>
        <Text type="metric" style={{ color: c.accent }}>{session.minutes}<Text type="subtitle" themeColor="textSecondary"> min</Text></Text>
        {session.coverage < 80 ? <Text type="small">Incomplete recording · excluded from trends</Text> : null}
      </Panel>
      <Section title="Movement range">
        {tracked.map((joint) => <Row key={joint.id}>
          <Text>{joint.name}</Text><Text type="subtitle">{rom(joint, session)}°</Text>
        </Row>)}
        <Text type="small" themeColor="textSecondary">No {session.activity.toLowerCase()} reference available.</Text>
      </Section>
    </Screen>
    <Sheet title="Recording details" open={open} onClose={() => setOpen(false)}>
      <Text>{session.activity} · {formatDate(session.date)}</Text>
      <Row wrap><Text>Valid coverage</Text><Text>{session.coverage}%</Text></Row>
      <Row wrap><Text>Movement cycles</Text><Text>{session.cycles.toLocaleString()}</Text></Row>
      <Text type="small">{((session.minutes * session.coverage) / 100).toFixed(1)} min of valid data out of {session.minutes} min.</Text>
      <Divider />
      <Text type="small">Recordings below 80% valid coverage are excluded from trends. Missing time is not zero movement.</Text>
      <Text type="small" themeColor="textSecondary">Activity movement range is separate from assessments and landing references. These are synthetic measurements.</Text>
    </Sheet>
  </>;
}
