import { Host, Picker } from '@expo/ui';
import { useState } from 'react';
import { Pressable, View } from 'react-native';
import Svg, { Line, Rect } from 'react-native-svg';

import { Action, Badge, Divider, Panel, Row, Section, Sheet } from '@/components/monitoring-ui';
import { ThemedText as Text } from '@/components/themed-text';
import { Palette as c, Spacing as s } from '@/constants/theme';
import { buildBendFeedback, MIN_REFERENCE_SETS, type BendSet, type SetCheckIn } from '@/data/knee-feedback';

type Detail = 'takeaway' | 'range' | 'pace' | 'variation' | 'reference' | 'quality';
const titles: Record<Detail, string> = {
  takeaway: 'Why this feedback?', range: 'Movement range', pace: 'Rep pace',
  variation: 'Repeatability', reference: 'Personal reference', quality: 'Recording quality',
};

export function BendSetFeedback({ set, history, saved, storageError, onCheckIn, onSave, onNewSet }: {
  set: BendSet; history: BendSet[]; saved: boolean; storageError: string | null;
  onCheckIn: (checkIn: SetCheckIn) => void; onSave: () => void; onNewSet: () => void;
}) {
  const [detail, setDetail] = useState<Detail>('takeaway');
  const [detailOpen, setDetailOpen] = useState(false);
  function showDetail(next: Detail) {
    setDetail(next);
    setDetailOpen(true);
  }
  const feedback = buildBendFeedback(set, history);
  const a = set.analysis;
  const trusted = a.status === 'ready';
  const show = (value: number | null, unit: string, precision = 0) => value === null ? '—' : `${value.toFixed(precision)}${unit}`;
  return <>
    <Section title="Your set">
      <Row wrap>
        <Badge>Simulated feedback</Badge>
        <Text type="small" themeColor="textSecondary">{a.reps.length} complete bends</Text>
      </Row>
      <Panel accent>
        <Pressable accessibilityRole="button" accessibilityLabel="Explain this feedback"
          onPress={() => showDetail('takeaway')} style={({ pressed }) => ({ gap: s.two, opacity: pressed ? 0.65 : 1 })}>
          <Text type="subtitle">{feedback.title}</Text>
          <Text type="small" themeColor="textSecondary">{feedback.observation}</Text>
          <Text type="smallBold" style={{ color: c.accent }}>See evidence ↗</Text>
        </Pressable>
        <Divider />
        <Text type="label" themeColor="textSecondary">Next step</Text>
        <Text>{feedback.nextStep}</Text>
      </Panel>
      {trusted && <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: s.three }}>
        <EvidenceCard label="Typical range" value={show(a.medianRangeDeg, '°')} onPress={() => showDetail('range')} />
        <EvidenceCard label="Typical rep" value={show(a.medianDurationS, ' s', 1)} onPress={() => showDetail('pace')} />
        <EvidenceCard label="Range variation" value={show(a.rangeSpreadDeg, '°')} onPress={() => showDetail('variation')} />
      </View>}
      {a.reps.length > 0 && <Panel>
        <Text type="smallBold">Movement range by rep</Text>
        <RepRangeChart ranges={a.reps.map((r) => r.rangeDeg)} />
        <Action onPress={() => showDetail('range')}>View each rep</Action>
      </Panel>}
      <Panel>
        <Text type="smallBold">How was the set?</Text>
        <Text type="small" themeColor="textSecondary">Your experience adds context to the movement readings.</Text>
        <Text type="label" themeColor="textSecondary">Exercise setup</Text>
        <Host matchContents colorScheme="dark" seedColor={c.accent}>
          <Picker selectedValue={set.checkIn.setup} enabled={!saved}
            onValueChange={(setup: SetCheckIn['setup']) => onCheckIn({ ...set.checkIn, setup })} testID="setup-check-in">
            <Picker.Item label="Not confirmed" value="unknown" />
            <Picker.Item label="Followed the planned setup" value="planned" />
            <Picker.Item label="Changed during this set" value="changed" />
          </Picker>
        </Host>
        <Text type="label" themeColor="textSecondary">Effort · optional</Text>
        <Host matchContents colorScheme="dark" seedColor={c.accent}>
          <Picker selectedValue={set.checkIn.effort} enabled={!saved}
            onValueChange={(effort: SetCheckIn['effort']) => onCheckIn({ ...set.checkIn, effort })} testID="effort-check-in">
            <Picker.Item label="Not recorded" value="unknown" />
            <Picker.Item label="Easy" value="easy" />
            <Picker.Item label="Moderate" value="moderate" />
            <Picker.Item label="Hard" value="hard" />
          </Picker>
        </Host>
      </Panel>
      <Pressable accessibilityRole="button" accessibilityLabel="Explain personal reference"
        onPress={() => showDetail('reference')} style={{ minHeight: 48, gap: s.one }}>
        <Text type="smallBold">{feedback.referenceRangeDeg === null ? 'Building comparable history' : 'Recent matching sets'} ↗</Text>
        <Text type="small" themeColor="textSecondary">
          {feedback.referenceRangeDeg === null
            ? a.reps.length < 3 ? 'Capture at least three complete bends for a set comparison.'
              : set.checkIn.setup !== 'planned' ? 'Confirm the planned setup to find matching sets.'
              : `${feedback.referenceCount} of ${MIN_REFERENCE_SETS} prior sets available for a demo comparison.`
            : `${feedback.referenceCount} prior sets · typical range ${feedback.referenceRangeDeg.toFixed(0)}°`}
        </Text>
      </Pressable>
      <Action onPress={() => showDetail('quality')}>Recording quality</Action>
      {storageError && <Text type="small" style={{ color: c.warning }}>{storageError}</Text>}
      <Row wrap>
        {!saved ? <Action primary onPress={onSave}>Save set</Action> : <Badge muted>Saved on this device</Badge>}
        <Action onPress={onNewSet}>New set</Action>
      </Row>
    </Section>
    <Sheet title={titles[detail]} open={detailOpen} onClose={() => setDetailOpen(false)}>
      <Badge>Simulated measurements</Badge>
      {detail === 'takeaway' && <>
        <Text>{feedback.observation}</Text>
        <Text type="small" themeColor="textSecondary">This is a descriptive rule based on complete bends. It does not identify fatigue, injury, or the cause of a change.</Text>
        {a.firstHalfRangeDeg !== null && <Text>First-half median range: {show(a.firstHalfRangeDeg, '°', 1)}. Last-half median range: {show(a.secondHalfRangeDeg, '°', 1)}.</Text>}
        {set.goal.kind !== 'observe' && <Text>Your chosen target: {set.goal.target} {set.goal.kind === 'depth' ? 'degrees at the deepest bend' : 'seconds per rep'}.</Text>}
        <Text type="small" themeColor="textSecondary">First/last-half comparisons require at least four bends. An odd middle bend is excluded. Differences are rounded to whole degrees for the headline, not judged against a validated significance threshold.</Text>
      </>}
      {detail === 'range' && <Text>Movement range is the deepest minus the straightest angle within each complete bend. Typical range is the median across bends; deepest bend and range are different measurements.</Text>}
      {detail === 'pace' && <Text>Rep duration runs from one return position to the next. It describes pace, not movement quality. Peak speed and acceleration are available below.</Text>}
      {detail === 'variation' && <>
        <Text>Range variation is the widest minus the narrowest complete bend. A smaller spread means the recorded ranges were closer together; it is not a technique score.</Text>
        <Text>Range spread: {show(a.rangeSpreadDeg, '°', 1)}. Rep-duration spread: {show(a.durationSpreadS, ' s', 2)}.</Text>
      </>}
      {detail === 'reference' && <>
        <Text>Only saved simulated sets with the same movement preset, chosen target, processing version, at least three complete bends, valid recording, and confirmed planned setup are compared.</Text>
        <Text>Reference: median of the session medians from up to five matching earlier sets. This set and later sets are excluded.</Text>
        <Text>Prior matching sets: {feedback.referenceCount}. Range reference: {show(feedback.referenceRangeDeg, '°', 1)}. Pace reference: {show(feedback.referenceDurationS, ' s', 2)}.</Text>
        <Text type="small" themeColor="textSecondary">Three prior sets is a prototype sufficiency rule. Your history describes previous movement, not ideal technique. Measurement-error thresholds are not established.</Text>
      </>}
      {detail === 'quality' && <>
        <Text>Status: {a.status}. {a.sampleCount} samples; {a.invalidSamples} invalid; {a.interruptions} continuity breaks.</Text>
        <Text>Complete-bend duration: {a.durationS.toFixed(1)} s. {a.reps.length} complete bends.</Text>
        {a.reasons.map((reason) => <Text key={reason}>{reason}</Text>)}
        <Text type="small" themeColor="textSecondary">The simulator is idealized gravity and X-axis rotation. Segmentation uses observed returns, a 6° amplitude gate and a 0.4 s minimum cycle. These are engineering gates, not recommended exercise limits. Partial edges and bends across missing readings are excluded.</Text>
        <Text type="code">{a.version} · source: {a.source}</Text>
      </>}
      {(detail === 'range' || detail === 'pace' || detail === 'variation') && a.reps.map((rep) => <View key={rep.number} style={{ gap: s.two }}>
        <Divider />
        <Text type="smallBold">Rep {rep.number}</Text>
        <Text type="small">Range {rep.rangeDeg.toFixed(1)}° · duration {rep.durationS.toFixed(2)} s</Text>
        <Text type="small" themeColor="textSecondary">Minimum {rep.minimumDeg.toFixed(1)}° · deepest {rep.peakDeg.toFixed(1)}° · time to peak {rep.timeToPeakS.toFixed(2)} s</Text>
        <Text type="code">Peak speed {rep.peakVelocityDegS.toFixed(1)} °/s{ '\n' }Peak acceleration {rep.peakAccelerationDegS2.toFixed(1)} °/s²</Text>
      </View>)}
    </Sheet>
  </>;
}

