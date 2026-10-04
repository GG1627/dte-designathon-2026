// Software tests only. Mock streams do not establish physical ESP32 acceptance.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { SerialDecoder, SerialConnection, serialSupport } from '../src/serial.ts';
import { analyzeBends, buildBendFeedback } from '../../rn-app/src/data/knee-feedback.ts';
import { simulateSample } from '../../rn-app/src/data/live-simulation.ts';

const encode = (text) => new TextEncoder().encode(text);
const segment = { ax: 0, ay: 0, az: 1, gx: 180, gy: 0, gz: 0 };
const packet = (t = 50, extra = {}) => JSON.stringify({ t, thigh: segment, shank: segment, ...extra });
function decode() { const records = []; return { records, decoder: new SerialDecoder((r) => records.push(r)) }; }
const turn = () => new Promise((resolve) => setTimeout(resolve, 0));

test('software framing: partial and multiple lines, CRLF and metadata', () => {
  const { records, decoder } = decode();
  const text = `# device start\r\n${packet()}\r\n${packet(100)}\n`;
  for (const byte of encode(text)) decoder.push(new Uint8Array([byte]));
  assert.deepEqual(records.map((r) => r.kind), ['metadata', 'sample', 'sample']);
  assert.equal(records[1].sample.timestampMs, 50);
  assert.equal(records[2].sample.sequence, 1);
  assert.equal(records[1].raw, `${packet()}\r`);
});
test('hardware SI conversion and provenance never become simulation', () => {
  const { records, decoder } = decode();
  decoder.push(encode(`${packet(50, { source: 'simulated', sequence: 123, firmware: 'unknown' })}\n`));
  const r = records[0];
  assert.equal(r.sample.source, 'hardware');
  assert.equal(r.sample.thigh.accelMS2.z, 9.80665);
  assert.equal(r.sample.thigh.gyroRadS.x, Math.PI);
  assert.equal(r.sample.timestampMs, 50);
  assert.equal(r.packet.sequence, 123);
  assert.equal(r.packet.source, 'simulated');
  assert.equal(r.sequenceOrigin, 'receiver');
  assert.match(r.validityOrigin.thigh, /unknown/);
  const analysis = analyzeBends([r.sample]);
  assert.equal(analysis.source, 'hardware');
  assert.equal(analysis.status, 'unsupported');
  assert.match(buildBendFeedback({ id: 'hardware', analysis, preset: 'slow', goal: { kind: 'observe', target: null }, checkIn: { setup: 'planned', effort: 'unknown' } }, []).title, /validation/);
});
test('malformed packets, invalid UTF-8, invalid shape and sensor errors remain evidence', () => {
  const { records, decoder } = decode();
  decoder.push(encode(`bad\n[]\n${packet(0, { thigh: { ...segment, gx: 'oops' } })}\n${packet(50, { error: 'sensor missing' })}\n${packet(100, { shank: { ...segment, valid: false } })}\n${packet(150)}\n`));
  decoder.push(new Uint8Array([0xff, 10]));
  assert.equal(records.filter((r) => r.kind === 'error').length, 3);
  const readings = records.filter((r) => r.sample);
  assert.equal(readings.length, 4);
  assert.equal(readings[0].sample.thigh.valid, false);
  assert.ok(Number.isNaN(readings[0].sample.thigh.gyroRadS.x));
  assert.equal(readings[1].packet.error, 'sensor missing');
  assert.equal(readings[1].sample.shank.valid, false);
  assert.equal(readings[2].sample.shank.valid, false);
  assert.equal(readings[3].sample.thigh.valid, true);
});
test('oversized packets stay bounded, resynchronize and expose truncation', () => {
  const { records, decoder } = decode();
  decoder.push(encode('x'.repeat(100000)));
  decoder.push(encode(`\n${packet()}\n`));
  assert.equal(records[0].kind, 'error');
  assert.equal(records[0].raw.length, 8192);
  assert.equal(records[0].byteLength, 100000);
  assert.equal(records[0].rawTruncated, true);
  assert.equal(records[1].kind, 'sample');
});
test('timestamp gaps, rollback and unfinished data are preserved, never normalized', () => {
  const { records, decoder } = decode();
  decoder.push(encode(`${packet(100)}\n${packet(500)}\n${packet(1)}\n{"t":`));
  decoder.interrupt('unplugged');
  assert.deepEqual(records.filter((r) => r.sample).map((r) => r.sample.timestampMs), [100, 500, 1]);
  assert.equal(records.filter((r) => r.kind === 'interruption').length, 3);
  assert.equal(records.find((r) => r.kind === 'error').raw, '{"t":');
});
test('shared simulator returns complete bends and keeps hardware/mixed feedback gated', () => {
  const simulated = Array.from({ length: 481 }, (_, i) => simulateSample('slow', i));
  assert.equal(analyzeBends(simulated).reps.length, 4);
  assert.equal(analyzeBends(simulated).status, 'ready');
  assert.equal(analyzeBends([...simulated, { ...simulated[0], source: 'hardware' }]).status, 'unsupported');
  const interrupted = simulated.filter((s) => s.sequence < 60 || s.sequence > 80);
  const result = analyzeBends(interrupted);
  assert.equal(result.status, 'partial');
  assert.equal(result.interruptions, 1);
  assert.ok(result.reps.length < 4);
});
test('shared references exclude later sets and incompatible setup', () => {
  const analysis = analyzeBends(Array.from({ length: 481 }, (_, i) => simulateSample('slow', i)));
  const base = { preset: 'slow', goal: { kind: 'observe', target: null }, checkIn: { setup: 'planned', effort: 'unknown' }, analysis };
  const current = { ...base, id: 'current', createdAt: '2026-10-04T12:00:00.000Z' };
  const earlier = Array.from({ length: 3 }, (_, i) => ({ ...base, id: `earlier-${i}`, createdAt: `2026-10-0${i + 1}T12:00:00.000Z` }));
  const later = { ...base, id: 'later', createdAt: '2026-10-05T12:00:00.000Z' };
  const feedback = buildBendFeedback(current, [later, current, ...earlier]);
  assert.equal(feedback.referenceCount, 3);
  assert.equal(feedback.referenceRangeDeg, analysis.medianRangeDeg);
  assert.equal(buildBendFeedback({ ...current, checkIn: { ...current.checkIn, setup: 'changed' } }, earlier).referenceCount, 0);
});

