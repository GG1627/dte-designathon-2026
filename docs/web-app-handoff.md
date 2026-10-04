# Website handoff

Built October 4, 2026 in `web-app/`. Website implementation keeps mobile source
read-only. Mobile and website work were committed separately at the user's
request. Continue keeping website commits separate from mobile work.

## Files and shared needs

- `web-app/package.json`, `package-lock.json`, `tsconfig.json`, `index.html`,
  `.gitignore`: independent React/Vite build and install.
- `web-app/src/main.tsx`, `app.tsx`, `styles.css`, `ui.tsx`, `landing.tsx`:
  DOM presentation, Home/Trends/Joints/Live navigation, details and responsive UI.
- `web-app/src/home-movement-feedback.tsx`, `setup.tsx`, `guide.tsx`:
  mobile Home feedback, no-wait demo setup, welcome and illustrated knee guide.
- `web-app/src/live.tsx`, `feedback.tsx`, `storage.ts`:
  set capture, review/evidence, browser-local simulated summaries, JSON export.
- `web-app/src/serial.ts`: byte framing, hardware decoder, port lifecycle.
- `web-app/src/hardware-recording.ts`, `hardware-review.tsx`: analysis-only
  packet-boundary adapter, shared candidate-cycle inspection, trace and evidence.
- `web-app/src/scripted-feedback.tsx`: four visibly labeled presentation examples,
  selected randomly and isolated from hardware analysis, history and exports.
- `web-app/src/shared.ts`: direct read-only mobile contracts/calculations.
- `web-app/tests/serial.test.mjs`: software-only decoder and mocked transport tests.
- `web-app/tests/hardware-recording.test.mjs`: software-only candidate inspection,
  provenance, exclusions and trace-gap regressions.
- `web-app/README.md` and this document: running and acceptance instructions.

Shared imports use `rn-app/src/data/live-simulation.ts` and `knee-feedback.ts`.
Home/Trends/Joints also reuse `demo.ts` and `learned-baselines.ts` with the frozen
Python snapshot. Native components are never imported. No shared-package move is
needed now. Contract changes in mobile must preserve exports/types or be
coordinated; rerun the website build/tests after they change. Production needs a
rebuild to receive changes. Importing code does not synchronize presentation.

Re-read the final mobile Live screen, feedback cards, theme, typography, and
Home/Trends/Joints source after the mobile implementation was reported finished.
The latest source requires planned setup, three bends, matching targets/version,
and **earlier** saved sets for reference comparison; the web uses that same engine
and matching evidence copy. The dark palette is `#111214` / `#1D2023`, orange is
`#FF5A36`, and thigh/reference blue is `#8CBFD9`. DOM dialogs replace native
sheets; desktop uses two columns and top navigation, phone uses bottom navigation.
Website screenshots were reviewed against these source rules. The existing mobile
web export predates the new feedback screens, so rendered mobile/native parity
has not been established. The user asked us to proceed from React Native source.

### Home/setup alignment update

The website now defaults to Welcome. Get started always opens the knee guide,
including on repeat visits; Skip/Explore opens Home. The guide reuses the four
mobile image assets. Its text has a small DOM copy because mobile's
`knee-guide.ts` uses native `require()` assets; keep that copy aligned when the
guide changes. No native module is imported.

Home hides its example joint/recording history until the eight-step demo setup
is complete. Continue never waits for time/counts/sensors; Strength training is
the default activity, choices survive Back/Save & close, and progress resets on
reload. Setup imports mobile's pure `setup.ts` types, labels and initial state.
It remains entirely separate from hardware calibration and the serial gate.

The Home story imports `home-bend-demo.ts` directly rather than generating a
second fixture or duplicating calculations. Six reps have first/last medians
85°/65° and whole-set median 75°; the prior-set reference is 85° from 88°/85°/82°.
The main card shows blue early/orange late schematic legs, a faded early outline,
and six rep markers. Evidence explains the comparison, reference and per-rep
measurements. Planned/unexpected and self-reported tired check-ins change next
steps without changing measurements; context is retained across tabs for this
visit. Examples never enter the user's saved Live history. Existing Web Serial
transport and hardware interpretation restrictions were not changed.

## Serial contract and boundaries

