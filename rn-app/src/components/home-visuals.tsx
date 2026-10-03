import { View } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import { ThemedText as Text } from '@/components/themed-text';
import { Palette as c, Spacing as s } from '@/constants/theme';

export function CoverageRing({ value }: { value: number }) {
  const fraction = Math.max(0, Math.min(value, 100)) / 100;
  const circumference = 2 * Math.PI * 59;
  return (
    <View
      accessible
      accessibilityLabel={`${value}% valid recording coverage`}
      style={{
        width: 128,
        height: 128,
        alignItems: 'center',
        justifyContent: 'center',
      }}>
      <View
        aria-hidden
        accessibilityElementsHidden
        importantForAccessibility="no-hide-descendants"
        style={{ position: 'absolute', width: 128, height: 128 }}>
        <Svg width={128} height={128} viewBox="0 0 128 128">
          <Circle
            cx={64}
            cy={64}
            r={59}
            fill="none"
            stroke={c.backgroundSelected}
            strokeWidth={8}
          />
          {fraction > 0 && (
            <Circle
              cx={64}
              cy={64}
              r={59}
              fill="none"
              stroke={c.accent}
              strokeWidth={8}
              strokeLinecap="round"
              strokeDasharray={`${circumference * fraction} ${circumference}`}
              transform="rotate(-90 64 64)"
            />
          )}
        </Svg>
      </View>
      <Text
        style={{
          fontSize: 32,
          lineHeight: 40,
          fontWeight: '700',
          color: c.text,
          fontVariant: ['tabular-nums'],
        }}>
        {value}%
      </Text>
      <Text type="small" themeColor="textSecondary">
        Valid coverage
      </Text>
    </View>
  );
}

export function ActivityBar({
  label,
  minutes,
  total,
}: {
  label: string;
  minutes: number;
  total: number;
}) {
  return (
    <View
      accessible
      accessibilityLabel={`${label}: ${minutes} of ${total} recorded minutes`}
      style={{ gap: s.two }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
        <Text type="small" themeColor="textSecondary">
          {label}
        </Text>
        <Text type="smallBold">{minutes} min</Text>
      </View>
      <View
        style={{
          height: 7,
          borderRadius: 4,
          backgroundColor: c.backgroundSelected,
          overflow: 'hidden',
        }}>
        <View
          style={{
            height: '100%',
            width: `${total ? (minutes / total) * 100 : 0}%`,
            backgroundColor: c.accent,
            borderRadius: 4,
          }}
        />
      </View>
    </View>
  );
}

export function JointRangeScale({
  value,
  low,
  high,
  ready,
}: {
  value: number;
  low: number;
  high: number;
  ready: boolean;
}) {
  const maximum = Math.ceil((Math.max(value, high) + 10) / 20) * 20;
  return (
    <View
      accessible
      accessibilityLabel={`Movement range ${value} degrees. ${ready ? `Personal reference ${low} to ${high} degrees.` : 'Personal baseline developing.'} Scale 0 to ${maximum} degrees.`}
      style={{ gap: s.two }}>
      <View style={{ height: 16, justifyContent: 'center' }}>
        <View
          style={{
            height: 6,
            borderRadius: 3,
            backgroundColor: c.backgroundSelected,
          }}
        />
        {ready && (
          <View
            style={{
              position: 'absolute',
              left: `${(low / maximum) * 100}%`,
              width: `${((high - low) / maximum) * 100}%`,
              height: 16,
              borderRadius: 3,
              backgroundColor: c.comparisonMuted,
              borderWidth: 1,
              borderColor: c.comparison,
            }}
          />
        )}
        <View
          style={{
            position: 'absolute',
            left: `${(value / maximum) * 100}%`,
            width: 4,
            marginLeft: -2,
            height: 16,
            borderRadius: 2,
            backgroundColor: c.accent,
          }}
        />
      </View>
      <View
        style={{
          flexDirection: 'row',
          justifyContent: 'space-between',
          gap: s.two,
        }}>
        <Text type="small" themeColor="textSecondary">
          0°
        </Text>
        <Text
          type="small"
          style={{ color: ready ? c.comparison : c.textSecondary }}>
          {ready ? `Reference ${low}–${high}°` : 'Baseline developing'}
        </Text>
        <Text type="small" themeColor="textSecondary">
          {maximum}°
        </Text>
      </View>
    </View>
  );
}
