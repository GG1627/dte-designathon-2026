import {
  Tabs,
  TabList,
  TabTrigger,
  TabSlot,
  type TabTriggerSlotProps,
} from 'expo-router/ui';
import { Pressable, View } from 'react-native';
import { Icon } from '@/components/monitoring-ui';
import { ThemedText as Text } from '@/components/themed-text';
import { MaxContentWidth, Palette as c, Spacing as s } from '@/constants/theme';

export default function AppTabs() {
  return (
    <Tabs>
      <TabSlot style={{ flex: 1 }} />
      <TabList asChild>
        <View
          style={{
            position: 'absolute',
            bottom: 0,
            width: '100%',
            maxWidth: MaxContentWidth,
            alignSelf: 'center',
            flexDirection: 'row',
            padding: s.two,
            backgroundColor: c.backgroundElement,
            borderTopWidth: 1,
            borderTopColor: c.border,
            alignItems: 'center',
          }}>
          <TabTrigger name="home" href="/home" asChild>
            <TabButton icon="home">Home</TabButton>
          </TabTrigger>
          <TabTrigger name="trends" href="/trends" asChild>
            <TabButton icon="show_chart">Trends</TabButton>
          </TabTrigger>
          <TabTrigger name="joints" href="/joints" asChild>
            <TabButton icon="accessibility_new">Joints</TabButton>
          </TabTrigger>
          <TabTrigger name="live" href="/live" asChild>
            <TabButton icon="sensors">Live</TabButton>
          </TabTrigger>
        </View>
      </TabList>
    </Tabs>
  );
}

function TabButton({
  children,
  isFocused,
  icon,
  ...props
}: TabTriggerSlotProps & {
  icon: 'home' | 'show_chart' | 'accessibility_new' | 'sensors';
}) {
  return (
    <Pressable
      {...props}
      accessibilityRole="tab"
      accessibilityLabel={typeof children === 'string' ? children : undefined}
      accessibilityState={{ selected: isFocused }}
      style={({ pressed }) => ({
        flex: 1,
        minHeight: 64,
        alignItems: 'center',
        justifyContent: 'center',
        gap: s.one,
        opacity: pressed ? 0.6 : 1,
      })}>
      <Icon
        name={{ web: icon, android: icon }}
        color={isFocused ? c.accent : c.textSecondary}
      />
      <Text
        type="small"
        style={{ color: isFocused ? c.accent : c.textSecondary }}>
        {children}
      </Text>
    </Pressable>
  );
}
