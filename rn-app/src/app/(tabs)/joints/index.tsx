import { Link } from 'expo-router';
import { useState } from 'react';
import { Pressable, View } from 'react-native';
import { isOnline, useDemo } from '@/components/demo-provider';
import {
  Action,
  Badge,
  PageIntro,
  DeviceSheet,
  Icon,
  Row,
  Screen,
  Section,
} from '@/components/monitoring-ui';
import { ThemedText as Text } from '@/components/themed-text';
import { Palette as c, Spacing as s } from '@/constants/theme';
import { joints, type Joint } from '@/data/demo';

export default function JointsScreen() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Screen>
        <PageIntro
          title="Built around you."
          description="Individual joints. Personal patterns."
        />
        <Section
          title="Monitored"
          action={<Action onPress={() => setOpen(true)}>Devices</Action>}>
          {joints
            .filter((joint) => joint.monitored)
            .map((joint) => (
              <JointRow key={joint.id} joint={joint} />
            ))}
        </Section>
        <Section title="Other joints">
          {joints
            .filter((joint) => !joint.monitored)
            .map((joint) => (
              <JointRow key={joint.id} joint={joint} />
            ))}
        </Section>
        <Text type="small" themeColor="textSecondary">
          Each side has its own history and baseline. Measurements stay
          associated with where the device was worn.
        </Text>
      </Screen>
      <DeviceSheet open={open} onClose={() => setOpen(false)} />
    </>
  );
}

function JointRow({ joint }: { joint: Joint }) {
  const { online } = useDemo();
  return (
    <Link href={{ pathname: '/joint/[id]', params: { id: joint.id } }} asChild>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`View ${joint.name}`}
        style={{
          minHeight: 92,
          paddingVertical: s.three,
          paddingHorizontal: s.three,
          backgroundColor: joint.monitored ? c.backgroundElement : c.background,
          borderRadius: 24,
          borderWidth: 1,
          borderColor: c.border,
          gap: s.two,
        }}>
        <Row>
          <View style={{ flex: 1, gap: s.one }}>
            <Text type="smallBold">{joint.name}</Text>
            <Text type="small" themeColor="textSecondary">
              {joint.monitored
                ? `${joint.devices.length} pods · ${joint.baselineReady ? 'Reference available' : 'Learning your baseline'}`
                : 'Not monitored · no data'}
            </Text>
          </View>
          {joint.monitored ? (
            <Badge muted={!isOnline(joint, online)}>
              {isOnline(joint, online) ? 'Online' : 'Offline'}
            </Badge>
          ) : null}
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
  );
}
