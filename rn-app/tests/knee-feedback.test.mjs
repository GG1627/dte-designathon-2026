import test from 'node:test';
import assert from 'node:assert/strict';
import { simulateSample } from '../src/data/live-simulation.ts';
import { analyzeBends, buildBendFeedback } from '../src/data/knee-feedback.ts';

const frames = (preset = 'slow', start = 0, end = 360) =>
  Array.from({ length: end - start + 1 }, (_, i) => simulateSample(preset, i + start));
const set = (id, analysis = analyzeBends(frames())) => ({
  id, createdAt: '2026-10-04T12:00:00Z', preset: 'slow',
  goal: { kind: 'observe', target: null },
  checkIn: { setup: 'planned', effort: 'moderate' }, analysis,
});

test('detects complete bends with measured range, duration, speed and acceleration', () => {
  const result = analyzeBends(frames());
  assert.equal(result.status, 'ready');
  assert.equal(result.reps.length, 3);
  assert.equal(result.medianRangeDeg, 85);
  assert.equal(result.medianDurationS, 6);
  assert.equal(result.reps[0].timeToPeakS, 3);
  assert.ok(Math.abs(result.reps[0].peakVelocityDegS - 85 * Math.PI / 6) < 0.01);
  assert.ok(result.reps[0].peakAccelerationDegS2 > 40);
});

test('excludes partial boundary bends and stationary recordings', () => {
  assert.equal(analyzeBends(frames('slow', 50, 300)).reps.length, 1);
  assert.equal(analyzeBends(frames('slow', 50, 150)).reps.length, 0);
  assert.equal(analyzeBends(frames('standing')).status, 'insufficient');
});

test('does not join bends across invalid samples, skipped sequence or reversed time', () => {
  const invalid = frames();
  invalid[80].shank.valid = false;
  const result = analyzeBends(invalid);
  assert.equal(result.status, 'partial');
  assert.equal(result.invalidSamples, 1);
  assert.ok(result.reps.every((r) => !(r.startMs < 4000 && r.endMs > 4000)));
  const gap = frames().filter((_, i) => i !== 80);
  assert.equal(analyzeBends(gap).interruptions, 1);
  const reversed = frames();
  reversed[80].timestampMs = 0;
  assert.equal(analyzeBends(reversed).status, 'partial');
  const nonfinite = frames();
  nonfinite[80].thigh.accelMS2.z = NaN;
  assert.equal(analyzeBends(nonfinite).invalidSamples, 1);
});

test('describes changing range without attributing fatigue or injury', () => {
  const current = set('changing', analyzeBends(frames('changing', 0, 720)));
  const feedback = buildBendFeedback(current, []);
  assert.equal(current.analysis.reps.length, 6);
  assert.equal(feedback.title, 'Later bends covered less movement');
  assert.doesNotMatch(feedback.observation, /fatigue|injury|unsafe/i);
});

test('blocks hardware and mixed-source exercise feedback', () => {
  const hardware = frames().map((s) => ({ ...s, source: 'hardware' }));
  assert.equal(analyzeBends(hardware).status, 'unsupported');
  const mixed = frames();
  mixed[50].source = 'hardware';
  assert.equal(analyzeBends(mixed).status, 'unsupported');
  assert.equal(buildBendFeedback(set('real', analyzeBends(hardware)), []).title, 'Movement estimate needs validation');
});

test('uses equal-weight prior sets and excludes itself and incompatible contexts', () => {
  const current = { ...set('current'), createdAt: '2026-10-04T12:30:00Z' };
  const history = [set('current'), set('a'), set('b'), set('c'),
    { ...set('wrong-speed'), preset: 'repeated' },
    { ...set('changed'), checkIn: { setup: 'changed', effort: 'moderate' } },
    { ...set('wrong-goal'), goal: { kind: 'depth', target: 80 } },
    { ...set('future'), createdAt: '2026-10-04T13:00:00Z' },
    set('too-short', analyzeBends(frames('slow', 0, 120)))];
  const feedback = buildBendFeedback(current, history);
  assert.equal(feedback.referenceCount, 3);
  assert.equal(feedback.referenceRangeDeg, 85);
  assert.equal(buildBendFeedback(current, [set('a'), set('b')]).referenceRangeDeg, null);
  assert.equal(buildBendFeedback({ ...current, checkIn: { setup: 'unknown', effort: 'unknown' } }, history).referenceCount, 0);
});

test('prioritizes data quality and changed setup over comparison and goal coaching', () => {
  const partial = frames();
  partial[80].thigh.valid = false;
  const a = { ...set('partial', analyzeBends(partial)), goal: { kind: 'depth', target: 90 } };
  assert.equal(buildBendFeedback(a, []).title, 'Some movement was missed');
  const changed = { ...set('changed'), checkIn: { setup: 'changed', effort: 'hard' } };
  assert.equal(buildBendFeedback(changed, []).title, 'Review this set on its own');
});

test('uses a user-chosen target without inventing an ideal angle', () => {
  const current = { ...set('target'), goal: { kind: 'depth', target: 90 } };
  assert.equal(buildBendFeedback(current, []).title, 'Review your chosen bend depth');
  assert.match(buildBendFeedback(current, []).observation, /Your target: 90°/);
});
