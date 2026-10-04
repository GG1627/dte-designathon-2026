import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { createViewer } from './scene.js';
import './style.css';

function Icon({ name }) {
  const paths = {
    expand: <path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5" />,
    reset: <><path d="M3 10a9 9 0 1 1 2 8M3 4v6h6" /></>,
    play: <path d="m8 5 11 7-11 7Z" />,
    pause: <path d="M8 5v14M16 5v14" />,
    plus: <path d="M12 5v14M5 12h14" />,
    minus: <path d="M5 12h14" />,
    left: <path d="m14 6-6 6 6 6" />,
    right: <path d="m10 6 6 6-6 6" />,
    download: <path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5" />,
    help: <><circle cx="12" cy="12" r="9" /><path d="M9.5 9a2.5 2.5 0 0 1 5 0c0 2-2.5 2-2.5 4m0 3h.01" /></>,
  };
  return <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

function App() {
  const host = useRef(null);
  const viewer = useRef(null);
  const [status, setStatus] = useState('loading');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const [mode, setMode] = useState('body');
  const [view, setView] = useState('overview');
  const [rotate, setRotate] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [help, setHelp] = useState(false);
  const [notice, setNotice] = useState('');
  const [reducedMotion, setReducedMotion] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const ready = status === 'ready';

  useEffect(() => {
    viewer.current = createViewer(host.current, {
      onReady: () => setStatus('ready'),
      onProgress: setProgress,
      onError: (message) => { setError(message); setStatus('error'); },
      onInteract: () => setView('custom'),
    });
    return () => viewer.current?.dispose();
  }, []);

  useEffect(() => {
    const updateFullscreen = () => setFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener('fullscreenchange', updateFullscreen);
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const updateMotion = () => {
      setReducedMotion(media.matches);
      if (media.matches) setRotate(false);
    };
    media.addEventListener('change', updateMotion);
    return () => {
      document.removeEventListener('fullscreenchange', updateFullscreen);
      media.removeEventListener('change', updateMotion);
    };
  }, []);

  function selectMode(nextMode) {
    setMode(nextMode);
    viewer.current?.setMode(nextMode);
  }

  function selectView(nextView) {
    setView(nextView);
    viewer.current?.setView(nextView);
  }

  function toggleRotate() {
    setRotate(!rotate);
    viewer.current?.setAutoRotate(!rotate);
  }

  function reset() {
    setRotate(false);
    setMode('body');
    setView('overview');
    viewer.current?.setAutoRotate(false);
    viewer.current?.setView('overview');
    viewer.current?.setMode('body');
  }

  async function toggleFullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch {
      setNotice('Fullscreen is unavailable in this browser. You can use your browser’s presentation mode.');
    }
  }

  return (
    <div className="app-shell">
      <header className="header">
        <img className="logo" src={`${import.meta.env.BASE_URL}kintra-logo.svg`} alt="Kintra" />
        <div className="header-right">
          <span className="prototype"><span />Design concept</span>
          <button className="presentation-button" onClick={toggleFullscreen} aria-pressed={fullscreen}>
            <Icon name="expand" /><span>{fullscreen ? 'Exit fullscreen' : 'Present'}</span>
          </button>
        </div>
      </header>

      <main className="workspace">
        <aside className="intro">
          <div>
            <p className="eyebrow">Wearable / Knee</p>
            <h1>Knee <br />sleeve<span>.</span></h1>
            <p className="description">A compact compression sleeve with contoured side supports and wraparound knee bands.</p>
            <ul className="materials" aria-label="Design components">
              <li><span className="swatch knit" /><span>Compression knit</span></li>
              <li><span className="swatch orange" /><span>Contoured side supports</span></li>
              <li><span className="swatch bands" /><span>Wraparound support bands</span></li>
            </ul>
          </div>
          <a className="download" href={`${import.meta.env.BASE_URL}models/kintra.glb`} download="kintra.glb"><Icon name="download" />Download model</a>
        </aside>

        <section className="stage" aria-label="Model viewer" aria-busy={status === 'loading'}>
          <div className="stage-top">
            <div className="segmented" role="group" aria-label="Model focus">
              <button disabled={!ready} aria-pressed={mode === 'body'} onClick={() => selectMode('body')}>Full body</button>
              <button disabled={!ready} aria-pressed={mode === 'knee'} onClick={() => selectMode('knee')}>Knee detail</button>
            </div>
            <button className="icon-button help-button" title="Viewer controls" aria-label="Viewer controls" aria-expanded={help} onClick={() => setHelp(!help)}><Icon name="help" /></button>
          </div>

          <div className="canvas-host" ref={host} />

          {help && <div className="help-popover">
            <h2>Viewer controls</h2>
            <p>Drag to orbit. Scroll or pinch to zoom.</p>
            <p>Focus the model and use arrow keys to rotate, or + / − to zoom.</p>
            <button onClick={() => setHelp(false)}>Got it</button>
          </div>}

          {status !== 'ready' && <div className="status-overlay" role={status === 'error' ? 'alert' : 'status'}>
            {status === 'loading' ? <>
              <span className="loading-label">{progress < 100 ? 'Loading model' : 'Preparing model'}</span>
              <div className="loading-track"><span style={{ width: `${progress}%` }} /></div>
              <span className="loading-percent">{progress}%</span>
            </> : <>
              <h2>Unable to open the viewer</h2>
              <p>{error}</p>
              <button className="retry" onClick={() => window.location.reload()}>Reload viewer</button>
            </>}
          </div>}

          <div className="toolbar" aria-label="View controls">
            <div className="view-presets" role="group" aria-label="Camera angle">
              {['front', 'side', 'back'].map((angle) => <button key={angle} disabled={!ready} aria-pressed={view === angle} onClick={() => selectView(angle)}>{angle[0].toUpperCase() + angle.slice(1)}</button>)}
            </div>
            <span className="toolbar-divider" />
            <div className="zoom-buttons" role="group" aria-label="Zoom">
              <button className="icon-button" disabled={!ready} title="Zoom out" aria-label="Zoom out" onClick={() => viewer.current?.zoom(1.18)}><Icon name="minus" /></button>
              <button className="icon-button" disabled={!ready} title="Zoom in" aria-label="Zoom in" onClick={() => viewer.current?.zoom(0.85)}><Icon name="plus" /></button>
            </div>
            <span className="toolbar-divider" />
            <button className="icon-button" disabled={!ready} title="Reset view" aria-label="Reset view" onClick={reset}><Icon name="reset" /></button>
          </div>

          <div className="stage-bottom">
            <div className="orbit-buttons" role="group" aria-label="Rotate model">
              <button className="icon-button" disabled={!ready} title="Rotate left" aria-label="Rotate left" onClick={() => viewer.current?.orbit(-Math.PI / 8)}><Icon name="left" /></button>
              <button className="icon-button" disabled={!ready} title="Rotate right" aria-label="Rotate right" onClick={() => viewer.current?.orbit(Math.PI / 8)}><Icon name="right" /></button>
            </div>
            <button className="auto-rotate" disabled={!ready || reducedMotion} aria-pressed={rotate} title={reducedMotion ? 'Auto-rotation is disabled by your reduced-motion preference' : undefined} onClick={toggleRotate}><Icon name={rotate ? 'pause' : 'play'} />Auto-rotate</button>
          </div>
        </section>
      </main>
      <footer className="footer"><span>Kintra / Wearable design study</span><span role="status">{notice || (ready ? 'Model ready' : status === 'loading' ? 'Loading model…' : 'Viewer unavailable')}</span></footer>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
