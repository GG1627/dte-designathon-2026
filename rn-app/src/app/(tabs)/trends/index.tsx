import { useState } from 'react';
import { LandingBaseline } from '@/components/landing-baseline';
import { Action, PageIntro, Panel, Row, Screen, Section, SessionRow, Sheet } from '@/components/monitoring-ui';
import { RangeChart } from '@/components/range-chart';
import { SelectionControl } from '@/components/selection-control';
import { ThemedText as Text } from '@/components/themed-text';
import { average, jointSessions, joints, observations, rom, type Activity } from '@/data/demo';

export default function TrendsScreen() {
  const [days, setDays] = useState('7');
  const [jointId, setJointId] = useState('right-knee');
  const [activity, setActivity] = useState('Running');
  const [qualityOpen, setQualityOpen] = useState(false);
  const joint = joints.find((item) => item.id === jointId)!;
  const landing = activity === 'Landings';
  const motionActivity = activity as Activity;
  const records = landing ? [] : observations(joint, motionActivity, Number(days));
  const previous = landing ? [] : observations(joint, motionActivity, Number(days), true);
  const current = average(records.map((session) => rom(joint, session)));
  const prior = average(previous.map((session) => rom(joint, session)));
  const excluded = jointSessions(joint).filter((session) => session.offset < Number(days)
    && session.activity === activity && session.coverage < 80).length;
  const activities = ['Running', 'Walking', ...(joint.anatomy === 'Knee' ? ['Landings'] : [])];
  return <>
    <Screen>
      <PageIntro title="Trends" />
      <Row wrap>
        <SelectionControl label="Joint" value={jointId} onChange={(value) => {
          setJointId(value);
          if (activity === 'Landings' && joints.find((item) => item.id === value)?.anatomy !== 'Knee') setActivity('Running');
        }} options={joints.filter((item) => item.monitored).map((item) => ({ value: item.id, label: item.name }))} />
        <SelectionControl label="Activity" value={activity} onChange={setActivity}
          options={activities.map((value) => ({ value, label: value }))} />
      </Row>
      {landing ? <LandingBaseline mode="summary" initialSide={joint.id.startsWith('left') ? 'left' : 'right'} key={joint.id} /> : <>
        <SelectionControl label="Period" value={days} onChange={setDays}
          options={[{ value: '7', label: 'Past week' }, { value: '30', label: 'Past month' }]} />
        <Panel>
          <RangeChart key={`${jointId}-${activity}-${days}`} joint={joint} activity={motionActivity} records={records} />
          {current !== null && prior !== null ? <Text type="small">
            {Math.abs(current - prior).toFixed(1)}° {current >= prior ? 'higher' : 'lower'} than the previous {days} days.
          </Text> : null}
        </Panel>
        <Row wrap>
          <Text type="small" themeColor="textSecondary">{records.length} recordings{excluded ? ` · ${excluded} excluded` : ''}</Text>
          <Action onPress={() => setQualityOpen(true)}>Recording details</Action>
        </Row>
        {records.length ? <Section title="Recent recordings">
          {records.slice(0, 3).map((session) => <SessionRow key={session.id} session={session} />)}
        </Section> : null}
      </>}
    </Screen>
    <Sheet title="Recording details" open={qualityOpen} onClose={() => setQualityOpen(false)}>
      <Text>{joint.name} · {activity} · past {days} days</Text>
      <Text type="small">Only recordings with at least 80% valid coverage are included. {excluded} excluded.</Text>
      <Text type="small" themeColor="textSecondary">No learned running or walking reference is available. Landing comparisons use a separate activity-specific reference. All data is synthetic.</Text>
      <Text type="small">{records.reduce((sum, session) => sum + session.minutes, 0)} min recorded · {records.reduce((sum, session) => sum + session.cycles, 0).toLocaleString()} movement cycles.</Text>
      {records.map((session) => <SessionRow key={session.id} session={session} />)}
    </Sheet>
  </>;
}
