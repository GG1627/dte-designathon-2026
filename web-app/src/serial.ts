import type { LiveSample, SegmentReading } from '../../rn-app/src/data/live-simulation.ts';

export const SERIAL_ASSUMPTIONS = {
  baudRate: 115200, timestamp: 'milliseconds (unconfirmed)',
  acceleration: 'g (unconfirmed)', gyro: 'degrees/s (unconfirmed)',
  angle: 'complementary-filter debug estimate; not anatomical calibration',
  sequence: 'receiver generated, not measured device continuity',
  validity: 'finite fields and optional wire flags; not validated sensor quality',
} as const;
export type SerialRecord = {
  kind: 'sample' | 'metadata' | 'error' | 'interruption';
  receivedAt: string; raw?: string; rawTruncated?: boolean; byteLength?: number;
  packet?: Record<string, unknown>; sample?: LiveSample; message?: string;
  sequenceOrigin?: 'receiver'; validityOrigin?: { thigh: string; shank: string };
};
const errorText = (error: unknown) => error instanceof Error ? error.message : String(error);
const isObject = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value);
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);

/** Bounded byte framing; oversized packets are discarded through the next newline. */
export class SerialDecoder {
  private bytes: number[] = [];
  private byteLength = 0;
  private sequence = 0;
  private previous: { t: number; thigh: number; shank: number } | null = null;
  private emit: (record: SerialRecord) => void;
  private maxBytes: number;
  constructor(emit: (record: SerialRecord) => void, maxBytes = 8192) { this.emit = emit; this.maxBytes = maxBytes; }

  push(chunk: Uint8Array) {
    for (const byte of chunk) {
      if (byte === 10) { this.line(); continue; }
      this.byteLength++;
      if (this.bytes.length < this.maxBytes) this.bytes.push(byte);
    }
  }
  interrupt(message: string) {
    this.flush();
    this.previous = null;
    this.emit({ kind: 'interruption', receivedAt: new Date().toISOString(), message });
  }
  flush() {
    if (!this.byteLength) return;
    this.emit({ kind: 'error', receivedAt: new Date().toISOString(),
      raw: new TextDecoder().decode(new Uint8Array(this.bytes)),
      rawTruncated: this.byteLength > this.maxBytes, byteLength: this.byteLength,
      message: 'Interrupted packet: no terminating newline.' });
    this.bytes = []; this.byteLength = 0; this.previous = null;
  }
  private line() {
    const bytes = new Uint8Array(this.bytes);
    const length = this.byteLength;
    this.bytes = []; this.byteLength = 0;
    const base = { receivedAt: new Date().toISOString(), raw: new TextDecoder().decode(bytes), byteLength: length };
    const fail = (message: string) => {
      this.previous = null;
      this.emit({ ...base, kind: 'error', message, rawTruncated: length > this.maxBytes });
    };
    if (length > this.maxBytes) { fail(`Packet exceeds ${this.maxBytes} bytes; retained prefix only.`); return; }
    let raw: string;
    try { raw = new TextDecoder('utf-8', { fatal: true }).decode(bytes).trim(); }
    catch { fail('Invalid UTF-8 packet.'); return; }
    if (!raw) return;
    if (raw.startsWith('#')) { this.emit({ ...base, kind: 'metadata' }); return; }
    let packet: Record<string, unknown>;
    try {
      const parsed: unknown = JSON.parse(raw);
      if (!isObject(parsed)) throw new Error('Expected a JSON object.');
      packet = parsed;
    } catch (error) { fail(`Malformed JSON: ${errorText(error)}`); return; }
    if (!finite(packet.t) || !isObject(packet.thigh) || !isObject(packet.shank)) {
      this.emit({ ...base, packet, kind: 'error', message: 'Expected finite t and thigh/shank objects.' });
      this.previous = null; return;
    }
    const t = packet.t;
    const dt = this.previous ? (t - this.previous.t) / 1000 : 0;
    if (this.previous && (dt <= 0 || dt > 0.1)) {
      this.emit({ kind: 'interruption', receivedAt: base.receivedAt,
        message: `Device timestamp discontinuity: ${this.previous.t} → ${t} ms; debug filter reset.` });
      this.previous = null;
    }
    const segment = (wire: Record<string, unknown>, prior: number | undefined): SegmentReading => {
      const numeric = ['ax', 'ay', 'az', 'gx', 'gy', 'gz'].every((key) => finite(wire[key]));
      const valid = numeric && (wire.valid === undefined || wire.valid === true) && !wire.error && !packet.error;
      const vector = (prefix: string, scale: number) => {
        const axis = (key: string) => { const value = wire[`${prefix}${key}`]; return finite(value) ? value * scale : NaN; };
        return { x: axis('x'), y: axis('y'), z: axis('z') };
      };
      const accelMS2 = vector('a', 9.80665);
      const gyroRadS = vector('g', Math.PI / 180);
      const tilt = Math.atan2(accelMS2.y, accelMS2.z) * 180 / Math.PI;
      const angleDeg = valid ? prior === undefined ? tilt :
        0.98 * (prior + (wire.gx as number) * dt) + 0.02 * tilt : NaN;
      return { valid, accelMS2, gyroRadS, angleDeg };
    };
    const thigh = segment(packet.thigh, this.previous?.thigh);
    const shank = segment(packet.shank, this.previous?.shank);
    const sample: LiveSample = { source: 'hardware', sequence: this.sequence++, timestampMs: t, thigh, shank };
    this.previous = thigh.valid && shank.valid ? { t, thigh: thigh.angleDeg, shank: shank.angleDeg } : null;
    this.emit({ ...base, kind: 'sample', packet, sample, sequenceOrigin: 'receiver',
      validityOrigin: {
        thigh: packet.thigh.valid === undefined ? 'receiver field check; device quality unknown' : 'wire flag plus receiver field check',
        shank: packet.shank.valid === undefined ? 'receiver field check; device quality unknown' : 'wire flag plus receiver field check',
      }, message: thigh.valid && shank.valid ? undefined : 'Invalid sensor fields or sensor error; original packet retained.' });
  }
}