class MockPort extends EventTarget {
  constructor() { super(); this.readable = null; this.opens = []; this.closes = 0; this.failClose = false; this.failOpen = false; }
  async open(options) {
    if (this.failOpen) throw new Error('open failed');
    this.opens.push(options);
    this.readable = new ReadableStream({ start: (controller) => { this.controller = controller; }, cancel: () => { this.cancelled = true; } });
  }
  async close() {
    assert.equal(this.readable?.locked, false, 'reader must release before close');
    this.closes++;
    if (this.failClose) throw new Error('close failed');
    this.readable = null;
  }
}
class MockApi extends EventTarget { constructor(port) { super(); this.port = port; this.requests = 0; } async requestPort() { this.requests++; return this.port; } }
function connection() {
  const port = new MockPort(), api = new MockApi(port), records = [], states = [];
  const client = new SerialConnection(api, (r) => records.push(r), (state, message) => states.push({ state, message }));
  return { port, api, records, states, client };
}
test('software transport: user request, duplicate connect, cancellation, release, closure and reconnect', async () => {
  const { port, api, client, records, states } = connection();
  await client.connect(); await client.connect();
  assert.equal(api.requests, 1);
  assert.deepEqual(port.opens[0], { baudRate: 115200 });
  port.controller.enqueue(encode(`${packet()}\npartial`)); await turn();
  await client.disconnect();
  assert.equal(port.cancelled, true); assert.equal(port.closes, 1);
  assert.equal(states.at(-1).state, 'disconnected');
  assert.ok(records.find((r) => r.kind === 'error' && r.raw === 'partial'));
  await client.connect(); port.controller.enqueue(encode(`${packet(0)}\n`)); await turn();
  assert.equal(records.filter((r) => r.sample).at(-1).sample.sequence, 0);
  await client.dispose();
});
test('software transport: unexpected stream end retains partial data and closes', async () => {
  const { port, client, records, states } = connection();
  await client.connect(); port.controller.enqueue(encode('partial')); port.controller.close();
  await turn(); await turn();
  assert.equal(states.at(-1).state, 'disconnected');
  assert.equal(port.closes, 1);
  assert.ok(records.find((r) => r.kind === 'interruption'));
  assert.ok(records.find((r) => r.raw === 'partial'));
  await client.dispose();
});
test('software transport: read errors preserve evidence and release the lock', async () => {
  const { port, client, records, states } = connection();
  await client.connect(); port.controller.error(new Error('framing error')); await turn(); await turn();
  assert.ok(records.some((r) => r.message?.includes('framing error')));
  assert.equal(states.at(-1).state, 'disconnected');
  assert.equal(port.closes, 1); await client.dispose();
});
test('software transport: recoverable read error acquires replacement stream', async () => {
  const { port, client, records } = connection();
  await client.connect(); const first = port.controller;
  port.readable = new ReadableStream({ start: (c) => { port.controller = c; } });
  first.error(new Error('parity error')); await turn();
  port.controller.enqueue(encode(`${packet()}\n`)); await turn();
  assert.ok(records.some((r) => r.message?.includes('parity error')));
  assert.equal(records.filter((r) => r.sample).length, 1); await client.dispose();
});
test('software transport: unplug event closes and permits reconnection', async () => {
  const { api, port, client, records } = connection();
  await client.connect(); const event = new Event('disconnect'); Object.defineProperty(event, 'port', { value: port }); api.dispatchEvent(event);
  await turn(); await turn(); assert.equal(port.readable, null);
  assert.ok(records.some((r) => r.message === 'Device disconnected.'));
  await client.connect(); assert.equal(port.opens.length, 2); await client.dispose();
});
test('software transport: chooser rejection and open failure allow retry', async () => {
  const { api, port, client, states } = connection();
  api.requestPort = async () => { throw new Error('No port selected'); };
  await client.connect(); assert.equal(states.at(-1).state, 'error');
  api.requestPort = async () => port; port.failOpen = true;
  await client.connect(); assert.equal(states.at(-1).state, 'error');
  port.failOpen = false; await client.connect(); assert.equal(states.at(-1).state, 'connected'); await client.dispose();
});
test('software transport: disconnect during chooser prevents a late open', async () => {
  const { api, port, client, states } = connection();
  let choose; api.requestPort = () => new Promise((r) => { choose = r; });
  const connecting = client.connect(); await client.disconnect(); choose(port); await connecting;
  assert.equal(port.opens.length, 0); assert.equal(states.at(-1).state, 'disconnected'); await client.dispose();
});
test('software transport: failed closure is visible and retryable', async () => {
  const { port, client, states, records } = connection();
  await client.connect(); port.failClose = true; await client.disconnect();
  assert.equal(states.at(-1).state, 'error');
  assert.ok(records.some((r) => r.message?.includes('Port closure')));
  port.failClose = false; await client.disconnect(); assert.equal(states.at(-1).state, 'disconnected'); await client.dispose();
});
test('software transport: idle stream reports a gap before recovery', async () => {
  const { port, client, records } = connection();
  await client.connect(); await new Promise((r) => setTimeout(r, 2600));
  assert.ok(records.some((r) => r.message?.includes('No serial bytes')));
  port.controller.enqueue(encode(`${packet()}\n`)); await turn(); assert.ok(records.some((r) => r.sample)); await client.dispose();
});
test('feature detection refuses insecure and unsupported browser contexts', () => {
  const windowDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'window');
  const navigatorDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'navigator');
  try {
    Object.defineProperty(globalThis, 'window', { configurable: true, value: { isSecureContext: false } });
    assert.match(serialSupport().reason, /HTTPS/);
    Object.defineProperty(globalThis, 'window', { configurable: true, value: { isSecureContext: true } });
    Object.defineProperty(globalThis, 'navigator', { configurable: true, value: {} });
    assert.match(serialSupport().reason, /desktop/);
  } finally {
    if (windowDescriptor) Object.defineProperty(globalThis, 'window', windowDescriptor); else delete globalThis.window;
    if (navigatorDescriptor) Object.defineProperty(globalThis, 'navigator', navigatorDescriptor); else delete globalThis.navigator;
  }
});
