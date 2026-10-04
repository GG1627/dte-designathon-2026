import { useState } from 'react';
import knee from '../../rn-app/assets/images/knee-how-it-works.png';
import sensors from '../../rn-app/assets/images/kintra-what-we-measure.png';
import injuries from '../../rn-app/assets/images/knee-injury-mechanisms.png';
import prevention from '../../rn-app/assets/images/knee-injury-risk-reduction.png';

// DOM presentation of the mobile guide. Its native require() assets cannot be imported into Vite.
const slides = [
  { title: 'How your knee works', description: 'Your knee bends and straightens as you move. Cartilage helps its surfaces glide, while ligaments help keep the joint stable.', image: knee, alt: 'Illustration of a bent knee showing bones, cartilage, and ligaments.' },
  { title: 'What Kintra tracks', description: 'Sensors on the thigh and shin estimate how much your knee bends. Pressure insoles measure loading under your feet.', note: 'This prototype uses simulated data. Foot loading is not internal knee force.', image: sensors, alt: 'Conceptual thigh and shin sensors beside a pressure-sensing insole.' },
  { title: 'How injuries can happen', description: 'Sudden twisting, awkward landings, and direct impacts can injure knee structures. Repeated demands without enough recovery can also contribute to injury.', image: injuries, alt: 'Athlete changing direction with a planted foot and the knee highlighted.' },
  { title: 'Help reduce injury risk', description: 'Warm up, build strength, and increase training gradually. Allow time for recovery and get guidance when pain persists.', note: 'Kintra supports movement awareness. It does not diagnose injuries or guarantee prevention.', image: prevention, alt: 'Athlete performing a bodyweight squat, with thigh muscles highlighted.' },
];
export function Welcome({ onStart }: { onStart: () => void }) {
  return <div className="welcome-screen stack"><span className="label">Built around you</span><svg className="welcome-mark" viewBox="0 0 280 280" aria-hidden="true"><circle cx="140" cy="140" r="116" fill="none" stroke="var(--border)"/><path d="M92 68v152m6-77 96-84" fill="none" stroke="var(--text)" strokeWidth="12" strokeLinecap="round"/><path d="m98 143 96 84" fill="none" stroke="var(--orange)" strokeWidth="12" strokeLinecap="round"/><circle cx="104" cy="144" r="25" fill="var(--bg)" stroke="var(--orange)" strokeWidth="3"/><circle cx="104" cy="144" r="5" fill="var(--orange)"/></svg><div className="stack welcome-copy"><h1>Kintra</h1><h2>Your movement,<br/>understood.</h2><p className="muted small">Personalized joint monitoring.</p></div><button className="primary" onClick={onStart}>Get started →</button></div>;
}
export function Guide({ onFinish }: { onFinish: () => void }) {
  const [index, setIndex] = useState(0), [failed, setFailed] = useState<number[]>([]);
  const slide = slides[index];
  return <div className="guide-screen stack"><div className="row"><span className="label">Kintra / Knee guide</span><button className="text-button" onClick={onFinish}>Skip introduction</button></div>
    {failed.includes(index) ? <p className="guide-image muted">Illustration unavailable</p> : <img className="guide-image" src={slide.image} alt={slide.alt} onError={() => setFailed((current) => [...current, index])}/>}
    <h1>{slide.title}</h1><p className="muted">{slide.description}</p>{slide.note ? <p className="muted small">{slide.note}</p> : null}
    <div className="guide-progress"><span className="muted small" aria-live="polite">{index + 1} of {slides.length}</span><div className="actions">{slides.map((item, i) => <button className="guide-dot" key={item.title} aria-label={`Slide ${i + 1}: ${item.title}`} aria-pressed={index === i} onClick={() => setIndex(i)}><span/></button>)}</div></div>
    <div className="actions">{index > 0 ? <button onClick={() => setIndex(index - 1)}>Back</button> : null}<button className="primary grow" onClick={() => index === slides.length - 1 ? onFinish() : setIndex(index + 1)}>{index === slides.length - 1 ? 'Explore the app' : 'Next'}</button></div>
  </div>;
}
