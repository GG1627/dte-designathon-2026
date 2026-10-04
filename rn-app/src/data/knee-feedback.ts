import type { LiveSample, MovementPreset } from './live-simulation';

export const FEEDBACK_VERSION = 'knee-bend-demo/1';
export const MIN_REFERENCE_SETS = 3;
export type BendGoal = { kind: 'observe' | 'depth' | 'pace'; target: number | null };
export type SetCheckIn = { effort: 'unknown' | 'easy' | 'moderate' | 'hard'; setup: 'unknown' | 'planned' | 'changed' };
type Point = { t: number; angle: number; velocity: number };
export type BendRep = {
  number: number; startMs: number; endMs: number; minimumDeg: number; peakDeg: number;
  rangeDeg: number; durationS: number; timeToPeakS: number;
  peakVelocityDegS: number; peakAccelerationDegS2: number;
};
export type BendAnalysis = {
  version: string; source: 'simulated' | 'hardware' | 'mixed';
  status: 'ready' | 'partial' | 'insufficient' | 'unsupported';
  sampleCount: number; invalidSamples: number; interruptions: number; durationS: number;
  reps: BendRep[]; reasons: string[];
  medianRangeDeg: number | null; medianPeakDeg: number | null; medianDurationS: number | null;
  rangeSpreadDeg: number | null; durationSpreadS: number | null;
  firstHalfRangeDeg: number | null; secondHalfRangeDeg: number | null;
};
export type BendSet = { id: string; createdAt: string; preset: MovementPreset; goal: BendGoal; checkIn: SetCheckIn; analysis: BendAnalysis };
export type BendFeedback = {
  title: string; observation: string; nextStep: string;
  referenceCount: number; referenceRangeDeg: number | null; referenceDurationS: number | null;
};

