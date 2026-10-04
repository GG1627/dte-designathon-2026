import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { Platform, Pressable, ScrollView, View } from 'react-native';
import { useReducedMotion } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Icon } from '@/components/monitoring-ui';
import { ThemedText as Text } from '@/components/themed-text';
import { Palette as c, Radius, Spacing as s } from '@/constants/theme';
import { kneeGuide } from '@/data/knee-guide';
import { completeOnboarding } from '@/utils/onboarding';

export default function OnboardingScreen() {
  const insets = useSafeAreaInsets();
  const reducedMotion = useReducedMotion();
  const pager = useRef<ScrollView>(null);
  const activeIndex = useRef(0);
  const scrollEndTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [index, setIndex] = useState(0);
  const [width, setWidth] = useState(0);
  const [failedImages, setFailedImages] = useState<number[]>([]);

  // Keep the selected slide aligned when the viewport changes orientation.
  useEffect(() => {
    pager.current?.scrollTo({ x: activeIndex.current * width, animated: false });
  }, [width]);

  useEffect(() => () => {
    if (scrollEndTimer.current) clearTimeout(scrollEndTimer.current);
  }, []);

  function settle(offset: number) {
    if (!width) return;
    const next = Math.max(0, Math.min(kneeGuide.length - 1, Math.round(offset / width)));
    activeIndex.current = next;
    setIndex(next);
  }

  function goTo(next: number) {
    activeIndex.current = next;
    setIndex(next);
    pager.current?.scrollTo({ x: next * width, animated: !reducedMotion });
  }

  function finish() {
    completeOnboarding();
    router.dismissTo('/home');
  }

  return (
    <View style={{ flex: 1, backgroundColor: c.background, alignItems: 'center', paddingTop: insets.top, paddingBottom: insets.bottom, paddingLeft: insets.left, paddingRight: insets.right }}>
      <View style={{ flex: 1, width: '100%', maxWidth: 520 }} onLayout={(event) => setWidth(event.nativeEvent.layout.width)}>
        <View style={{ paddingHorizontal: s.four, paddingTop: s.two, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <Text type="label" themeColor="textSecondary">Kintra / Knee guide</Text>
          <Pressable accessibilityRole="button" accessibilityLabel="Skip introduction" onPress={finish}
            style={({ pressed }) => ({ minHeight: 48, minWidth: 48, justifyContent: 'center', alignItems: 'flex-end', opacity: pressed ? 0.6 : 1 })}>
            <Text type="smallBold">Skip</Text>
          </Pressable>
        </View>

        <ScrollView ref={pager} horizontal pagingEnabled bounces={false} directionalLockEnabled
          showsHorizontalScrollIndicator={false} contentInsetAdjustmentBehavior="never"
          testID="knee-guide-pager" style={{ flex: 1 }}
          onMomentumScrollEnd={(event) => settle(event.nativeEvent.contentOffset.x)}
          // RN web has scroll events but no native momentum-end callback.
          // Update React only after scrolling settles, rather than every frame.
          scrollEventThrottle={Platform.OS === 'web' ? 64 : undefined}
          onScroll={Platform.OS === 'web' ? (event) => {
            const offset = event.nativeEvent.contentOffset.x;
            if (scrollEndTimer.current) clearTimeout(scrollEndTimer.current);
            scrollEndTimer.current = setTimeout(() => settle(offset), 150);
          } : undefined}>
          {width > 0 ? kneeGuide.map((slide, slideIndex) => (
            <ScrollView key={slide.title} style={{ width }} contentInsetAdjustmentBehavior="never"
              showsVerticalScrollIndicator={false}
              aria-hidden={slideIndex !== index} accessibilityElementsHidden={slideIndex !== index}
              importantForAccessibility={slideIndex === index ? 'auto' : 'no-hide-descendants'}
              contentContainerStyle={{ flexGrow: 1, justifyContent: 'center', gap: s.four, paddingVertical: s.four }}>
              <View style={{ width: '100%', height: Math.min(width * 3 / 4, 340), justifyContent: 'center', alignItems: 'center' }}>
                {failedImages.includes(slideIndex) ? <Text type="small" themeColor="textSecondary">Illustration unavailable</Text> : (
                  <Image source={slide.image} contentFit="contain" accessible accessibilityLabel={slide.imageDescription}
                    style={{ width: '100%', height: '100%' }}
                    onError={() => setFailedImages((current) => current.includes(slideIndex) ? current : [...current, slideIndex])} />
                )}
              </View>
              <View style={{ paddingHorizontal: s.four, gap: s.three }}>
                <Text accessibilityRole="header" style={{ fontSize: 30, lineHeight: 38, fontWeight: '600', letterSpacing: -0.5 }}>{slide.title}</Text>
                <Text themeColor="textSecondary">{slide.description}</Text>
                {'note' in slide ? <Text type="small" themeColor="textSecondary">{slide.note}</Text> : null}
              </View>
            </ScrollView>
          )) : null}
        </ScrollView>

        <View style={{ paddingHorizontal: s.four, paddingBottom: s.four, gap: s.two }}>
          <View style={{ alignItems: 'center' }}>
            <Text type="small" themeColor="textSecondary" accessibilityLiveRegion="polite">{index + 1} of {kneeGuide.length}</Text>
            <View style={{ flexDirection: 'row' }}>
              {kneeGuide.map((slide, slideIndex) => (
                <Pressable key={slide.title} accessibilityRole="button" accessibilityLabel={`Slide ${slideIndex + 1}: ${slide.title}`}
                  accessibilityState={{ selected: slideIndex === index }} onPress={() => goTo(slideIndex)}
                  style={({ pressed }) => ({ width: 48, height: 48, alignItems: 'center', justifyContent: 'center', opacity: pressed ? 0.6 : 1 })}>
                  <View style={{ width: slideIndex === index ? 24 : 8, height: 8, borderRadius: 4, backgroundColor: slideIndex === index ? c.accent : c.textSecondary }} />
                </Pressable>
              ))}
            </View>
          </View>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: s.three }}>
            {index > 0 ? (
              <Pressable accessibilityRole="button" accessibilityLabel="Previous slide" onPress={() => goTo(index - 1)}
                style={({ pressed }) => ({ minWidth: 64, minHeight: 60, justifyContent: 'center', opacity: pressed ? 0.6 : 1 })}>
                <Text type="smallBold">Back</Text>
              </Pressable>
            ) : null}
            <Pressable accessibilityRole="button" onPress={() => index === kneeGuide.length - 1 ? finish() : goTo(index + 1)}
              style={({ pressed }) => ({ flex: 1, minHeight: 60, padding: s.three, borderRadius: Radius.medium, borderCurve: 'continuous', backgroundColor: c.accent, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: s.three, opacity: pressed ? 0.75 : 1 })}>
              <Text style={{ color: c.background, fontWeight: '700', fontSize: 17 }}>{index === kneeGuide.length - 1 ? 'Explore the app' : 'Next'}</Text>
              <Icon name={{ ios: 'arrow.right', android: 'arrow_forward', web: 'arrow_forward' }} size={22} color={c.background} />
            </Pressable>
          </View>
        </View>
      </View>
    </View>
  );
}
