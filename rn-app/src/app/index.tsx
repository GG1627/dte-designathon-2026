import { router } from 'expo-router';
import { SymbolView } from 'expo-symbols';
import { Pressable, ScrollView, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText as Text } from '@/components/themed-text';
import { KintraBrand as brand, Radius, Spacing as s } from '@/constants/theme';

export default function WelcomeScreen() {
  const insets = useSafeAreaInsets();

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: brand.background }}
      contentContainerStyle={{
        flexGrow: 1,
        alignItems: 'center',
        paddingHorizontal: s.four,
        paddingTop: Math.max(insets.top, s.four),
        paddingBottom: Math.max(insets.bottom, s.four),
      }}>
      <View style={{ flex: 1, width: '100%', maxWidth: 440, gap: s.five }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: s.two }}>
          <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: brand.accent }} />
          <Text type="label" style={{ color: brand.muted }}>Built around you</Text>
        </View>

        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', gap: s.four, paddingVertical: s.four }}>
          <View aria-hidden accessibilityElementsHidden importantForAccessibility="no-hide-descendants" style={{ width: 280, height: 280 }}>
            <View style={{ position: 'absolute', left: 24, top: 24, width: 232, height: 232, borderRadius: 116, borderWidth: 1, borderColor: brand.line }} />
            <View style={{ position: 'absolute', left: 4, top: 4, width: 272, height: 272, borderRadius: 136, borderWidth: 1, borderColor: brand.accentSoft, borderTopColor: 'transparent', borderLeftColor: 'transparent', transform: [{ rotate: '-24deg' }] }} />
            <View style={{ position: 'absolute', left: 86, top: 68, width: 12, height: 152, borderRadius: 6, backgroundColor: brand.text }} />
            <View style={{ position: 'absolute', left: 90, top: 96, width: 120, height: 12, borderRadius: 6, backgroundColor: brand.text, transform: [{ rotate: '-42deg' }] }} />
            <View style={{ position: 'absolute', left: 90, top: 176, width: 120, height: 12, borderRadius: 6, backgroundColor: brand.accent, transform: [{ rotate: '42deg' }] }} />
            <View style={{ position: 'absolute', left: 80, top: 118, width: 52, height: 52, borderRadius: 26, backgroundColor: brand.background, borderWidth: 3, borderColor: brand.accent, alignItems: 'center', justifyContent: 'center' }}>
              <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: brand.accent }} />
            </View>
          </View>

          <View style={{ alignItems: 'center', gap: s.three }}>
            <Text accessibilityRole="header" style={{ fontSize: 64, lineHeight: 76, fontWeight: '700', letterSpacing: -3, color: brand.text }}>Kintra</Text>
            <Text style={{ fontSize: 26, lineHeight: 34, fontWeight: '500', color: brand.text, textAlign: 'center' }}>Your movement,{ '\n' }understood.</Text>
            <Text type="small" style={{ color: brand.muted, textAlign: 'center' }}>Personalized joint monitoring.</Text>
          </View>
        </View>

        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Get started"
          accessibilityHint="Opens the Kintra home screen"
          onPress={() => router.replace('/home')}
          style={({ pressed }) => ({
            minHeight: 60,
            paddingHorizontal: s.four,
            paddingVertical: s.three,
            borderRadius: Radius.medium,
            borderCurve: 'continuous',
            backgroundColor: brand.accent,
            flexDirection: 'row',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: s.three,
            opacity: pressed ? 0.75 : 1,
          })}>
          <Text style={{ color: brand.background, fontWeight: '700', fontSize: 17 }}>Get started</Text>
          <View aria-hidden accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
            <SymbolView name={{ ios: 'arrow.right', android: 'arrow_forward', web: 'arrow_forward' }} size={22} tintColor={brand.background} />
          </View>
        </Pressable>
      </View>
    </ScrollView>
  );
}
