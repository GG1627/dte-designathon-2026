import { createElement, useState } from 'react';
import { Platform, View } from 'react-native';
import Animated, { FadeInDown, ReduceMotion } from 'react-native-reanimated';
import { Action, Badge, Row, Sheet } from '@/components/monitoring-ui';
import { ThemedText as Text } from '@/components/themed-text';
import { Palette as c, Spacing as s } from '@/constants/theme';
import {
  average,
  formatDate,
  reference,
  rom,
  type Activity,
  type Joint,
  type Session,
} from '@/data/demo';

export function RangeChart({
  joint,
  activity,
  records,
}: {
  joint: Joint;
  activity: Activity;
  records: Session[];
}) {
  const [open, setOpen] = useState(false);
  const ordered = [...records].reverse();
  const values = ordered.map((session) => rom(joint, session));
  const mean = average(values);
  const baseline = reference(joint, activity);
  const hasReference = joint.baselineReady && baseline !== null;
  const max = Math.ceil(Math.max(...values, baseline?.high ?? 0) / 20) * 20 + 20;
  const height = 160;
  if (mean === null)
    return (
      <View style={{ paddingVertical: s.four, gap: s.two }}>
        <Text type="smallBold">No comparable recordings</Text>
        <Text type="small" themeColor="textSecondary">
          Choose another activity or period. Missing recordings are not zero
          movement.
        </Text>
      </View>
    );
  const chart = (
    <Animated.View
      entering={
        Platform.OS === 'web'
          ? undefined
          : FadeInDown.duration(140)
              .withInitialValues({ opacity: 0, transform: [{ translateY: 4 }] })
              .reduceMotion(ReduceMotion.System)
      }
      style={{ gap: s.three }}>
      <Row>
        <View style={{ gap: s.one }}>
          <Text type="small" themeColor="textSecondary">
            Average movement range
          </Text>
          <Text type="metric" style={{ color: c.accent }}>
            {Math.round(mean)}
            <Text type="subtitle" themeColor="textSecondary">
              °
            </Text>
          </Text>
        </View>
        <Action onPress={() => setOpen(true)}>View data</Action>
      </Row>
      <View
        accessible
        accessibilityLabel={`${joint.name}, ${activity}. Average movement range ${Math.round(mean)} degrees over ${records.length} comparable recordings.${hasReference ? ` Personal reference ${baseline.low} to ${baseline.high} degrees.` : ' No learned reference for this activity.'}`}
        style={{ flexDirection: 'row', gap: s.two }}>
        <View style={{ height, justifyContent: 'space-between', width: 32 }}>
          <Text type="small" themeColor="textSecondary">
            {max}°
          </Text>
          <Text type="small" themeColor="textSecondary">
            {max / 2}°
          </Text>
          <Text type="small" themeColor="textSecondary">
            0°
          </Text>
        </View>
        <View
          style={{
            flex: 1,
            height,
            borderBottomWidth: 1,
            borderBottomColor: c.border,
          }}>
          {[0.25, 0.5, 0.75, 1].map((fraction) => (
            <View
              key={fraction}
              style={{
                position: 'absolute',
                bottom: `${fraction * 100}%`,
                width: '100%',
                borderTopWidth: 1,
                borderTopColor: c.border,
                opacity: 0.5,
              }}
            />
          ))}
          {hasReference ? (
            <View
              style={{
                position: 'absolute',
                width: '100%',
                bottom: `${(baseline.low / max) * 100}%`,
                height: ((baseline.high - baseline.low) / max) * height,
                backgroundColor: c.comparisonMuted,
                borderTopWidth: 1,
                borderBottomWidth: 1,
                borderColor: c.comparison,
              }}
            />
          ) : null}
          <View
            style={{
              height,
              flexDirection: 'row',
              alignItems: 'flex-end',
              gap: s.one,
              paddingHorizontal: s.one,
            }}>
            {ordered.map((session, index) => (
              <View
                key={session.id}
                style={{
                  flex: 1,
                  height: (rom(joint, session) / max) * height,
                  backgroundColor: c.accent,
                  opacity: index === ordered.length - 1 ? 1 : 0.55,
                  borderTopLeftRadius: 4,
                  borderTopRightRadius: 4,
                }}
              />
            ))}
          </View>
        </View>
      </View>
      <Row>
        <Text type="small" themeColor="textSecondary">
          {formatDate(ordered[0].date)}
        </Text>
        <Text type="small" themeColor="textSecondary">
          {formatDate(ordered[ordered.length - 1].date)}
        </Text>
      </Row>
      <Row wrap>
        <Text type="small" themeColor="textSecondary">
          {records.length} comparable {activity.toLowerCase()} recordings
        </Text>
        {hasReference ? (
          <Badge
            comparison>{`Reference ${baseline.low}–${baseline.high}°`}</Badge>
        ) : (
          <Badge muted>No activity reference</Badge>
        )}
      </Row>
      <Sheet
        title="Movement range data"
        open={open}
        onClose={() => setOpen(false)}>
        <Badge muted>Demo · derived from joint angle</Badge>
        <Text type="small" themeColor="textSecondary">
          {joint.name} · {activity}. Only recordings with at least 80% valid
          coverage are included. No learned running/walking reference is available;
          landing references are kept separate.
        </Text>
        {ordered.map((session) => (
          <Row key={session.id}>
            <Text type="small">{formatDate(session.date)}</Text>
            <Text type="smallBold">
              {rom(joint, session)}° · {session.coverage}% coverage
            </Text>
          </Row>
        ))}
      </Sheet>
    </Animated.View>
  );
  return Platform.OS === 'web'
    ? createElement('div', { className: 'kintra-chart-transition' }, chart)
    : chart;
}