// Small structural interfaces keep transport testable without browser globals.
export interface SerialPortLike {
  readable: ReadableStream<Uint8Array> | null;
  open(options: { baudRate: number }): Promise<void>;
  close(): Promise<void>;
}
export interface SerialApiLike extends EventTarget { requestPort(): Promise<SerialPortLike> }
export function serialSupport(): { api?: SerialApiLike; reason?: string } {
  if (!window.isSecureContext) return { reason: 'Open on localhost or HTTPS to connect a serial device.' };
  const api = (navigator as Navigator & { serial?: SerialApiLike }).serial;
  return api ? { api } : { reason: 'Use a desktop browser with Web Serial support, such as Chrome or Edge.' };
}
export type SerialState = 'disconnected' | 'connecting' | 'connected' | 'disconnecting' | 'error';
export class SerialConnection {
  private port: SerialPortLike | null = null;
  private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
  private task: Promise<void> | null = null;
  private closing = false;
  private busy = false;
  private decoder: SerialDecoder;
  private lastRead = 0;
  private stalled = false;
  private watchdog: ReturnType<typeof setInterval> | undefined;
  private disconnectListener = (event: Event) => {
    if (event.target === this.port || (event as Event & { port?: SerialPortLike }).port === this.port) {
      this.decoder.interrupt('Device disconnected.');
      void this.disconnect();
    }
  };
  private api: SerialApiLike;
  private emit: (record: SerialRecord) => void;
  private onState: (state: SerialState, message?: string) => void;
  constructor(api: SerialApiLike, emit: (record: SerialRecord) => void,
    onState: (state: SerialState, message?: string) => void) {
    this.api = api; this.emit = emit; this.onState = onState;
    this.decoder = new SerialDecoder(emit);
    api.addEventListener('disconnect', this.disconnectListener);
  }
  async connect() {
    if (this.busy || this.port) return;
    this.busy = true; this.closing = false;
    this.onState('connecting');
    try {
      // Called directly from a click; no asynchronous work precedes requestPort.
      const port = await this.api.requestPort();
      if (this.closing) { this.onState('disconnected'); return; }
      await port.open({ baudRate: SERIAL_ASSUMPTIONS.baudRate });
      this.port = port;
      if (this.closing) { await this.closePort(); return; }
      if (!port.readable) throw new Error('The selected port has no readable stream.');
      this.decoder = new SerialDecoder(this.emit);
      this.onState('connected'); this.lastRead = Date.now(); this.stalled = false;
      this.watchdog = setInterval(() => {
        if (!this.stalled && Date.now() - this.lastRead > 2000) {
          this.stalled = true; this.decoder.interrupt('No serial bytes for 2 seconds. Recording has a gap.');
        }
      }, 500);
      this.task = this.read(port);
    } catch (error) {
      await this.closePort();
      this.emit({ kind: 'error', receivedAt: new Date().toISOString(), message: `Connection: ${errorText(error)}` });
      this.onState('error', errorText(error));
    } finally { this.busy = false; }
  }
  private async read(port: SerialPortLike) {
    try {
      while (!this.closing && port.readable) {
        const stream = port.readable;
        const reader = stream.getReader(); this.reader = reader;
        try {
          while (!this.closing) {
            const { value, done } = await reader.read();
            if (done) { if (!this.closing) this.decoder.interrupt('Serial stream ended.'); return; }
            if (value) { this.lastRead = Date.now(); this.stalled = false; this.decoder.push(value); }
          }
        } catch (error) {
          if (!this.closing) this.decoder.interrupt(`Serial read error: ${errorText(error)}`);
          // Web Serial replaces readable on recoverable errors. Avoid spinning on an unchanged stream.
          if (this.closing || port.readable === stream) return;
        } finally { reader.releaseLock(); this.reader = null; }
      }
    } catch (error) {
      this.decoder.interrupt(`Serial stream error: ${errorText(error)}`);
    } finally {
      clearInterval(this.watchdog); this.decoder.flush();
      await this.closePort();
    }
  }
  private async closePort() {
    if (!this.port) { this.onState('disconnected'); return; }
    try { await this.port.close(); this.port = null; this.onState('disconnected'); }
    catch (error) {
      this.emit({ kind: 'error', receivedAt: new Date().toISOString(), message: `Port closure: ${errorText(error)}` });
      this.onState('error', `Could not close port: ${errorText(error)}. Retry Disconnect.`);
    }
  }
  async disconnect() {
    this.closing = true; this.onState('disconnecting'); clearInterval(this.watchdog);
    this.decoder.interrupt('Connection stopped; remaining data retained.');
    try { await this.reader?.cancel(); }
    catch (error) { this.emit({ kind: 'error', receivedAt: new Date().toISOString(), message: `Reader cancellation: ${errorText(error)}` }); }
    if (this.task) { await this.task; this.task = null; if (this.port) await this.closePort(); }
    else if (!this.busy) await this.closePort();
  }
  async dispose() { this.api.removeEventListener('disconnect', this.disconnectListener); await this.disconnect(); }
}
