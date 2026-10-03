import { Stack } from 'expo-router/stack';
import { Palette as c } from '@/constants/theme';

export function TabStack({ title }: { title: string }) {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        headerLargeTitleEnabled: true,
        headerStyle: { backgroundColor: c.background },
        headerLargeStyle: { backgroundColor: c.background },
        headerTitleStyle: { color: c.text },
        headerTintColor: c.accent,
        headerShadowVisible: false,
        headerLargeTitleShadowVisible: false,
        contentStyle: { backgroundColor: c.background },
      }}>
      <Stack.Screen name="index" options={{ title }} />
    </Stack>
  );
}
