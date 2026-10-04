import { useSetup } from '@/components/setup-provider';
import { PersonalReference } from '@/components/setup-ui';
import { Link } from 'expo-router';
import { useState } from 'react';
import { Pressable, View } from 'react-native';
import { isOnline, useDemo } from '@/components/demo-provider';
import { Action, DeviceSheet, Divider, Icon, PageIntro, Panel, Screen, Section, SessionRow } from '@/components/monitoring-ui';
import { ThemedText as Text } from '@/components/themed-text';
import { Palette as c, Spacing as s } from '@/constants/theme';
import { demoDate, formatDate, joints, rom, sessions } from '@/data/demo';

export default function HomeScreen() {
  const { setup } = useSetup();
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
      <Panel accent>
        <Text type="subtitle">{setup.setup_status === 'complete' ? 'Kintra is ready' : setup.setup_status === 'in_progress' ? 'Setup incomplete' : 'Get ready to move'}</Text>
        <Text type="small" themeColor="textSecondary">{setup.setup_status === 'complete' ? 'Sensor fit and movement checks complete in this demo.' : 'Help Kintra learn how your sensors are positioned and how you move.'}</Text>
        <Action primary href="/setup">{setup.setup_status === 'complete' ? 'Review Kintra setup' : setup.setup_status === 'in_progress' ? 'Resume Kintra setup' : 'Set up Kintra'}</Action>
      </Panel>
      {setup.setup_status === 'complete' ? <PersonalReference setup={setup} /> : null}
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
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: s.two }}>
        <Text type="small" themeColor="textSecondary">{minutes} min recorded · {today.length} recordings today</Text>
        <Action href="/onboarding">Knee guide</Action>
      </View>
    </Screen>
    <DeviceSheet open={devicesOpen} onClose={() => setDevicesOpen(false)} />
  </>;
}
