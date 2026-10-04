import { analyzeBends, buildBendFeedback, type BendSet } from './knee-feedback';
import { simulateSample } from './live-simulation';

// Scripted history for the Home demo, never added to the user's saved Live sets.
// Scale relative flexion and gyro together; regenerate gravity for the new angle.
function makeSet(id: string, day: string, ranges: number | number[]): BendSet {
  const samples = Array.from({ length: 721 }, (_, sequence) => {
    const sample = simulateSample('slow', sequence);
    const range = typeof ranges === 'number' ? ranges : ranges[Math.min(ranges.length - 1, Math.floor(sequence / 120))];
    const angleDeg = sample.thigh.angleDeg + (sample.shank.angleDeg - sample.thigh.angleDeg) * range / 85;
    const angle = angleDeg * Math.PI / 180;
    return { ...sample, shank: { ...sample.shank, angleDeg,
      accelMS2: { x: 0, y: 9.80665 * Math.sin(angle), z: 9.80665 * Math.cos(angle) },
      gyroRadS: { x: sample.thigh.gyroRadS.x + (sample.shank.gyroRadS.x - sample.thigh.gyroRadS.x) * range / 85, y: 0, z: 0 },
    } };
  });
  return { id, createdAt: `${day}T12:00:00Z`, preset: 'slow',
    goal: { kind: 'observe', target: null }, checkIn: { setup: 'planned', effort: 'moderate' },
    analysis: analyzeBends(samples) };
}

export const homeBendHistory = [
  makeSet('home-demo-3', '2026-10-02', 88),
  makeSet('home-demo-2', '2026-10-01', 85),
  makeSet('home-demo-1', '2026-09-30', 82),
];
export const homeBendSet = makeSet('home-demo-current', '2026-10-03', [85, 85, 85, 65, 65, 65]);
export const homeBendFeedback = buildBendFeedback(homeBendSet, homeBendHistory);
