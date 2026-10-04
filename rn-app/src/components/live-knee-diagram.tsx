import { useEffect } from 'react';
import { View } from 'react-native';
import Animated, {
  Easing,
  useAnimatedProps,
  useReducedMotion,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';
import Svg, { Circle, Line, Text as SvgText } from 'react-native-svg';

import { Palette as c } from '@/constants/theme';
import { SAMPLE_INTERVAL_MS } from '@/data/live-simulation';

const AnimatedLine = Animated.createAnimatedComponent(Line);
const AnimatedCircle = Animated.createAnimatedComponent(Circle);
const radians = Math.PI / 180;

export function LiveKneeDiagram({
  thighAngle,
  shankAngle,
}: {
  thighAngle: number;
  shankAngle: number;
}) {
  const thigh = useSharedValue(thighAngle);
  const shank = useSharedValue(shankAngle);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    // Numeric samples update at 20 Hz; interpolation runs on the UI thread.
    const config = { duration: SAMPLE_INTERVAL_MS, easing: Easing.linear };
    thigh.value = reducedMotion ? thighAngle : withTiming(thighAngle, config);
    shank.value = reducedMotion ? shankAngle : withTiming(shankAngle, config);
  }, [thighAngle, shankAngle, thigh, shank, reducedMotion]);

  const thighProps = useAnimatedProps(() => ({
    x1: 160 - 95 * Math.sin(thigh.value * radians),
    y1: 165 - 95 * Math.cos(thigh.value * radians),
  }));
  const shankProps = useAnimatedProps(() => ({
    x2: 160 + 110 * Math.sin(shank.value * radians),
    y2: 165 + 110 * Math.cos(shank.value * radians),
  }));
  const hipProps = useAnimatedProps(() => ({
    cx: 160 - 95 * Math.sin(thigh.value * radians),
    cy: 165 - 95 * Math.cos(thigh.value * radians),
  }));
  const ankleProps = useAnimatedProps(() => ({
    cx: 160 + 110 * Math.sin(shank.value * radians),
    cy: 165 + 110 * Math.cos(shank.value * radians),
  }));

  return (
    <View
      accessible
      accessibilityRole="image"
      accessibilityLabel="Simulated thigh and shank movement. Open reading details for segment angles."
      style={{ width: '100%', height: 270 }}>
      <Svg width="100%" height="100%" viewBox="0 0 340 310" aria-hidden>
        <Line x1={160} y1={42} x2={160} y2={285} stroke={c.border} strokeDasharray="4 6" />
        <Circle cx={160} cy={165} r={48} fill="none" stroke={c.border} />
        <AnimatedLine animatedProps={thighProps} x2={160} y2={165}
          stroke={c.comparison} strokeWidth={18} strokeLinecap="round" />
        <AnimatedLine animatedProps={shankProps} x1={160} y1={165}
          stroke={c.accent} strokeWidth={18} strokeLinecap="round" />
        <AnimatedCircle animatedProps={hipProps} r={7} fill={c.comparison} />
        <AnimatedCircle animatedProps={ankleProps} r={7} fill={c.accent} />
        <Circle cx={160} cy={165} r={13} fill={c.backgroundElement} stroke={c.text} strokeWidth={3} />
        <SvgText x={38} y={90} fontSize={12} fill={c.comparison}>THIGH</SvgText>
        <SvgText x={38} y={258} fontSize={12} fill={c.accent}>SHANK</SvgText>
      </Svg>
    </View>
  );
}
