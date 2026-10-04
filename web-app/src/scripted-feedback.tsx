import { useState } from 'react';
import { Badge } from './ui';

const examples = [
  {
    title: 'Later bends covered less movement',
    observation: 'Example: the early bends covered a wider range than the later bends.',
    suggestion: 'If the change was unexpected, check that the sensors stayed in place and repeat the recording to check whether the pattern repeats.',
  },
  {
    title: 'Movement range varied across the set',
    observation: 'Example: the bends covered different ranges rather than repeating the same movement.',
    suggestion: 'Repeat one consistent movement with the same sensor placement to check repeatability.',
  },
  {
    title: 'The pace changed toward the end',
    observation: 'Example: later bend-and-return cycles were quicker than the earlier cycles.',
    suggestion: 'If you intended a steady pace, repeat the recording at your chosen pace and compare the cycle durations.',
  },
  {
    title: 'Some movement was missed',
    observation: 'Example: interrupted readings prevented a complete comparison of the recording.',
    suggestion: 'Check the sensor connection, reconnect if needed, and record again.',
  },
];

/** Presentation examples only. Never supplied to analysis, history, or hardware export. */
export function ScriptedFeedback() {
  const [index, setIndex] = useState(() => Math.floor(Math.random() * examples.length));
  const example = examples[index];
  return <section className="panel accent-panel" aria-label="Scripted feedback example">
    <Badge>Scripted demo feedback</Badge>
    <p className="muted small">Randomly selected example. Not calculated from this recording or the Python backend.</p>
    <div className="stack" aria-live="polite"><h2>{example.title}</h2><p>{example.observation}</p><hr/><span className="label">Example next step</span><p>{example.suggestion}</p></div>
    <button onClick={() => setIndex((current) => (current + 1 + Math.floor(Math.random() * (examples.length - 1))) % examples.length)}>Show another example</button>
  </section>;
}
