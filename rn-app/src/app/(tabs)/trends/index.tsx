import { Host, Picker } from '@expo/ui';
import { createElement, useState, type ReactNode } from 'react';
import { Platform, View } from 'react-native';
import {
  Badge,
  PageIntro,
  Metric,
  Panel,
  Row,
  Screen,
  Section,
  SessionRow,
} from '@/components/monitoring-ui';
import { RangeChart } from '@/components/range-chart';
import { LandingBaseline } from '@/components/landing-baseline';
import { ThemedText as Text } from '@/components/themed-text';
import { Palette as c, Spacing as s } from '@/constants/theme';
import {
  average,
  formatDate,
  jointSessions,
  joints,
  observations,
  reference,
  rom,
  type Activity,
} from '@/data/demo';

export default function TrendsScreen() {
  const [days, setDays] = useState(7);
  const [jointId, setJointId] = useState('right-knee');
  const [activity, setActivity] = useState<Activity>('Running');
  const joint = joints.find((item) => item.id === jointId)!;
  const records = observations(joint, activity, days);
  const previous = observations(joint, activity, days, true);
  const currentRange = average(records.map((session) => rom(joint, session)));
  const previousRange = average(previous.map((session) => rom(joint, session)));
  const minutes = records.reduce((sum, session) => sum + session.minutes, 0);
  const previousMinutes = previous.reduce(
    (sum, session) => sum + session.minutes,
    0,
  );
  const baseline = reference(joint, activity);
  const hasReference = joint.baselineReady && baseline !== null;
  const excluded = jointSessions(joint).filter(
    (session) =>
      session.offset < days &&
      session.activity === activity &&
      session.coverage < 80,
  ).length;
  return (
    <Screen>
      <PageIntro
        title="See your patterns."
        description="Your movement, understood over time."
      />
      <LandingBaseline />
      <Text type="subtitle">Running & walking history</Text>
      <Row wrap>
        <View style={{ flexGrow: 1, gap: s.two }}>
          <FilterControl label="Joint">
            <Picker selectedValue={jointId} onValueChange={setJointId}>
              {joints.map((item) => (
                <Picker.Item key={item.id} label={item.name} value={item.id} />
              ))}
            </Picker>
          </FilterControl>
        </View>
        <View style={{ gap: s.two }}>
          <FilterControl label="Period">
            <Picker selectedValue={days} onValueChange={setDays}>
              <Picker.Item label="Past week" value={7} />
              <Picker.Item label="Past month" value={30} />
            </Picker>
          </FilterControl>
        </View>
      </Row>
      <Row>
        <Text type="small" themeColor="textSecondary">
          Compare similar activity
        </Text>
        <FilterControl label="Activity">
          <Picker selectedValue={activity} onValueChange={setActivity}>
            <Picker.Item label="Running" value="Running" />
            <Picker.Item label="Walking" value="Walking" />
          </Picker>
        </FilterControl>
      </Row>
      <Panel>
        <Row wrap>
          <Text type="smallBold">
            {joint.name} · {activity}
          </Text>
          <Badge muted>{`Past ${days} days`}</Badge>
        </Row>
        <RangeChart
          key={`${jointId}-${activity}-${days}`}
          joint={joint}
          activity={activity}
          records={records}
        />
      </Panel>
      {records.length ? (
        <>
          <Section title="Activity exposure">
            <Row wrap>
              <Metric
                label="Activity duration"
                value={String(minutes)}
                unit="min"
                detail={`Total duration of ${records.length} comparable ${activity.toLowerCase()} recordings for the ${joint.name.toLowerCase()}. Recordings below 80% valid coverage are excluded. This is a duration summary, not a tissue-load measurement.`}
              />
              <Metric
                label="Movement cycles"
                value={records
                  .reduce((sum, session) => sum + session.cycles, 0)
                  .toLocaleString()}
                detail="Counted movement cycles in the selected recordings. Detection rules depend on the activity and sensor setup; a cycle is not a force measurement."
              />
            </Row>
          </Section>
          <Section title="What changed?">
            <Panel>
              <Text type="label" style={{ color: c.accent }}>
                Movement pattern
              </Text>
              <Text type="subtitle">
                {hasReference
                  ? currentRange! >= baseline.low &&
                    currentRange! <= baseline.high
                    ? 'Your range stayed close to your reference.'
                    : 'Your range differs from your reference.'
                  : 'No learned reference for this activity yet.'}
              </Text>
              <Text type="small" themeColor="textSecondary">
                {hasReference
                  ? `${Math.round(currentRange!)}° average across ${records.length} comparable recordings. Your illustrative reference is ${baseline.low}–${baseline.high}° for ${activity.toLowerCase()} with the same placement.`
                  : `${records.length} comparable demo recordings. Landing reference values are not used for ${activity.toLowerCase()}.`}
              </Text>
              {previousRange !== null ? (
                <Text type="small">
                  {Math.abs(currentRange! - previousRange).toFixed(1)}°{' '}
                  {currentRange! >= previousRange ? 'higher' : 'lower'} than the
                  previous {days} days’ average.
                </Text>
              ) : (
                <Text type="small" themeColor="textSecondary">
                  No comparable recordings in the previous period.
                </Text>
              )}
            </Panel>
            {previous.length ? (
              <Panel>
                <Text type="label" style={{ color: c.accent }}>
                  Activity history
                </Text>
                <Text type="subtitle">
                  {Math.abs(minutes - previousMinutes)} min{' '}
                  {minutes >= previousMinutes ? 'more' : 'less'} recorded{' '}
                  {activity.toLowerCase()}.
                </Text>
                <Text type="small" themeColor="textSecondary">
                  {records.length} recordings in this period versus{' '}
                  {previous.length} in the previous {days} days. This describes
                  recorded exposure; more is not automatically better.
                </Text>
              </Panel>
            ) : null}
          </Section>
          <Text type="small" themeColor="textSecondary">
            {excluded
              ? `${excluded} recording excluded because of incomplete coverage. `
              : ''}
            Comparisons use the same joint, activity, and demo placement.
            Unrecorded activity is not included.
          </Text>
          <Section title="Compared recordings">
            {records.slice(0, days === 7 ? 4 : 8).map((session) => (
              <SessionRow key={session.id} session={session} />
            ))}
            {records.length > 8 ? (
              <Text type="small" themeColor="textSecondary">
                Showing the latest 8 recordings. All {records.length}{' '}
                measurements are available in “View data”.
              </Text>
            ) : null}
          </Section>
        </>
      ) : (
        <View style={{ gap: s.two }}>
          <Text type="subtitle">
            {joint.monitored
              ? 'No data for this selection'
              : 'This joint isn’t monitored yet'}
          </Text>
          <Text themeColor="textSecondary">
            {joint.monitored
              ? 'Try another activity or period.'
              : 'Choose a monitored joint to explore its history.'}
          </Text>
        </View>
      )}
      {records.length ? (
        <Text type="small" themeColor="textSecondary">
          Latest included observation · {formatDate(records[0].date)}
        </Text>
      ) : null}
    </Screen>
  );
}

function FilterControl({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  const content = (
    <>
      <Text type="label" themeColor="textSecondary">
        {label}
      </Text>
      <Host
        colorScheme="dark"
        seedColor={c.accent}
        matchContents
        style={{ minHeight: 48 }}>
        {children}
      </Host>
    </>
  );
  // A wrapping HTML label names the Expo UI select in the web preview.
  return Platform.OS === 'web' ? (
    createElement(
      'label',
      { style: { display: 'flex', flexDirection: 'column', gap: s.two } },
      content,
    )
  ) : (
    <View style={{ gap: s.two }}>{content}</View>
  );
}
