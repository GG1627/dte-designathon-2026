// Software inspection tests. Constructed hardware-shaped readings are not device validation.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { inspectHardwareRecording, recordingTrace } from '../src/hardware-recording.ts';

function records(cycles = 6) {
  return Array.from({ length: cycles * 80 + 1 }, (_, sequence) => {
    const phase = sequence % 80 / 80 * 2 * Math.PI;
    const amplitude = sequence < 240 ? 85 : 65;
    const timestampMs = 5000 + sequence * 50;
    const thigh = { valid: true, angleDeg: 0, accelMS2: { x: 0, y: 0, z: 9.80665 }, gyroRadS: { x: 0, y: 0, z: 0 } };
    const shank = { ...thigh, angleDeg: amplitude * (1 - Math.cos(phase)) / 2,
      gyroRadS: { x: amplitude / 2 * Math.sin(phase) * (2 * Math.PI / 4) * Math.PI / 180, y: 0, z: 0 } };
    return { kind: 'sample', receivedAt: new Date(1791115200000 + sequence * 50).toISOString(),
      packet: { t: timestampMs, source: 'esp32', sequence: 1000 + sequence }, raw: `wire packet ${sequence}`,
      sample: { source: 'hardware', timestampMs, sequence, thigh, shank } };
  });
}

test('software inspection runs the shared detector without unlocking or relabeling hardware', () => {
  const captured = records(), original = structuredClone(captured);
  const result = inspectHardwareRecording(captured);
  assert.equal(result.analysis.source, 'hardware');
  assert.equal(result.analysis.status, 'unsupported');
  assert.equal(result.analysis.reps.length, 6);
  assert.equal(result.analysis.firstHalfRangeDeg, 85);
  assert.equal(result.analysis.secondHalfRangeDeg, 65);
  assert.equal(result.analysis.medianRangeDeg, 75);
  assert.deepEqual(captured, original, 'raw data, source fields, timestamps and validity must remain unchanged');
});

test('metadata does not split candidate cycles', () => {
  const captured = records(2);
  captured.splice(40, 0, { kind: 'metadata', raw: '# config', receivedAt: captured[40].receivedAt });
  const result = inspectHardwareRecording(captured);
  assert.equal(result.analysis.reps.length, 2);
  assert.equal(recordingTrace(captured).runs.length, 1);
});

test('malformed packets split analysis even when receiver sequences remain consecutive', () => {
  const captured = records(2), boundaryTime = captured[40].sample.timestampMs;
  captured.splice(40, 0, { kind: 'error', raw: '{broken', message: 'Malformed JSON', receivedAt: captured[40].receivedAt });
  const result = inspectHardwareRecording(captured);
  assert.equal(result.packetErrors, 1);
  assert.deepEqual(result.excludedBoundarySequences, [40]);
  assert.equal(result.analysis.invalidSamples, 1);
  assert.ok(result.analysis.reps.every((rep) => !(rep.startMs < boundaryTime && rep.endMs > boundaryTime)));
  assert.equal(captured[41].sample.thigh.valid, true, 'exclusion is analysis-only');
  assert.equal(recordingTrace(captured).runs.length, 2);
});

test('interruptions and sensor errors remain boundaries and trace gaps', () => {
  const captured = records(3);
  captured[120].sample.shank.valid = false;
  captured.splice(40, 0, { kind: 'interruption', message: 'Read stream replaced', receivedAt: captured[40].receivedAt });
  const result = inspectHardwareRecording(captured);
  assert.equal(result.interruptionRecords, 1);
  assert.equal(result.analysis.invalidSamples, 2);
  assert.equal(recordingTrace(captured).runs.length, 3);
  assert.equal(recordingTrace(captured).sampleCount, 241);
});

test('device timing jumps and reversal are never joined in the trace', () => {
  const captured = records(1);
  captured[30].sample.timestampMs += 300;
  const trace = recordingTrace(captured);
  assert.equal(trace.runs.length, 3);
  assert.equal(inspectHardwareRecording(captured).analysis.interruptions, 2);
  assert.equal(captured[30].sample.timestampMs, 6800);
});

test('empty, stationary, partial, and mixed recordings do not become ready hardware feedback', () => {
  assert.equal(inspectHardwareRecording([]).analysis, null);
  assert.equal(inspectHardwareRecording([{ kind: 'error', message: 'Unplugged partial packet' }]).analysis, null);
  const stationary = records(1).map((record) => ({ ...record, sample: { ...record.sample, shank: record.sample.thigh } }));
  assert.equal(inspectHardwareRecording(stationary).analysis.reps.length, 0);
  assert.equal(inspectHardwareRecording(records(1).slice(0, 40)).analysis.reps.length, 0);
  const mixed = records(1);
  mixed[0].sample.source = 'simulated';
  assert.equal(inspectHardwareRecording(mixed).analysis.source, 'mixed');
  assert.equal(inspectHardwareRecording(mixed).analysis.status, 'unsupported');
});
