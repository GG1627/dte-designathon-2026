import { DarkTheme, ThemeProvider } from 'expo-router/react-navigation';
import { Stack } from 'expo-router/stack';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';

import { DemoProvider } from '@/components/demo-provider';
import { Palette as c } from '@/constants/theme';

SplashScreen.preventAutoHideAsync().catch(() => {});
export const unstable_settings = { initialRouteName: 'index' };
const theme = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    primary: c.accent,
    background: c.background,
    card: c.background,
    text: c.text,
    border: c.border,
  },
};

export default function TabLayout() {
  useEffect(() => {
    SplashScreen.hideAsync().catch(() => {});
  }, []);
  return (
    <ThemeProvider value={theme}>
      <DemoProvider>
        <StatusBar style="light" />
        <Stack
          screenOptions={{
            headerStyle: { backgroundColor: c.background },
            headerTintColor: c.accent,
            headerTitleStyle: { color: c.text },
            headerShadowVisible: false,
            contentStyle: { backgroundColor: c.background },
          }}>
          <Stack.Screen name="index" options={{ headerShown: false, title: 'Kintra' }} />
          <Stack.Screen name="onboarding" options={{ headerShown: false, title: 'Knee guide' }} />
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen name="joint/[id]" options={{ title: 'Joint detail' }} />
          <Stack.Screen name="demo-lab" options={{ title: 'Demo Lab' }} />
          <Stack.Screen
            name="session/[id]"
            options={{ title: 'Session summary' }}
          />
        </Stack>
      </DemoProvider>
    </ThemeProvider>
  );
}
