import { useSetup } from '@/components/setup-provider';
import { HomeMovementFeedback } from '@/components/home-movement-feedback';
import { Link } from 'expo-router';
import { useState } from 'react';
import { Pressable, View } from 'react-native';
import { isOnline, useDemo } from '@/components/demo-provider';
import { Action, DeviceSheet, Divider, Icon, PageIntro, Panel, Row, Screen, Section, SessionRow } from '@/components/monitoring-ui';
import { ThemedText as Text } from '@/components/themed-text';
import { Palette as c, Spacing as s } from '@/constants/theme';
import { demoDate, formatDate, joints, rom, sessions } from '@/data/demo';

export default function HomeScreen() {
  const { setup } = useSetup();
  const ready = setup.setup_status === 'complete';
  const [devicesOpen, setDevicesOpen] = useState(false);
  const { online } = useDemo();
  const today = sessions.filter((session) => session.offset === 0);
  const latest = today[0];
  const minutes = today.reduce((sum, session) => sum + session.minutes, 0);
  const tracked = joints.filter((joint) => joint.monitored);
  const disconnected = tracked.filter((joint) => !isOnline(joint, online));
  return <>
    <Screen>
      <PageIntro title="Today" description={formatDate(demoDate, true)} />
      {!ready && <Row wrap>
        <Text type="small" themeColor="textSecondary">Start tracking your movement</Text>
        <Action href="/setup">{setup.setup_status === 'in_progress' ? 'Resume setup' : 'Set up Kintra'}</Action>
      </Row>}
      {ready ? <>
      <HomeMovementFeedback />
      <Section title="Your joints" action={<Action onPress={() => setDevicesOpen(true)}>Devices</Action>}>
        <Text type="small" themeColor="textSecondary">{latest ? `Movement range · today’s ${latest.activity.toLowerCase()}` : 'No recordings today'}</Text>
        <Panel>
          {tracked.map((joint, index) => <View key={joint.id} style={{ gap: s.three }}>
            {index > 0 ? <Divider /> : null}
            <Link href={{ pathname: '/joint/[id]', params: { id: joint.id } }} asChild>
              <Pressable accessibilityRole="button" accessibilityLabel={`View ${joint.name}${latest ? `, movement range ${rom(joint, latest)} degrees` : ''}`}
                style={{ minHeight: 80, flexDirection: 'row', alignItems: 'center', gap: s.three }}>
                <View style={{ flex: 1, gap: s.one }}>
                  <Text type="smallBold">{joint.name}</Text>
                  {!isOnline(joint, online) ? <Text type="small" themeColor="textSecondary">Device offline</Text> : null}
                </View>
                <Text type="title" style={{ color: c.accent, fontVariant: ['tabular-nums'] }}>{latest ? `${rom(joint, latest)}°` : '—'}</Text>
                <Icon name={{ ios: 'chevron.right', android: 'chevron_right', web: 'chevron_right' }} size={16} color={c.textSecondary} />
              </Pressable>
            </Link>
          </View>)}
        </Panel>
        {disconnected.length ? <Text type="small" themeColor="textSecondary">Device connection unavailable. Recorded measurements are still available.</Text> : null}
      </Section>
      <Section title="Latest recording" action={<Action href="/trends">History</Action>}>
        {latest ? <SessionRow session={latest} /> : <Text themeColor="textSecondary">Your next recording will appear here.</Text>}
      </Section>
      </> : <View style={{ gap: s.two, paddingVertical: s.four }}>
        <Text type="subtitle">Your movement starts here</Text>
        <Text themeColor="textSecondary">Complete the demo setup to explore readings, a personal baseline, and your next step.</Text>
      </View>}
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: s.two }}>
        {ready ? <Text type="small" themeColor="textSecondary">{minutes} min recorded · {today.length} demo recordings today</Text> : null}
        <Action href="/onboarding">Knee guide</Action>
        {ready ? <Action href="/setup">Review setup</Action> : null}
      </View>
    </Screen>
    <DeviceSheet open={devicesOpen} onClose={() => setDevicesOpen(false)} />
  </>;
}