function EvidenceCard({ label, value, onPress }: { label: string; value: string; onPress: () => void }) {
  return <Pressable accessibilityRole="button" accessibilityLabel={`${label}: ${value}. Show details`}
    onPress={onPress} style={({ pressed }) => ({ flexGrow: 1, flexBasis: '40%', minHeight: 90,
      padding: s.three, borderRadius: 16, backgroundColor: c.backgroundElement, gap: s.two,
      opacity: pressed ? 0.65 : 1 })}>
    <Text type="small" themeColor="textSecondary">{label} ↗</Text>
    <Text type="subtitle">{value}</Text>
  </Pressable>;
}

function RepRangeChart({ ranges }: { ranges: number[] }) {
  const shown = ranges.slice(0, 12);
  const max = Math.max(10, ...shown);
  return <View style={{ gap: s.two }}>
    <Text type="small" themeColor="textSecondary">{ranges.length > 12 ? `First 12 of ${ranges.length} bends` : `${ranges.length} bends`} · 0–{Math.ceil(max)}°</Text>
    <View accessible accessibilityRole="image" accessibilityLabel={shown.map((value, i) => `Rep ${i + 1}: ${value.toFixed(0)} degrees`).join('. ')}>
      <Svg width="100%" height={130} viewBox="0 0 320 130" aria-hidden>
        <Line x1={0} y1={116} x2={320} y2={116} stroke={c.border} />
        {shown.map((value, i) => <Rect key={i} x={i * 320 / shown.length + 4}
          y={116 - value / max * 100} width={Math.max(2, 320 / shown.length - 8)}
          height={value / max * 100} rx={3} fill={c.accent} />)}
      </Svg>
    </View>
    <Row><Text type="small" themeColor="textSecondary">Rep 1</Text><Text type="small" themeColor="textSecondary">Rep {shown.length}</Text></Row>
  </View>;
}
