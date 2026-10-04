import { Stack } from 'expo-router/stack';
import { LandingBaseline } from '@/components/landing-baseline';
import { Badge, Screen } from '@/components/monitoring-ui';
import { ThemedText as Text } from '@/components/themed-text';

export default function DemoLabScreen() {
  return <Screen>
    <Stack.Screen options={{ title: 'Demo Lab' }} />
    <Badge muted>Synthetic data</Badge>
    <Text type="small" themeColor="textSecondary">Explore participants, recording faults, and reference history. These controls affect this experiment only.</Text>
    <LandingBaseline />
  </Screen>;
}
