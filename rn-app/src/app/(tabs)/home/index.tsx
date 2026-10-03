import { Link } from 'expo-router';
import { useState } from 'react';
import { Pressable, View } from 'react-native';
import { isOnline, useDemo } from '@/components/demo-provider';
import {
  Action,
  Badge,
  PageIntro,
  DeviceSheet,
  Divider,
  Icon,
  Panel,
  Row,
  Screen,
  Section,
  SessionRow,
  Sheet,
} from '@/components/monitoring-ui';
import { ThemedText as Text } from '@/components/themed-text';
import { Palette as c, Spacing as s } from '@/constants/theme';
import { demoDate, formatDate, joints, rom, sessions } from '@/data/demo';

export default function HomeScreen() {
  const [devicesOpen, setDevicesOpen] = useState(false);
  const [exposureOpen, setExposureOpen] = useState(false);
  const { online } = useDemo();
  const today = sessions.filter((session) => session.offset === 0);
  const minutes = today.reduce((sum, session) => sum + session.minutes, 0);
  const coverage = Math.round(
    today.reduce(
      (sum, session) => sum + session.minutes * session.coverage,
      0,
    ) / minutes,
  );
  const tracked = joints.filter((joint) => joint.monitored);
  const connected = tracked.filter((joint) => isOnline(joint, online)).length;
  return (
    <>
      <Screen>
        <PageIntro
          title="Your movement today."
          description={formatDate(demoDate, true)}
        />
        <Row wrap>
          <View
            style={{ flexDirection: 'row', alignItems: 'center', gap: s.two }}>
            <Icon
              name={{ ios: 'wave.3.right', android: 'sensors', web: 'sensors' }}
            />
            <Text type="small">
              {connected} of {tracked.length} joint configurations online
            </Text>
          </View>
          <Action onPress={() => setDevicesOpen(true)}>Devices</Action>
        </Row>
        <Panel accent>
          <Row>
            <Text type="label" style={{ color: c.accent }}>
              Today’s activity exposure
            </Text>
            <Action
              onPress={() => setExposureOpen(true)}
              label="Explain activity exposure">
              About
            </Action>
          </Row>
          <Text type="metric" style={{ color: c.accent }}>
            {minutes}
            <Text type="subtitle" themeColor="textSecondary">
              {' '}
              min
            </Text>
          </Text>
          <Text themeColor="textSecondary">
            of activity across {today.length} recordings
          </Text>
          <Divider />
          <Row wrap>
            <Text type="small" themeColor="textSecondary">
              {coverage}% valid recording coverage
            </Text>
            <Text type="small" style={{ color: c.accent }}>
              Latest sync · 10:24
            </Text>
          </Row>
        </Panel>
        <Section
          title="Your joints today"
          action={<Action href="/joints">View all</Action>}>
          <Text type="small" themeColor="textSecondary">
            Movement from today’s running session
          </Text>
          {tracked.map((joint) => (
            <Link
              key={joint.id}
              href={{ pathname: '/joint/[id]', params: { id: joint.id } }}
              asChild>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={`View ${joint.name}`}
                style={{
                  paddingVertical: s.three,
                  paddingHorizontal: s.three,
                  backgroundColor: c.backgroundElement,
                  borderRadius: 24,
                  borderWidth: 1,
                  borderColor: c.border,
                  gap: s.three,
                }}>
                <Row>
                  <Text type="smallBold">{joint.name}</Text>
                  <Badge muted={!isOnline(joint, online)}>
                    {isOnline(joint, online)
                      ? 'Online · demo'
                      : 'Offline · demo'}
                  </Badge>
                </Row>
                <Row>
                  <View>
                    <Text type="subtitle">{rom(joint, today[0])}°</Text>
                    <Text type="small" themeColor="textSecondary">
                      Movement range
                    </Text>
                  </View>
                  <View>
                    <Text type="subtitle">
                      {today[0].cycles.toLocaleString()}
                    </Text>
                    <Text type="small" themeColor="textSecondary">
                      Movement cycles
                    </Text>
                  </View>
                  <Icon
                    name={{
                      ios: 'chevron.right',
                      android: 'chevron_right',
                      web: 'chevron_right',
                    }}
                    size={16}
                    color={c.textSecondary}
                  />
                </Row>
              </Pressable>
            </Link>
          ))}
        </Section>
        <Panel>
          <Text type="label" style={{ color: c.accent }}>
            A closer look
          </Text>
          <Text type="subtitle">
            Your knee’s range is within its usual running pattern.
          </Text>
          <Text type="small" themeColor="textSecondary">
            Today’s 92° sits within the illustrative 86–94° personal reference.
            Based on the right knee’s running recording, with 96% coverage.
          </Text>
          <Action href="/trends">Explore your trends →</Action>
        </Panel>
        <Section title="Recent activity">
          {sessions.slice(0, 3).map((session) => (
            <SessionRow key={session.id} session={session} />
          ))}
        </Section>
      </Screen>
      <DeviceSheet open={devicesOpen} onClose={() => setDevicesOpen(false)} />
      <Sheet
        title="Activity exposure"
        open={exposureOpen}
        onClose={() => setExposureOpen(false)}>
        <Badge muted>Demo · duration summary</Badge>
        <Text>
          Today’s {minutes} minutes combine running and walking recording
          durations. Coverage shows how much of that time has valid samples.
        </Text>
        <Text themeColor="textSecondary">
          Motion range and movement count add context for each joint. Duration
          alone does not measure joint force or tissue stress.
        </Text>
      </Sheet>
    </>
  );
}
