import { useState } from 'react';
import { Pressable, View } from 'react-native';
import { Action, Badge, Panel, Row } from '@/components/monitoring-ui';
import { ThemedText as Text } from '@/components/themed-text';
import { Palette as c, Radius, Spacing as s } from '@/constants/theme';
import { activities, movementLabels, sensorLabels, type Activity, type Movement, type SetupData } from '@/data/setup';

export function SetupButton({ children, onPress, disabled = false }: { children: string; onPress: () => void; disabled?: boolean }) {
  return <Pressable accessibilityRole="button" accessibilityState={{ disabled }} disabled={disabled} onPress={onPress}
    style={({ pressed }) => ({ minHeight: 52, padding: s.three, borderRadius: Radius.medium, alignItems: 'center', justifyContent: 'center', backgroundColor: c.accent, opacity: disabled ? 0.35 : pressed ? 0.65 : 1 })}>
    <Text type="smallBold" style={{ color: c.background }}>{children}</Text>
  </Pressable>;
}
export function TaskProgress({ value, target, label, counter }: { value: number; target: number; label: string; counter?: string }) {
  return <Panel>
    <Text type="small" themeColor="textSecondary">{label}</Text>
    <Text type="metric" style={{ color: c.accent }}>{counter ?? `${value} / ${target}`}</Text>
    <View accessibilityRole="progressbar" accessibilityLabel={label} accessibilityValue={{ min: 0, max: target, now: value }} style={{ height: 6, borderRadius: 3, backgroundColor: c.backgroundSelected, overflow: 'hidden' }}>
      <View style={{ height: 6, width: `${Math.min(100, value / target * 100)}%`, backgroundColor: c.accent }} />
    </View>
    {value >= target ? <Badge>Complete ?</Badge> : null}
  </Panel>;
}
export function SensorStatusList({ sensors, quality = false }: { sensors: SetupData['sensors']; quality?: boolean }) {
  return <Panel>{Object.entries(sensorLabels).map(([key, label]) => {
    const status = sensors[key as keyof typeof sensors];
    return <Row key={key} wrap><Text type="smallBold">{label}</Text><Text type="small" style={{ color: status === 'connected' ? c.text : c.warning }}>{status === 'connected' ? quality ? 'Signal ready ?' : 'Connected ?' : status === 'disconnected' ? 'Disconnected — check connection' : 'Check sensor fit'}</Text></Row>;
  })}</Panel>;
}
export function MovementConfirmation({ predicted, confirmed, options, onConfirm }: { predicted: Movement | null; confirmed: Movement | null; options: Movement[]; onConfirm: (movement: Movement) => void }) {
  const [changing, setChanging] = useState(false);
  return <Panel>
    <Text type="small" themeColor="textSecondary">{confirmed ? 'Athlete confirmed' : 'Movement detected'}</Text>
    <Text type="subtitle">{confirmed ? movementLabels[confirmed] : predicted ? movementLabels[predicted] : 'We couldn’t verify this movement.'}</Text>
    {!predicted && !confirmed ? <Text type="small" themeColor="textSecondary">Check sensor fit and try again, or choose your movement below.</Text> : null}
    {changing || !predicted ? options.map(option => <Action key={option} onPress={() => { onConfirm(option); setChanging(false); }}>{movementLabels[option]}</Action>) : <>
      {!confirmed ? <Text>Was that correct?</Text> : null}
      <Row>{!confirmed && predicted ? <Action primary onPress={() => onConfirm(predicted)}>Yes</Action> : null}<Action onPress={() => setChanging(true)}>Change</Action></Row>
    </>}
  </Panel>;
}
export function ActivitySelection({ selected, onSelect }: { selected: Activity | null; onSelect: (activity: Activity) => void }) {
  return <View style={{ gap: s.two }}>{Object.entries(activities).map(([key, label]) => <Pressable key={key} accessibilityRole="radio" accessibilityState={{ selected: key === selected }} onPress={() => onSelect(key as Activity)}
    style={({ pressed }) => ({ minHeight: 52, padding: s.three, borderRadius: Radius.medium, borderWidth: 1, borderColor: key === selected ? c.accent : c.border, backgroundColor: key === selected ? c.accentMuted : c.backgroundElement, opacity: pressed ? 0.65 : 1 })}>
    <Row><Text type="smallBold">{label}</Text>{key === selected ? <Text style={{ color: c.accent }}>?</Text> : null}</Row>
  </Pressable>)}</View>;
}
export function PersonalReference({ setup }: { setup: SetupData }) {
  const movements = [...new Set([setup.walking_calibration, setup.squat_check, setup.landing_check].filter(task => task.status === 'complete' && task.confirmed_movement && task.confirmed_movement !== 'other').map(task => task.confirmed_movement!))];
  return <Panel><Row wrap><Text type="smallBold">Personal reference</Text><Badge muted>{setup.personal_reference.status === 'learning' ? 'Learning…' : 'Provisional'}</Badge></Row>
    {setup.confirmed_activity ? movements.map(movement => <Text key={movement} type="small" themeColor="textSecondary">{activities[setup.confirmed_activity!]} • {movementLabels[movement]}</Text>) : null}
    <Text type="small" themeColor="textSecondary">Your personal movement reference becomes more useful with more confirmed sessions.</Text>
  </Panel>;
}
export function SetupSummary({ setup }: { setup: SetupData }) {
  return <View style={{ gap: s.three }}><Panel>{['Sensor fit', 'Walking calibration', 'Movement recognition', 'Smart insoles'].map(label => <Row key={label}><Text type="smallBold">{label}</Text><Text style={{ color: c.accent }}>?</Text></Row>)}
    {setup.landing_check.status === 'skipped' ? <Text type="small" themeColor="textSecondary">Jump / landing check skipped. You can try it another time.</Text> : null}
  </Panel><PersonalReference setup={setup} /></View>;
}
