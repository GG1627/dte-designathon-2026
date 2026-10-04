import './onboarding-storage';
import { FEEDBACK_VERSION, type BendSet } from '@/data/knee-feedback';

const key = 'kintra.simulated-knee-bends.v1';
export async function loadBendSets(): Promise<{ sets: BendSet[]; error: string | null }> {
  try {
    const stored = JSON.parse(globalThis.localStorage.getItem(key) ?? '[]');
    if (!Array.isArray(stored) || stored.some((s) => !s || typeof s.id !== 'string' ||
        !s.analysis || s.analysis.version !== FEEDBACK_VERSION || !Array.isArray(s.analysis.reps) ||
        !s.goal || !s.checkIn || !['slow', 'repeated', 'standing', 'changing'].includes(s.preset) ||
        !['unknown', 'planned', 'changed'].includes(s.checkIn.setup) ||
        !['unknown', 'easy', 'moderate', 'hard'].includes(s.checkIn.effort) ||
        !['observe', 'depth', 'pace'].includes(s.goal.kind) ||
        (s.goal.kind !== 'observe' && !(Number.isFinite(s.goal.target) && s.goal.target > 0)) ||
        !['ready', 'partial', 'insufficient', 'unsupported'].includes(s.analysis.status) ||
        !['simulated', 'hardware', 'mixed'].includes(s.analysis.source) ||
        !Array.isArray(s.analysis.reasons) || !s.analysis.reasons.every((reason: unknown) => typeof reason === 'string') ||
        !['sampleCount', 'invalidSamples', 'interruptions', 'durationS'].every((field) => Number.isFinite(s.analysis[field])) ||
        !s.analysis.reps.every((r: Record<string, unknown>) => r &&
          ['number', 'startMs', 'endMs', 'minimumDeg', 'peakDeg', 'rangeDeg', 'durationS', 'timeToPeakS',
            'peakVelocityDegS', 'peakAccelerationDegS2'].every((field) => Number.isFinite(r[field]))) ||
        !['medianRangeDeg', 'medianPeakDeg', 'medianDurationS', 'rangeSpreadDeg', 'durationSpreadS',
          'firstHalfRangeDeg', 'secondHalfRangeDeg'].every((field) => s.analysis[field] === null || Number.isFinite(s.analysis[field])) ||
        (s.analysis.status === 'ready' && (!s.analysis.reps.length || s.analysis.medianRangeDeg === null ||
          s.analysis.medianPeakDeg === null || s.analysis.medianDurationS === null)))) throw new Error('Invalid history');
    return { sets: stored.slice(0, 30), error: null };
  } catch {
    return { sets: [], error: 'Saved sets could not be loaded. You can still review a new set.' };
  }
}
export function saveBendSets(sets: BendSet[]): string | null {
  try {
    globalThis.localStorage.setItem(key, JSON.stringify(sets.slice(0, 30)));
    return null;
  } catch {
    return 'This set is available for this visit, but could not be saved on this device.';
  }
}
