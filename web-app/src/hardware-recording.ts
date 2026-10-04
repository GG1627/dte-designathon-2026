import { analyzeBends, type BendAnalysis } from '../../rn-app/src/data/knee-feedback.ts';
import type { LiveSample } from '../../rn-app/src/data/live-simulation.ts';
import type { SerialRecord } from './serial.ts';

export type HardwareInspection = {
  analysis: BendAnalysis | null;
  packetErrors: number;
  interruptionRecords: number;
  excludedBoundarySequences: number[];
};
export type SignalPoint = { index: number; angle: number };

export function relativeAngle(sample: LiveSample): number | null {
  const angle = sample.shank.angleDeg - sample.thigh.angleDeg;
  return sample.thigh.valid && sample.shank.valid && Number.isFinite(angle) ? angle : null;
}

/** Inspection only: keep hardware provenance and the shared engine's unsupported status. */
export function inspectHardwareRecording(records: SerialRecord[]): HardwareInspection {
  const inputs: LiveSample[] = [];
  const excludedBoundarySequences: number[] = [];
  let boundary = false, packetErrors = 0, interruptionRecords = 0;
  for (const record of records) {
    if (record.kind === 'error' || record.kind === 'interruption') {
      boundary = true;
      if (record.kind === 'error') packetErrors++;
      else interruptionRecords++;
    }
    if (!record.sample) continue;
    const sample = record.sample;
    // The wire has no packet sequence. Exclude the first reading after a known
    // decoder/filter break from segmentation, without changing the raw record.
    if (boundary) {
      inputs.push({ ...sample, thigh: { ...sample.thigh, valid: false }, shank: { ...sample.shank, valid: false } });
      excludedBoundarySequences.push(sample.sequence);
    } else inputs.push(sample);
    boundary = false;
  }
  return { analysis: inputs.length ? analyzeBends(inputs) : null, packetErrors, interruptionRecords, excludedBoundarySequences };
}

/** X encodes received-sample order, not normalized device time. Breaks stay gaps. */
export function recordingTrace(records: SerialRecord[]): { runs: SignalPoint[][]; sampleCount: number } {
  const runs: SignalPoint[][] = [];
  let run: SignalPoint[] | null = null, previous: LiveSample | null = null, index = 0;
  for (const record of records) {
    if (record.kind === 'error' || record.kind === 'interruption') { run = null; previous = null; }
    if (!record.sample) continue;
    const sample = record.sample, angle = relativeAngle(sample), currentIndex = index++;
    if (angle === null || !Number.isFinite(sample.timestampMs) || sample.timestampMs < 0) { run = null; previous = null; continue; }
    if (previous && (sample.sequence !== previous.sequence + 1 || sample.timestampMs <= previous.timestampMs || sample.timestampMs - previous.timestampMs > 100)) run = null;
    if (!run) { run = []; runs.push(run); }
    run.push({ index: currentIndex, angle }); previous = sample;
  }
  return { runs, sampleCount: index };
}
