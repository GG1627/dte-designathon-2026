import type { BendSet } from './shared';
const KEY = 'kintra.web.bend-sets.v1';
export function loadSets(): { sets: BendSet[]; error: string | null } {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(KEY) ?? '[]');
    if (!Array.isArray(value) || value.length > 30 || !value.every(isSet)) throw new Error('Invalid saved history');
    return { sets: value, error: null };
  } catch { return { sets: [], error: 'Saved history is unavailable in this browser. New sets can still be reviewed and exported.' }; }
}
function isSet(value: unknown): value is BendSet {
  if (!value || typeof value !== 'object') return false;
  const s = value as BendSet;
  return typeof s.id === 'string' && typeof s.createdAt === 'string' && Number.isFinite(Date.parse(s.createdAt)) &&
    ['slow', 'repeated', 'standing', 'changing'].includes(s.preset) && !!s.goal &&
    ['observe', 'depth', 'pace'].includes(s.goal.kind) && (s.goal.target === null || Number.isFinite(s.goal.target)) &&
    !!s.checkIn && ['unknown', 'planned', 'changed'].includes(s.checkIn.setup) &&
    ['unknown', 'easy', 'moderate', 'hard'].includes(s.checkIn.effort) && !!s.analysis &&
    s.analysis.source === 'simulated' && ['ready', 'partial', 'insufficient'].includes(s.analysis.status) &&
    typeof s.analysis.version === 'string' && Array.isArray(s.analysis.reasons) && s.analysis.reasons.every((r) => typeof r === 'string') &&
    ['sampleCount', 'invalidSamples', 'interruptions', 'durationS'].every((k) => Number.isFinite(s.analysis[k as keyof typeof s.analysis])) &&
    ['medianRangeDeg', 'medianPeakDeg', 'medianDurationS', 'rangeSpreadDeg', 'durationSpreadS', 'firstHalfRangeDeg', 'secondHalfRangeDeg'].every((k) => s.analysis[k as keyof typeof s.analysis] === null || Number.isFinite(s.analysis[k as keyof typeof s.analysis])) &&
    Array.isArray(s.analysis.reps) && s.analysis.reps.length <= 6000 && s.analysis.reps.every((r) =>
      !!r && ['number', 'startMs', 'endMs', 'minimumDeg', 'peakDeg', 'rangeDeg', 'durationS', 'timeToPeakS', 'peakVelocityDegS', 'peakAccelerationDegS2'].every((k) => Number.isFinite(r[k as keyof typeof r])));
}
export function saveSets(sets: BendSet[]) {
  try { localStorage.setItem(KEY, JSON.stringify(sets.slice(0, 30))); return null; }
  catch { return 'Could not save on this browser. Your set remains reviewable; export it before leaving.'; }
}
export function downloadJson(value: unknown, name: string) {
  // JSON has no NaN: encode unavailable SI fields explicitly as null.
  const blob = new Blob([JSON.stringify(value, (_key, v) => typeof v === 'number' && !Number.isFinite(v) ? null : v, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a'); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