export function median(values: number[]): number | null {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function detectReps(points: Point[]): BendRep[] {
  const reps: BendRep[] = [];
  let start: number | null = null;
  let direction = 0;
  function complete(end: number) {
    if (start === null) return;
    const window = points.slice(start, end + 1);
    const angles = window.map((p) => p.angle);
    const minimumDeg = Math.min(...angles);
    const peakDeg = Math.max(...angles);
    const durationS = (points[end].t - points[start].t) / 1000;
    // Engineering segmentation gates for the simulator, not technique targets.
    if (peakDeg - minimumDeg < 6 || durationS < 0.4) return;
    const peakIndex = angles.indexOf(peakDeg);
    const acceleration = window.slice(1).map((p, i) =>
      Math.abs((p.velocity - window[i].velocity) / ((p.t - window[i].t) / 1000)));
    reps.push({ number: reps.length + 1, startMs: points[start].t, endMs: points[end].t,
      minimumDeg, peakDeg, rangeDeg: peakDeg - minimumDeg, durationS,
      timeToPeakS: (window[peakIndex].t - window[0].t) / 1000,
      peakVelocityDegS: Math.max(...window.map((p) => Math.abs(p.velocity))),
      peakAccelerationDegS2: Math.max(0, ...acceleration) });
  }
  for (let i = 1; i < points.length; i++) {
    const change = points[i].angle - points[i - 1].angle;
    if (Math.abs(change) < 1e-6) continue;
    const next = Math.sign(change);
    // A recording that starts mid-bend waits for the first observed trough.
    if (direction === 0 && next > 0 && Math.abs(points[0].angle) <= 0.5) start = 0;
    if (direction < 0 && next > 0) {
      complete(i - 1);
      start = i - 1;
    }
    direction = next;
  }
  // Accept a terminal return to the initial position; exclude incomplete edges.
  if (start !== null && direction < 0 &&
      Math.abs(points[points.length - 1].angle - points[start].angle) <= 0.05) {
    complete(points.length - 1);
  }
  return reps;
}

export function analyzeBends(samples: LiveSample[]): BendAnalysis {
  const sources = new Set(samples.map((s) => s.source));
  const source = sources.size > 1 ? 'mixed' : samples[0]?.source ?? 'simulated';
  const reps: BendRep[] = [];
  let segment: Point[] = [];
  let invalidSamples = 0;
  let interruptions = 0;
  let previous: LiveSample | null = null;
  function flush() {
    reps.push(...detectReps(segment));
    segment = [];
  }
  for (const sample of samples) {
    const valid = Number.isFinite(sample.timestampMs) && sample.timestampMs >= 0 &&
      Number.isInteger(sample.sequence) && sample.sequence >= 0 &&
      [sample.thigh, sample.shank].every((reading) => reading.valid === true &&
        [reading.angleDeg, reading.accelMS2.x, reading.accelMS2.y, reading.accelMS2.z,
          reading.gyroRadS.x, reading.gyroRadS.y, reading.gyroRadS.z].every(Number.isFinite));
    if (!valid) {
      invalidSamples++;
      flush();
      previous = null;
      continue;
    }
    if (previous && (sample.sequence !== previous.sequence + 1 ||
        sample.timestampMs <= previous.timestampMs || sample.timestampMs - previous.timestampMs > 100)) {
      interruptions++;
      flush();
    }
    segment.push({ t: sample.timestampMs, angle: sample.shank.angleDeg - sample.thigh.angleDeg,
      velocity: (sample.shank.gyroRadS.x - sample.thigh.gyroRadS.x) * 180 / Math.PI });
    previous = sample;
  }
  flush();
  reps.forEach((rep, i) => { rep.number = i + 1; });
  const ranges = reps.map((r) => r.rangeDeg);
  const durations = reps.map((r) => r.durationS);
  const half = Math.floor(reps.length / 2);
  const reasons: string[] = [];
  if (source !== 'simulated') reasons.push('Hardware angle estimation and calibration are not validated for this feedback protocol.');
  if (invalidSamples || interruptions) reasons.push('Some readings were invalid or interrupted. Bends crossing those breaks were excluded.');
  if (!reps.length) reasons.push('No complete knee bends were captured. Partial bends and movement below the demo segmentation gate are excluded.');
  return { version: FEEDBACK_VERSION, source,
    status: source !== 'simulated' ? 'unsupported' : invalidSamples || interruptions ? 'partial' : reps.length ? 'ready' : 'insufficient',
    sampleCount: samples.length, invalidSamples, interruptions,
    durationS: reps.reduce((total, rep) => total + rep.durationS, 0), reps, reasons,
    medianRangeDeg: median(ranges), medianPeakDeg: median(reps.map((r) => r.peakDeg)), medianDurationS: median(durations),
    rangeSpreadDeg: ranges.length >= 2 ? Math.max(...ranges) - Math.min(...ranges) : null,
    durationSpreadS: durations.length >= 2 ? Math.max(...durations) - Math.min(...durations) : null,
    firstHalfRangeDeg: reps.length >= 4 ? median(ranges.slice(0, half)) : null,
    secondHalfRangeDeg: reps.length >= 4 ? median(ranges.slice(reps.length - half)) : null };
}

export function buildBendFeedback(current: BendSet, history: BendSet[]): BendFeedback {
  const a = current.analysis;
  const comparable = history.filter((s) => a.status === 'ready' && a.reps.length >= 3 &&
    s.id !== current.id && s.createdAt < current.createdAt && s.preset === current.preset &&
    s.analysis.version === a.version && s.analysis.source === a.source && s.analysis.status === 'ready' &&
    s.analysis.reps.length >= 3 && s.goal.kind === current.goal.kind && s.goal.target === current.goal.target &&
    s.checkIn.setup === 'planned' && current.checkIn.setup === 'planned').slice(0, 5);
  const referenceCount = comparable.length;
  const referenceRangeDeg = referenceCount >= MIN_REFERENCE_SETS
    ? median(comparable.map((s) => s.analysis.medianRangeDeg!)) : null;
  const referenceDurationS = referenceCount >= MIN_REFERENCE_SETS
    ? median(comparable.map((s) => s.analysis.medianDurationS!)) : null;
  const reference = { referenceCount, referenceRangeDeg, referenceDurationS };
  if (a.status === 'unsupported') return { ...reference, title: 'Movement estimate needs validation',
    observation: a.reasons[0], nextStep: 'Use the sensor display for inspection. Validate calibration and angle estimation before using exercise feedback.' };
  if (a.status === 'partial') return { ...reference, title: 'Some movement was missed',
    observation: `${a.reps.length} complete bends remain after excluding interrupted readings.`,
    nextStep: 'Check sensor fit and recording continuity, then capture the same drill again.' };
  if (!a.reps.length) return { ...reference, title: 'Capture a complete bend',
    observation: 'This recording does not contain a complete bend-and-return cycle.',
    nextStep: 'Start a new set, complete a full bend and return, then finish the set.' };
  if (current.checkIn.setup === 'changed') return { ...reference, title: 'Review this set on its own',
    observation: `You recorded ${a.reps.length} bends and reported a change in exercise setup.`,
    nextStep: 'Keep this set separate from your usual drill. Record the planned setup for your next comparison.' };
  if (current.goal.kind !== 'observe' && current.goal.target !== null) {
    const depth = current.goal.kind === 'depth';
    const measured = depth ? a.medianPeakDeg! : a.medianDurationS!;
    return { ...reference, title: depth ? 'Review your chosen bend depth' : 'Review your chosen pace',
      observation: `Typical ${depth ? 'deepest bend' : 'rep duration'}: ${measured.toFixed(depth ? 0 : 1)}${depth ? '°' : ' s'}. Your target: ${current.goal.target}${depth ? '°' : ' s'}.`,
      nextStep: 'Review individual reps against the target you chose. Confirm that it still matches your exercise plan.' };
  }
  const change = a.firstHalfRangeDeg !== null && a.secondHalfRangeDeg !== null
    ? Math.round(a.secondHalfRangeDeg - a.firstHalfRangeDeg) : 0;
  if (change !== 0) return { ...reference, title: change < 0 ? 'Later bends covered less movement' : 'Later bends covered more movement',
    observation: `Typical range changed from ${a.firstHalfRangeDeg!.toFixed(0)}° in the first half to ${a.secondHalfRangeDeg!.toFixed(0)}° in the second half.`,
    nextStep: 'Were the later bends intentionally different? Repeat the same drill and check whether the pattern repeats.' };
  if (referenceRangeDeg !== null && a.reps.length >= 3) return { ...reference, title: 'Compare with your recent sets',
    observation: `Typical range: ${a.medianRangeDeg!.toFixed(0)}°. Your recent reference: ${referenceRangeDeg.toFixed(0)}° across ${referenceCount} matching sets.`,
    nextStep: 'Check whether the exercise and effort were comparable. A numerical difference alone does not establish its cause.' };
  return { ...reference, title: 'Your set is ready to review',
    observation: `${a.reps.length} complete bends, with a typical movement range of ${a.medianRangeDeg!.toFixed(0)}°.`,
    nextStep: a.reps.length < 3 ? 'Capture more complete bends to review repeatability.' :
      current.checkIn.setup === 'unknown' ? 'Confirm whether the set followed the planned setup before comparing with history.' :
        'Repeat the same drill to build a reference from comparable sets.' };
}
