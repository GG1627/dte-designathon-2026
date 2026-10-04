export type MovementPreset = 'slow' | 'repeated' | 'standing' | 'changing';

export const movementPresets: { id: MovementPreset; label: string }[] = [
  { id: 'slow', label: 'Slow knee bends' },
  { id: 'repeated', label: 'Repeated flexion' },
  { id: 'standing', label: 'Standing still' },
  { id: 'changing', label: 'Changing bend depth' },
];

export const SIMULATION_RATE_HZ = 20;
export const SAMPLE_INTERVAL_MS = 1000 / SIMULATION_RATE_HZ;
const radians = Math.PI / 180;

export type Vector3 = { x: number; y: number; z: number };
export type SegmentReading = {
  angleDeg: number;
  accelMS2: Vector3;
  gyroRadS: Vector3;
  valid: boolean;
};

// Display contract: a future hardware decoder can supply the same SI units.
// angleDeg is a display estimate, separate from canonical session analysis.
export type LiveSample = {
  source: 'simulated' | 'hardware';
  sequence: number;
  timestampMs: number;
  thigh: SegmentReading;
  shank: SegmentReading;
};

function segment(angleDeg: number, rateDegS: number): SegmentReading {
  const angle = angleDeg * radians;
  return {
    angleDeg,
    // Idealized X-axis rotation: gravity only, without linear acceleration/noise.
    accelMS2: { x: 0, y: 9.80665 * Math.sin(angle), z: 9.80665 * Math.cos(angle) },
    gyroRadS: { x: rateDegS * radians, y: 0, z: 0 },
    valid: true,
  };
}

export function simulateSample(preset: MovementPreset, sequence: number): LiveSample {
  const timestampMs = sequence * SAMPLE_INTERVAL_MS;
  const omega = 2 * Math.PI / (preset === 'repeated' ? 2.6 : 6);
  const phase = omega * timestampMs / 1000;
  const wave = preset === 'standing' ? 0 : (1 - Math.cos(phase)) / 2;
  const velocity = preset === 'standing' ? 0 : omega * Math.sin(phase) / 2;
  const cycle = Math.floor(timestampMs / 1000 / 6);
  const range = preset === 'repeated' ? 105 : preset === 'changing' ? Math.max(50, 85 - cycle * 5) : 85;
  const thighAngle = 14 * wave;
  const kneeAngle = range * wave;
  return {
    source: 'simulated',
    sequence,
    timestampMs,
    thigh: segment(thighAngle, 14 * velocity),
    shank: segment(thighAngle + kneeAngle, (14 + range) * velocity),
  };
}