[Chrome's Web Serial guide](https://developer.chrome.com/docs/capabilities/serial)
documents the user-triggered chooser, feature detection, read errors, reader
cancellation/release and port closure.
[MDN](https://developer.mozilla.org/en-US/docs/Web/API/Web_Serial_API) documents
secure contexts and browser support limitations. This site checks support and
secure context, asks for a port only on Connect, and has no Bluetooth integration.

Wire assumption: newline-delimited JSON with `t`, `thigh` and `shank`, each with
`ax/ay/az/gx/gy/gz`; `#` lines are metadata and retained without decoding as JSON.
115200 baud, ms timestamps, acceleration in g and gyro in degrees/s are assumptions
from the supplied viewer, **not confirmed firmware facts**. The decoder converts
acceleration with 9.80665 and gyro with π/180. Original `t`, JSON source fields,
wire sequence/flags and raw lines stay in the evidence records. `LiveSample`
source is always `hardware` for serial input regardless of any wire source string.

The complementary filter uses X gyro and atan2(ay, az), with a 0.98 coefficient.
It resets on packet errors, invalid sensors, read interruptions and timestamp
rollback/gaps over 100 ms. This is a debug estimate, not validated anatomical
calibration or a faithful reconstruction of unspecified viewer filter parameters.
The 100 ms continuity gate is an engineering display rule, not a device quality
standard. A two-second byte timeout records an interruption. Device timestamps
are not normalized or replaced by host timing. Host receipt timestamps are also
retained. Receiver-generated sequence/finite-field validity do not measure packet
loss or sensor accuracy. Explicit wire flags/errors are additionally honored.

Malformed packets, invalid UTF-8, invalid sensor fields, oversized lines,
disconnect tails, read errors and close failures remain evidence. Memory bounds
and truncation are visible rather than silently discarded. A recoverable read
error releases the old reader and accepts the browser's replacement stream;
fatal errors close the port. User disconnect cancels and releases the reader
before closing. Close failures remain visible and allow Disconnect retry.

Hardware inspection/recording is supported; exercise interpretation stays blocked.
Unvalidated candidate-cycle signal summaries are shown for inspection; no exercise
scores or simulated-history comparisons are displayed.
There is no hardware-to-simulation fallback. Exports explicitly state they are
not canonical sessions. See [pipeline review](pipeline-review.md) for the existing
Python limitations. Simulation interruptions also break feedback continuity;
paused/backgrounded periods are not quietly joined into a complete bend.

### Recorded-movement demo

USB serial now provides **Record movement → Stop & review**, an elapsed recording
timer, fresh-reading state and a relative-angle trace. Only packets received
during the interval feed the review. `inspectHardwareRecording` calls the existing
shared `analyzeBends` without changing source or bypassing its `unsupported`
hardware status. It shows candidate cycles, typical signal range/duration, a
per-cycle chart and first/last-half signal medians for four or more candidates.
These describe an unvalidated debug signal, not measured anatomical repetitions,
exercise advice or a personal baseline. The Python pipeline remains disconnected.

Errors and interruption records cannot be inferred from receiver sequence alone.
The web adapter excludes the first sample after such a boundary in an analysis-only
copy so the shared detector cannot join cycles across it. Excluded receiver
sequences are exported alongside the shared result. Original records, raw sensor
validity, source and timestamps are preserved. Empty captures have no analysis,
rather than inheriting the shared engine's default simulated source.

The SVG trace plots received-sample order with explicit gaps, never normalized
time. Browser wall time drives the timer and recorded interval; candidate-cycle
durations retain the assumed device-ms calculation. Live angles clear after one
second without a sample and on packet/filter errors. Candidate results are
ephemeral until JSON export and never enter saved simulated/personal history.
Exports remain `canonicalSession: false`, with the interpretation gate intact.
No shared contracts or mobile files were changed for this feature.

After a nonempty hardware recording, a separate **Scripted demo feedback** card
shows one of four randomly selected examples (reduced range, variable range,
changing pace, interrupted capture). It explicitly states the text is not derived
from the recording or Python backend. Show another example selects a different
case and does not alter actual results. These example messages are not exported,
saved as personal history, or described as validated injury detection.

## Verification

- TypeScript and Vite production build passed. Vite warns about the 2.4 MB
  initial bundle because the existing synthetic Python snapshot is imported;
  compressed size after the Home update is approximately 170 kB. No native runtime
  is included. The guide also ships the four existing mobile PNG assets.
- 17 software tests passed: byte splitting/batching, metadata, malformed/oversized
  JSON, UTF-8, SI units/source provenance, sensor errors, timestamps/partial tails,
  shared hardware gate/reference chronology, reconnect, read recovery, chooser/open
  failures, cancellation/release/closure, unplug, close retry, idle timeout and
  unsupported/insecure feature detection.
- Playwright checked localhost at 1280×900, 375×812 and 812×375. Built-in browser
  was unavailable. Simulated Start → Finish → Review produced four bends; evidence,
  Escape dismissal, planned check-in, Save, reload persistence passed. Trends
  filters, coverage exclusions, landing comparison and Other joints passed.
  Chosen-target validation/feedback, blocked browser storage with export recovery,
  and unsupported serial UI also passed. An intentionally incomplete three-second
  slow bend correctly returned the complete-bend prompt instead of target feedback.
  The compiled `dist/` also loaded independently through Vite preview.
- A **software mock** drove the actual hardware UI/decoder: split packets,
  metadata, malformed JSON, invalid sensor flags, partial disconnect tail, and
  JSON download. The export retained `source: hardware`, original wire source
  and sequence, raw timestamps, SI values, errors and interruption. Hardware
  exercise metrics stayed hidden. No horizontal overflow at tested sizes;
  reduced-motion rendering checked. Temporary QA files live outside the repo.
- An initial favicon 404 was fixed. Node's test runner emits a module-type warning
  for mobile's package; it is harmless and mobile package settings were left alone.
- Home-update browser verification passed at 375×812, 1280×900 and 812×375 with
  reduced motion: all four guide images, Next/Back/dots/Skip/replay, setup without
  waiting, Resume and retained movement/activity choices, Strength training
  default, pre/post-setup Home, exact early/late/reference values and all six reps,
  planned/unexpected/tired branches, context across Live navigation, reload reset,
  and no Home fixtures in saved Live history. Build and all 17 existing serial
  regression tests passed. The setup movement label was corrected so its help
  text is an accessible description rather than part of the field name.

Recorded-movement software verification: all 23 web tests passed, including six
new inspection regressions. Playwright used a **software mock serial port**, not
an ESP32, at 1280×900, 375×812 and 812×375 (reduced motion). It checked the timer,
stale-angle clearing, six candidate cycles with early/late signal ranges, recording
boundaries, calculation/packet evidence, JSON export, interrupted tails, reconnect,
empty review and the existing simulation flow. No browser errors or horizontal
overflow were found. Export retained raw device time, wire source fields,
`source: hardware`, `status: unsupported`, and `canonicalSession: false`; no
hardware results entered saved simulated history. Mock packet time was compressed
relative to browser wall time. This verifies software behavior, not physical
timing, sensor accuracy or successful detection on a person.

## Physical serial acceptance — pending

No ESP32 was available to the coding session. These steps are required on a real
device and are not satisfied by mock streams:

1. Open localhost or HTTPS in a supported desktop browser. Connect by clicking
   Connect device and selecting the actual port. Confirm 115200 baud/framing and
   inspect `#` metadata against the firmware.
2. Confirm `t` units, clock origin/rollover, acquisition rate, acceleration units,
   gyro units, sensor axis/sign conventions, and any actual wire sequence,
   validity/error/source fields. Record firmware version and mounting protocol.
3. Check SI conversions against stationary gravity and an independent known
   rotation/reference. Validate calibration and anatomical angle estimation
   separately before attempting exercise interpretation.
4. Record movement, inspect thigh/shank evidence, stop and export. Compare candidate
   cycles and signal ranges against observed bends/returns and an independent
   reference; document partial/extra/missed cycles and mounting/sign effects.
   Inspect first/last-half behavior with four or more observed cycles. Confirm
   original timestamps/source fields, receiver annotations and invalid readings
   remain intact, and the export is labeled noncanonical.
5. Unplug during a partial packet. Confirm automatic review, retained tail/error
   and interruption, no fabricated metrics, released reader and closed port.
   Replug, reconnect, and record a new set. Repeat user Disconnect and a device
   reset/clock rollback. Check quiet-stream timeout and sensor failure behavior.
6. Test denied/canceled chooser, port-in-use and unsupported/insecure contexts.
   Validate device disconnect/recovery on actual Chrome/Edge versions; no mocks
   can establish native serial-driver behavior or physical sensor accuracy.

Calibration, angle estimation and segmentation must be independently validated
and the shared engine gate deliberately updated before hardware exercise feedback
can become available. Never relabel hardware packets as simulated to unlock it.
