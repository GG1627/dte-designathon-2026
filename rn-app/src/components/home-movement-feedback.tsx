import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, View } from 'react-native';
import Svg, { Circle, Line, Path, Rect } from 'react-native-svg';

import { Action, Badge, Divider, Panel, Row, Section, Sheet } from '@/components/monitoring-ui';
import { ThemedText as Text } from '@/components/themed-text';
import { Palette as c, Spacing as s } from '@/constants/theme';
import { homeBendFeedback, homeBendHistory, homeBendSet } from '@/data/home-bend-demo';

export function HomeMovementFeedback() {
  const [open, setOpen] = useState(false);
  const [intent, setIntent] = useState<'planned' | 'unexpected' | null>(null);
  const [tired, setTired] = useState(false);
  const a = homeBendSet.analysis;
  const early = a.firstHalfRangeDeg!;
  const late = a.secondHalfRangeDeg!;
  const difference = early - late;
  const nextStep = intent === 'planned'
    ? 'Keep following your planned variation. We’ll treat this change as intentional.'
    : intent === 'unexpected'
      ? tired ? 'You reported feeling tired. Take a break and return to comfortable movement when you feel ready.'
        : 'Check that your sensors stayed in place, then repeat a few comfortable bends with the same setup.'
      : 'Confirm whether this was planned before changing your next set.';

  return <>
    <Section title="Your movement today">
      <Row wrap><Text type="small" themeColor="textSecondary">Knee bends · {a.reps.length} complete reps</Text><Badge muted>Simulated</Badge></Row>
      <Panel>
        <Pressable accessibilityRole="button" accessibilityLabel={`Your bends became shallower near the end. Early ${early.toFixed(0)} degrees, late ${late.toFixed(0)} degrees, ${difference.toFixed(0)} degrees less. Show evidence.`}
          onPress={() => setOpen(true)} style={({ pressed }) => ({ gap: s.two, opacity: pressed ? 0.65 : 1 })}>
          <Text type="subtitle">Your bends got shallower near the end</Text>
          <View style={{ width: '100%', maxWidth: 320, alignSelf: 'center', gap: s.two }}>
          <BendComparison early={early} late={late} />
          <Row>
            <View style={{ flex: 1, alignItems: 'center', gap: s.one }}>
              <Text type="smallBold" style={{ color: c.comparison }}>Early · {early.toFixed(0)}°</Text>
              <Text type="small" themeColor="textSecondary">First three bends</Text>
            </View>
            <View style={{ flex: 1, alignItems: 'center', gap: s.one }}>
              <Text type="smallBold" style={{ color: c.accent }}>Late · {late.toFixed(0)}°</Text>
              <Text type="small" themeColor="textSecondary">Last three bends</Text>
            </View>
          </Row>
          <RepMarkers ranges={a.reps.map(rep => rep.rangeDeg)} />
          </View>
          <Text type="smallBold" style={{ color: c.accent }}>{difference.toFixed(0)}° less movement · See evidence ↗</Text>
        </Pressable>
      </Panel>
      <View style={{ gap: s.two }}>
        <Text type="smallBold">Was this intentional?</Text>
        <View accessibilityRole="radiogroup" accessibilityLabel="Was this intentional?" style={{ flexDirection: 'row', flexWrap: 'wrap', gap: s.two }}>
          {([{ value: 'planned', label: 'Yes, planned' }, { value: 'unexpected', label: 'No, unexpected' }] as const).map(answer =>
            <Pressable key={answer.value} accessibilityRole="radio" aria-checked={intent === answer.value}
              onPress={() => { setIntent(answer.value); setTired(false); }}
              style={({ pressed }) => ({ flex: 1, minWidth: 120, minHeight: 48, padding: s.two,
                borderRadius: 12, borderWidth: 1, borderColor: intent === answer.value ? c.accent : c.border,
                backgroundColor: intent === answer.value ? c.accentMuted : c.backgroundElement,
                alignItems: 'center', justifyContent: 'center', opacity: pressed ? 0.65 : 1 })}>
              <Text type="smallBold">{answer.label}</Text>
            </Pressable>)}
        </View>
      </View>
      {intent === 'unexpected' && <Action onPress={() => setTired(value => !value)}>
        {tired ? 'Clear tired check-in' : 'I’m feeling tired'}
      </Action>}
      <View style={{ gap: s.two }} accessibilityLiveRegion="polite">
        <Text type="label" themeColor="textSecondary">{intent ? 'Next step' : 'Your context matters'}</Text>
        <Text>{nextStep}</Text>
        {intent === 'unexpected' && !tired
          ? <Action href="/live">Try a new set</Action>
          : <Action onPress={() => setOpen(true)}>Review movement details</Action>}
      </View>
    </Section>
    <Sheet title="Behind your movement reading" open={open} onClose={() => setOpen(false)} fullHeight>
      <Badge>Simulated example set</Badge>
      <Text>{homeBendFeedback.observation}</Text>
      <Text>Each bend’s range is its deepest minus its straightest angle. The first three ranges are {early.toFixed(0)}° each; the last three are {late.toFixed(0)}° each. Their group medians differ by {difference.toFixed(0)}°.</Text>
      <Text>The leg drawings show a representative bend from each group. The faded blue outline behind the later bend shows the earlier position. These are schematic comparisons, not anatomical images.</Text>
      <Text>Recent reference: {homeBendFeedback.referenceRangeDeg!.toFixed(0)}°, from earlier matching set medians of {homeBendHistory.map(item => `${item.analysis.medianRangeDeg!.toFixed(0)}°`).join(', ')}. The main card compares early and late bends in this set, rather than treating that reference as a target.</Text>
      <Text type="small" themeColor="textSecondary">Setup does not create a real personal baseline. This scripted example does not establish fatigue, injury, or the cause of the change.</Text>
      <Text type="small">Your check-in: {intent === 'planned' ? 'intentional change' : intent === 'unexpected' ? 'unexpected change' : 'not answered'}{tired ? ' · feeling tired (self-reported)' : ''}. Your answer changes the next step, not the recorded measurements.</Text>
      <Divider />
      <Text type="smallBold">Complete bends · {a.reps.length}</Text>
      <Text type="small">Typical range · {a.medianRangeDeg!.toFixed(1)}°{ '\n' }Typical rep · {a.medianDurationS!.toFixed(1)} s{ '\n' }Range variation · {a.rangeSpreadDeg!.toFixed(1)}°{ '\n' }Recording · {a.sampleCount} simulated readings, no continuity breaks</Text>
      {a.reps.map(rep => <View key={rep.number} style={{ gap: s.one }}>
        <Text type="smallBold">Rep {rep.number} · {rep.rangeDeg.toFixed(1)}° range</Text>
        <Text type="code">{rep.durationS.toFixed(2)} s · peak speed {rep.peakVelocityDegS.toFixed(1)} °/s{ '\n' }Peak acceleration {rep.peakAccelerationDegS2.toFixed(1)} °/s²</Text>
      </View>)}
      <Action onPress={() => { setOpen(false); router.push('/live'); }}>Open Live movement</Action>
    </Sheet>
  </>;
}

