import { Host, Picker, TextInput } from '@expo/ui';
import { useIsFocused } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { AppState, Pressable, StyleSheet, View } from 'react-native';

import { LiveKneeDiagram } from '@/components/live-knee-diagram';
import { BendSetFeedback } from '@/components/bend-set-feedback';
import { Action, Badge, Divider, PageIntro, Panel, Row, Screen, Section, Sheet } from '@/components/monitoring-ui';
import { ThemedText as Text } from '@/components/themed-text';
import { Palette as c, Spacing as s } from '@/constants/theme';
import {
  movementPresets,
  SAMPLE_INTERVAL_MS,
  SIMULATION_RATE_HZ,
  simulateSample,
  type MovementPreset,
  type LiveSample,
  type SegmentReading,
  type Vector3,
} from '@/data/live-simulation';
import { analyzeBends, type BendGoal, type BendSet } from '@/data/knee-feedback';
import { loadBendSets, saveBendSets } from '@/utils/bend-set-storage';

const MAX_SET_SAMPLES = 6000;

export default function LiveScreen() {
  const [preset, setPreset] = useState<MovementPreset>('slow');
  const [playing, setPlaying] = useState(false);
  const [sample, setSample] = useState(() => simulateSample('slow', 0));
  const [zero, setZero] = useState(0);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [recording, setRecording] = useState(false);
  const [finished, setFinished] = useState<BendSet | null>(null);
  const [history, setHistory] = useState<BendSet[]>([]);
  const [saved, setSaved] = useState(false);
  const [storageError, setStorageError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [goalKind, setGoalKind] = useState<BendGoal['kind']>('observe');
  const [targetText, setTargetText] = useState('');
  const captured = useRef<LiveSample[]>([]);
  const captureGoal = useRef<BendGoal>({ kind: 'observe', target: null });
  const [active, setActive] = useState(AppState.currentState === 'active');
  const focused = useIsFocused();
  const running = playing && focused && active;
  const kneeAngle = sample.shank.angleDeg - sample.thigh.angleDeg - zero;

  const finishSet = useCallback(() => {
    setPlaying(false);
    setRecording(false);
    setFinished({ id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      createdAt: new Date().toISOString(), preset, goal: captureGoal.current,
      checkIn: { setup: 'unknown', effort: 'unknown' }, analysis: analyzeBends(captured.current) });
  }, [preset]);

  useEffect(() => {
    let cancelled = false;
    void loadBendSets().then((stored) => {
      if (!cancelled) {
        setHistory(stored.sets);
        setStorageError(stored.error);
      }
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const listener = AppState.addEventListener('change', (state) => setActive(state === 'active'));
    return () => listener.remove();
  }, []);

  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => {
      setSample((previous) => simulateSample(preset, previous.sequence + 1));
    }, SAMPLE_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [running, preset]);

  useEffect(() => {
    if (!recording || captured.current.at(-1)?.sequence === sample.sequence) return;
    captured.current.push(sample);
    if (captured.current.length >= MAX_SET_SAMPLES) {
      finishSet();
      setNotice('The five-minute demo limit was reached. Your set is ready to review.');
    }
  }, [recording, sample, finishSet]);

  function reset(nextPreset: MovementPreset = preset) {
    setPlaying(false);
    setPreset(nextPreset);
    setSample(simulateSample(nextPreset, 0));
    setZero(0);
    setNotice(null);
  }

  function startSet() {
    const target = goalKind === 'observe' ? null : Number(targetText);
    if (goalKind !== 'observe' && (!targetText.trim() || !Number.isFinite(target) || target! <= 0 ||
        (goalKind === 'depth' && target! > 180))) {
      setNotice('Enter a positive target. Bend-depth targets must be 180° or less.');
      return;
    }
    reset();
    captured.current = [simulateSample(preset, 0)];
    captureGoal.current = { kind: goalKind, target };
    setFinished(null);
    setSaved(false);
    setRecording(true);
    setPlaying(true);
  }

  function saveSet() {
    if (!finished || saved) return;
    const next = [finished, ...history.filter((item) => item.id !== finished.id)].slice(0, 30);
    const error = saveBendSets(next);
    setStorageError(error);
    // Failed persistence stays reviewable for this visit, without claiming saved.
    setSaved(error === null);
    if (!error) setHistory(next);
  }

  return (
    <>
    <Screen>
      <PageIntro title="Live movement" />
      <Row wrap>
        <Badge>Simulated data</Badge>
        <Text type="small" themeColor="textSecondary">{finished ? 'Set complete' : recording ? running ? 'Recording set' : 'Set paused' : running ? 'Preview playing' : 'Preview paused'}</Text>
      </Row>
      {notice && <Text type="small" style={{ color: c.warning }}>{notice}</Text>}
      {finished ? <BendSetFeedback set={finished} history={history} saved={saved} storageError={storageError}
        onCheckIn={(checkIn) => setFinished({ ...finished, checkIn })} onSave={saveSet}
        onNewSet={() => { setFinished(null); reset(); }} /> : <>
      <View style={{ gap: s.two }}>
        <Text type="label" themeColor="textSecondary">Movement</Text>
        <Host matchContents colorScheme="dark" seedColor={c.accent}>
          <Picker selectedValue={preset} enabled={!recording} onValueChange={(value: MovementPreset) => reset(value)}
            testID="movement-preset">
            {movementPresets.map((movement) => (
              <Picker.Item key={movement.id} label={movement.label} value={movement.id} />
            ))}
          </Picker>
        </Host>
      </View>
      {!recording && <Panel>
        <Text type="smallBold">Set focus</Text>
        <Host matchContents colorScheme="dark" seedColor={c.accent}>
          <Picker selectedValue={goalKind} onValueChange={(kind: BendGoal['kind']) => { setGoalKind(kind); setTargetText(''); }} testID="set-focus">
            <Picker.Item label="Observe my movement" value="observe" />
            <Picker.Item label="My chosen bend depth" value="depth" />
            <Picker.Item label="My chosen rep pace" value="pace" />
          </Picker>
        </Host>
        {goalKind !== 'observe' && <>
          <Text type="small">{goalKind === 'depth' ? 'Your target at the deepest bend (degrees)' : 'Your target duration per rep (seconds)'}</Text>
          <Host matchContents colorScheme="dark" seedColor={c.accent}>
            <TextInput key={goalKind} onChangeText={setTargetText} keyboardType="decimal-pad"
              placeholder={goalKind === 'depth' ? 'Enter degrees' : 'Enter seconds'} textStyle={{ color: c.text }} testID="set-target" />
          </Host>
          <Text type="small" themeColor="textSecondary">Use a target from your exercise plan.</Text>
        </>}
        <Action primary onPress={startSet}>Start set</Action>
      </Panel>}
      <Panel>
        <Row wrap>
          <Text type="label" themeColor="textSecondary">Knee flexion</Text>
          <Text type="small" themeColor="textSecondary">Simulated angle</Text>
        </Row>
        <Pressable accessibilityRole="button" accessibilityLabel="Explain the current knee angle" onPress={() => setDetailsOpen(true)}>
          <Text type="metric" accessibilityLabel={`Knee flexion ${kneeAngle.toFixed(1)} degrees`}
            style={{ color: c.accent }} testID="knee-angle">{kneeAngle.toFixed(1)}°</Text>
          <Text type="small" style={{ color: c.accent }}>Reading details ↗</Text>
        </Pressable>
        <Row wrap>
          <Action primary onPress={() => setPlaying((value) => !value)}>{playing ? 'Pause' : 'Play'}</Action>
          {recording ? <Action primary onPress={finishSet}>Finish set</Action> : <>
            <Action onPress={() => setZero(sample.shank.angleDeg - sample.thigh.angleDeg)}>Zero knee</Action>
            <Action onPress={() => reset()}>Reset</Action>
          </>}
        </Row>
        <LiveKneeDiagram thighAngle={sample.thigh.angleDeg} shankAngle={sample.shank.angleDeg} />
        <Text type="small" themeColor="textSecondary">
          {recording ? `${(sample.timestampMs / 1000).toFixed(1)} s captured · finish after complete bends` : 'Preview a movement or start a set for feedback.'}
        </Text>
      </Panel>
      </>}
      {!recording && history.length > 0 && <Section title="Saved knee-bend sets">
        {history.slice(0, 5).map((item) => <Pressable key={item.id} accessibilityRole="button"
          accessibilityLabel={`Review saved set with ${item.analysis.reps.length} bends`}
          onPress={() => { setPlaying(false); setFinished(item); setSaved(true); }}
          style={{ minHeight: 70, paddingVertical: s.two, gap: s.one }}>
          <Text type="smallBold">{movementPresets.find((p) => p.id === item.preset)?.label} · {item.analysis.reps.length} bends ↗</Text>
          <Text type="small" themeColor="textSecondary">{new Date(item.createdAt).toLocaleString()} · Simulated</Text>
        </Pressable>)}
      </Section>}
    </Screen>
    <Sheet title="Knee angle details" open={detailsOpen} onClose={() => setDetailsOpen(false)}>
      <Badge>Simulated readings</Badge>
      <Text>The displayed knee angle is shank angle minus thigh angle, minus your display offset. It describes one instant; movement range describes a complete bend.</Text>
      <View style={styles.metrics}>
        <Reading label="Thigh angle" value={`${sample.thigh.angleDeg.toFixed(1)}°`} color={c.comparison} />
        <Reading label="Shank angle" value={`${sample.shank.angleDeg.toFixed(1)}°`} color={c.accent} />
      </View>
      <Text type="small">Display offset: {zero.toFixed(1)}°. Zeroing changes the display only; set analysis uses the original segment angles.</Text>
      <View style={styles.metrics}>
        <Reading label="Simulation rate" value={`${SIMULATION_RATE_HZ} Hz`} />
        <Reading label="Playback time" value={`${(sample.timestampMs / 1000).toFixed(1)} s`} />
      </View>
            <View style={{ gap: s.three, paddingTop: s.three }}>
              <Text type="small" themeColor="textSecondary">Idealized gravity and rotation · X-axis flexion</Text>
              <RawSensor name="Thigh" reading={sample.thigh} />
              <Divider />
              <RawSensor name="Shank" reading={sample.shank} />
              <Text type="code" themeColor="textSecondary">
                Sample {sample.sequence} · {sample.timestampMs.toFixed(0)} ms
              </Text>
            </View>
      </Sheet>
    </>
  );
}

function Reading({ label, value, color = c.text }: { label: string; value: string; color?: string }) {
  return (
    <View style={{ flex: 1, minWidth: 100, gap: s.one }}>
      <Text type="label" themeColor="textSecondary">{label}</Text>
      <Text type="subtitle" style={{ color }}>{value}</Text>
    </View>
  );
}

function vectorText(vector: Vector3, scale = 1) {
  return [vector.x, vector.y, vector.z].map((value) => (value * scale).toFixed(3)).join(', ');
}

function RawSensor({ name, reading }: { name: string; reading: SegmentReading }) {
  return (
    <View style={{ gap: s.two }}>
      <Row wrap>
        <Text type="smallBold">{name}</Text>
        <Badge muted>Simulated</Badge>
      </Row>
      <Text type="label" themeColor="textSecondary">X, Y, Z</Text>
      <Text type="code">A: {vectorText(reading.accelMS2, 1 / 9.80665)} g</Text>
      <Text type="code">G: {vectorText(reading.gyroRadS, 180 / Math.PI)} °/s</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  metrics: { flexDirection: 'row', flexWrap: 'wrap', gap: s.three },
});
