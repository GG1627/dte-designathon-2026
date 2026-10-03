// Synthetic observations for the designathon. These are not sensor readings.
import { landingReferenceReady } from './learned-baselines';
export const demoDate = '2026-10-03';
export type Activity = 'Running' | 'Walking';
export type Joint = {
  id: string;
  name: string;
  anatomy: 'Knee' | 'Ankle' | 'Elbow' | 'Shoulder';
  monitored: boolean;
  baselineReady: boolean;
  devices: string[];
  placement: string[];
};

export const devices = [
  { id: 'pod-01', name: 'Pod 01', placement: 'Right thigh', battery: 84 },
  { id: 'pod-02', name: 'Pod 02', placement: 'Right lower leg', battery: 79 },
  { id: 'pod-03', name: 'Pod 03', placement: 'Right shoe', battery: 91 },
];

export const joints: Joint[] = [
  {
    id: 'right-knee',
    name: 'Right knee',
    anatomy: 'Knee',
    monitored: true,
    baselineReady: landingReferenceReady('right'),
    devices: ['pod-01', 'pod-02'],
    placement: [
      'Secure the thigh and lower-leg attachments.',
      'Match each pod to its marked orientation.',
      'Check that both attachments stay in place as you bend.',
    ],
  },
  {
    id: 'right-ankle',
    name: 'Right ankle',
    anatomy: 'Ankle',
    monitored: true,
    baselineReady: false,
    devices: ['pod-02', 'pod-03'],
    placement: [
      'Secure the lower-leg attachment.',
      'Secure the foot pod to its shoe attachment.',
      'Check that the shoe attachment does not shift as you move.',
    ],
  },
  ...(['Knee', 'Ankle', 'Elbow', 'Shoulder'] as const).flatMap((anatomy) =>
    (['Left', 'Right'] as const)
      .filter(
        (side) =>
          !(side === 'Right' && (anatomy === 'Knee' || anatomy === 'Ankle')),
      )
      .map((side) => ({
        id: `${side.toLowerCase()}-${anatomy.toLowerCase()}`,
        name: `${side} ${anatomy.toLowerCase()}`,
        anatomy,
        monitored: false,
        baselineReady: false,
        devices: [],
        placement: [
          anatomy === 'Shoulder'
            ? 'Monitoring needs an upper-arm attachment and a torso reference.'
            : `Monitoring needs attachments on both sides of the ${anatomy.toLowerCase()} joint.`,
          'No devices are assigned to this joint in the demo.',
        ],
      })),
  ),
];

export type Session = {
  id: string;
  date: string;
  offset: number;
  activity: Activity;
  minutes: number;
  coverage: number;
  cycles: number;
  kneeRom: number;
  ankleRom: number;
};

export const sessions: Session[] = Array.from({ length: 60 }, (_, offset) => {
  const date = new Date(`${demoDate}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() - offset);
  const dateString = date.toISOString().slice(0, 10);
  const running = offset % 2 === 0;
  const activities: Activity[] = running ? ['Running', 'Walking'] : ['Walking'];
  return activities.map((activity) => {
    const minutes =
      activity === 'Running'
        ? offset === 0
          ? 41
          : 30 + ((offset * 7) % 20)
        : 18 + (offset % 9);
    const coverage = offset === 10 ? 64 : activity === 'Running' ? 96 : 98;
    return {
      id: `${dateString}-${activity.toLowerCase()}`,
      date: dateString,
      offset,
      activity,
      minutes,
      coverage,
      cycles: Math.round(
        ((minutes * coverage) / 100) * (activity === 'Running' ? 80 : 52),
      ),
      kneeRom: activity === 'Running' ? 92 - (offset % 5) : 58 + (offset % 5),
      ankleRom: activity === 'Running' ? 32 - (offset % 5) : 24 + (offset % 4),
    };
  });
}).flat();

export function jointSessions(joint: Joint) {
  return joint.monitored
    ? sessions.filter(
        (session) => joint.id === 'right-knee' || session.offset <= 10,
      )
    : [];
}

export function observations(
  joint: Joint,
  activity: Activity,
  days: number,
  previous = false,
) {
  return jointSessions(joint).filter(
    (s) =>
      s.activity === activity &&
      s.coverage >= 80 &&
      s.offset >= (previous ? days : 0) &&
      s.offset < (previous ? days * 2 : days),
  );
}

export function rom(joint: Joint, session: Session) {
  return joint.anatomy === 'Knee' ? session.kneeRom : session.ankleRom;
}

export function reference(_joint: Joint, _activity: Activity): {
  median: number; low: number; high: number;
} | null {
  // The Python learner currently supports bilateral landings only.
  // Never apply its reference to these separate running/walking UI fixtures.
  return null;
}

export function average(values: number[]) {
  return values.length
    ? values.reduce((sum, value) => sum + value, 0) / values.length
    : null;
}

export function formatDate(date: string, weekday = false) {
  return new Date(`${date}T12:00:00Z`).toLocaleDateString('en-US', {
    timeZone: 'UTC',
    month: 'short',
    day: 'numeric',
    ...(weekday ? { weekday: 'long' as const } : {}),
  });
}