function BendComparison({ early, late }: { early: number; late: number }) {
  const leg = (x: number, degrees: number) => {
    const angle = degrees * Math.PI / 180;
    return `M ${x} 17 L ${x} 66 L ${x + 54 * Math.sin(angle)} ${66 + 54 * Math.cos(angle)}`;
  };
  return <View accessible accessibilityRole="image"
    accessibilityLabel={`Early bend ${early.toFixed(0)} degrees, later bend ${late.toFixed(0)} degrees. Later bends are shallower.`}>
    <Svg width="100%" height={102} viewBox="0 0 320 114" aria-hidden>
      <Line x1={54} y1={17} x2={54} y2={110} stroke={c.border} strokeDasharray="3 5" />
      <Line x1={214} y1={17} x2={214} y2={110} stroke={c.border} strokeDasharray="3 5" />
      <Path d={leg(54, early)} stroke={c.comparison} strokeWidth={13} strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <Path d={leg(214, early)} stroke={c.comparison} strokeWidth={13} strokeLinecap="round" strokeLinejoin="round" fill="none" opacity={0.22} />
      <Path d={leg(214, late)} stroke={c.accent} strokeWidth={13} strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <Circle cx={54} cy={66} r={7} fill={c.backgroundElement} stroke={c.comparison} strokeWidth={3} />
      <Circle cx={214} cy={66} r={7} fill={c.backgroundElement} stroke={c.accent} strokeWidth={3} />
    </Svg>
  </View>;
}

function RepMarkers({ ranges }: { ranges: number[] }) {
  const max = Math.max(...ranges);
  return <View accessible accessibilityRole="image"
    accessibilityLabel={ranges.map((range, i) => `Bend ${i + 1}: ${range.toFixed(0)} degrees`).join('. ')}>
    <Svg width="100%" height={34} viewBox="0 0 280 34" aria-hidden>
      {ranges.map((range, i) => {
        const height = range / max * 26;
        return <Rect key={i} x={i * 46 + 3} y={30 - height} width={34} height={height}
          rx={4} fill={i < 3 ? c.comparison : c.accent} />;
      })}
    </Svg>
  </View>;
}
