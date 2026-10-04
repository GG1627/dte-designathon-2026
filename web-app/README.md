# Kintra web

Standalone React/Vite DOM application. `rn-app/` is read-only to this project.

```powershell
cd web-app
npm ci
npm run dev
```

Open the printed localhost URL (normally http://127.0.0.1:5173).
Node 22.18+ is required for the dependency-free TypeScript software tests.

```powershell
npm test
npm run build
npm run preview
```

Home, Trends and Joints reuse the mobile app's frozen synthetic observations,
including the October 3 demo date and separate Python landing snapshots. They
are not connected to live device packets. Live has distinct Simulation and USB
serial modes, Start set → Finish set → Review, and expandable evidence.

The initial route opens the mobile-style welcome screen. Get started always opens
the four-slide knee guide; Skip or Explore the app opens Home. Before setup, Home
shows an introduction. The eight-step demo setup advances immediately without
waiting for counts or timers, defaults to Strength training, and retains choices
when closed or revisited. Completing it reveals the example Home movement history.
Setup progress and Home check-ins last for this visit and reset on reload.

Home imports `rn-app/src/data/home-bend-demo.ts` directly: six complete bends,
early 85° / late 65°, a 20° decrease, and an 85° reference from three earlier
sets. Intentional/unexpected and optional tired check-ins change suggestions,
not measurements. The leg drawings, six rep markers and evidence dialog match
the mobile presentation. These examples never enter saved Live history. Setup
is a simulated walkthrough, not hardware calibration or a learned real baseline.

Simulation uses the mobile generator and feedback engine directly. Saved set
summaries/check-ins are local to this website's browser origin (30 sets maximum),
separate from mobile storage. Raw simulated samples remain available for export
only during the current review. Reviewing a saved set exports its summary without
the original sample stream. Storage failures leave the current set reviewable.

USB serial uses a click-triggered browser port chooser and 115200 baud. Hardware
sets are inspection recordings, never validated exercise feedback. Units are unconfirmed;
the relative angle is a complementary-filter debug estimate. Recording stops
on disconnect, 6,000 samples, or 12,000 evidence records; export before leaving.
Without a set, the packet inspector retains only the latest 100 records. Partial
and malformed packets remain evidence; oversized lines retain an explicitly
marked 8,192-byte prefix and total byte count. Reconnecting starts a new stream.

In USB serial mode, use **Record movement → Stop & review** to capture a chosen
interval. A timer and live relative-angle trace show the recording in progress.
The review runs the existing shared bend detector on those captured readings:
candidate cycles, typical debug-signal range/cycle duration, and first/last-half
signal ranges when at least four candidates exist. These are explicitly
unvalidated inspection results; the engine keeps `source: hardware` and
`status: unsupported`. No exercise advice, anatomical accuracy claim, personal
reference, or simulated-history save is enabled. The Python baseline pipeline
is not connected by this feature.

Nonempty hardware reviews also include a separate **Scripted demo feedback**
card, randomly selected from four presentation examples: reduced range, variable
range, changing pace, and interrupted capture. Each card explicitly states it is
not calculated from the recording or Python backend. Show another example chooses
a different card. Examples make no injury-detection claims and are excluded from
analysis, saved history, and hardware JSON exports.

Known packet/filter breaks also break candidate detection. The first sample
after a break is excluded in an analysis-only copy; original packets, sensor
validity and timestamps stay untouched. The graph uses received-sample order,
leaves gaps at interruptions, and does not replace device time. The recording
timer uses browser wall time; candidate durations assume the device's `t` is ms.
Missing/stale readings clear the live angle rather than appearing current.

Exports use `kintra.web.inspection/1`, retain original JSON fields and device
timestamps, and explicitly set `canonicalSession: false`. Unavailable numeric
fields serialize as `null`. Receiver-generated sequence numbers and finite-field
validity checks are labeled as such; missing wire quality is unknown. No Bluetooth,
backend, anatomical calibration, or canonical Python ingestion is implemented.

The project needs the sibling mobile data files at development/build time; the
generated `dist/` is standalone. `src/shared.ts` imports the dependency-free mobile
contracts instead of forking them. Do not move them into a shared package until
both sessions agree; no mobile changes are required by this website.

See [website handoff and physical acceptance](../docs/web-app-handoff.md).
