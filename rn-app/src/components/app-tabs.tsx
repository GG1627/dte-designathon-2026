import { NativeTabs } from 'expo-router/unstable-native-tabs';
import { Palette as c } from '@/constants/theme';

export default function AppTabs() {
  return (
    <NativeTabs
      backgroundColor={c.backgroundElement}
      tintColor={c.accent}
      iconColor={{ default: c.textSecondary, selected: c.accent }}
      indicatorColor={c.accentMuted}
      disableTransparentOnScrollEdge
      labelStyle={{
        default: { color: c.textSecondary },
        selected: { color: c.accent },
      }}>
      <NativeTabs.Trigger name="home">
        <NativeTabs.Trigger.Label>Home</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: 'house', selected: 'house.fill' }}
          md="home"
        />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="trends">
        <NativeTabs.Trigger.Label>Trends</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="chart.xyaxis.line" md="show_chart" />
      </NativeTabs.Trigger>
      <NativeTabs.Trigger name="joints">
        <NativeTabs.Trigger.Label>Joints</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="figure.walk" md="accessibility_new" />
      </NativeTabs.Trigger>
      <NativeTabs.Trigger name="live">
        <NativeTabs.Trigger.Label>Live</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="waveform.path" md="sensors" />
      </NativeTabs.Trigger>
    </NativeTabs>
  );
}
