# Kintra app handoff

Updated October 3, 2026. Read [PRODUCT_CONTEXT.md](../PRODUCT_CONTEXT.md) before changing product behavior and follow the repository and app `AGENTS.md` instructions.

## Current state

Kintra names both the wearable platform and companion app. This is a designathon UI prototype built with Expo SDK 57, React Native, and Expo Router. It uses synthetic observations, not live sensor readings.

| Route | Implemented experience |
| --- | --- |
| `/` | Branded welcome, K mark, "Your movement, understood." Get started always opens `/onboarding` for demo replay. |
| `/onboarding` | Four illustrated knee-education slides; swipe, Next, Back, tappable progress dots, Skip and Explore the app. Replay through Home's Knee guide link. |
| `/home` | Compact setup entry before completion; afterward knee-bend baseline comparison and suggestion first, then monitored joints, latest activity card, device sheet. |
| `/setup` | Eight-step demo walkthrough. Continue fills each simulated check immediately; optional timers, movement choices, skip, Back, and close remain available. |
| `/trends` | One joint/activity at a time, week/month range chart, concise period difference, exact-data and quality sheets. Landings show a compact learned comparison. |
| `/joints` | Monitored joints first; unmonitored joints available through Other joints. |
| `/joint/[id]` | Activity-specific primary range or landing comparison; cycles, coverage, assessments and setup behind a tap. |
| `/session/[id]` | Recorded duration and joint ranges; coverage, cycles and context in Details. |
| `/demo-lab` | Separate synthetic experiment: participant, side, scenario and history-size controls, full metric/history/quality inspection. |

Native uses native tabs; web has a separate tab-bar component. Sheets/pickers use `@expo/ui`. The smooth coverage ring and header K mark use `react-native-svg`.

## Approved design

| Role | Color |
| --- | --- |
| Background / card surface | `#111214` / `#1D2023` |
| Main accent, recorded movement, selected controls | `#FF5A36` |
| Personal reference and comparison data | `#8CBFD9` |
| Main / secondary text | `#F4F2ED` / `#A6ADB5` |

- Preserve rounded cards, quiet borders, large numbers/smaller units, compact branded headers, and the K motif.
- Keep welcome-screen colors consistent with shared theme tokens in `src/constants/theme.ts`.
- Lead with joint measurements; keep coverage, cycles and methodology in details. Avoid restoring the large coverage ring, activity bars, or repeated reference controls to everyday screens.
- Orange shows observed movement; blue shows the reference. Developing baselines have no reference band.
- Filtered charts have a short fade/small movement with reduced-motion support: Reanimated on native, CSS on web. Tabs retain platform behavior.
- ScrollView automatic adjustment owns top insets. Adding manual `insets.top` padding as well caused excess space above headers.
- `Link asChild` did not forward callback Pressable styles correctly in this preview. Joint/activity cards use static styles to keep their horizontal layouts intact.

## Data and limitations

- `src/data/demo.ts` contains deterministic samples anchored to October 3, 2026; they do not advance with the actual date.
- Right knee and ankle are monitored. Other joints have no data. The ankle baseline is developing.
- The lower-leg pod is shared by knee and ankle; simulating it offline affects both.
- Connection toggles/checklist confirmations live in `demo-provider.tsx` memory and reset on reload.
- Running/walking Trends compare the same joint/activity and exclude recordings below 80% valid coverage. They have no learned reference. Landing comparisons display actual Python learner results from the bundled synthetic snapshot.
- No Bluetooth, backend, authentication, persistent measurement storage, hardware calibration, or validated inference pipeline is connected. The knee guide stores only a device-local completion preference.
- Main measurements: ROM, cycles, duration, coverage. Strength needs instrumented assessment hardware; do not derive it from motion alone or invent readiness/injury scores.
- Display name is Kintra. Slug, scheme, icons and splash artwork still use starter configuration/assets and need a branding pass before release.

## Key files

| Area | Files |
| --- | --- |
| Routes | `src/app/` |
| Cards, headers, sheets, activity rows | `src/components/monitoring-ui.tsx` |
| Home visual indicators | `src/components/home-visuals.tsx` |
| Trends chart/data sheet | `src/components/range-chart.tsx` |
| Navigation | `src/components/app-tabs.tsx`, `app-tabs.web.tsx`, `tab-stack.tsx` |
| Typography/theme/web motion | `src/components/themed-text.tsx`, `src/constants/theme.ts`, `src/global.css` |
| Sample data/device state | `src/data/demo.ts`, `src/components/demo-provider.tsx` |
| Knee education/copy/local completion | `src/app/onboarding.tsx`, `src/data/knee-guide.ts`, `src/utils/onboarding.ts`, `assets/images/knee-*.png`, `assets/images/kintra-what-we-measure.png` |

## Run and verify

From `rn-app`:

```powershell
npm ci
npx expo start
# Alternatively, the web preview port used during design work:
npx expo start --web --port 8085
```

After implementation changes:

```powershell
npx expo lint
npx tsc --noEmit
```

The simplified-screen pass passed lint, TypeScript and `npx expo export --platform web`. Playwright reviewed the local preview at 375 x 812, 1280 x 900 and 812 x 375, including reduced-motion rendering. Interaction checks covered Home-to-joint navigation, running/walking/landing switching, reference and recording sheets, month exclusions, unmonitored joints, session details, and Demo Lab dropout/insufficient history. Console showed no app errors; Reanimated's expected reduced-motion development warning was present. Native iOS/Android, large system text and release-build motion remain unverified. Screenshots and temporary interaction checks are outside the repository.

### Windows generated-route cache issue

Expo's watcher intermittently generates incorrect `.expo/types/router.d.ts` paths on Windows after edits, such as `/home/index` instead of `/home` and paths outside the route directory. Do not change valid routes or cast links to suppress this. Regenerate ignored declarations, then rerun TypeScript:

```powershell
node -e "process.env.EXPO_ROUTER_APP_ROOT=require('node:path').resolve('src/app'); require('./node_modules/expo/node_modules/@expo/cli/node_modules/@expo/router-server/build/typed-routes').regenerateDeclarations('.expo/types');"
npx tsc --noEmit
```

The internal tooling path is specific to the installed SDK 57 layout; check it if Expo changes. Do not commit `.expo` files or patch dependencies as a workaround.

## Resuming work

### Knee guide

The guide covers knee function, conceptual thigh/shin IMUs and pressure insoles,
injury mechanisms, and general actions to help reduce injury risk. Copy is based
on AAOS [Common Knee Injuries](https://www.orthoinfo.org/diseases--conditions/common-knee-injuries/)
and [Safe Exercise](https://www.orthoinfo.org/staying-healthy/safe-exercise/), plus
the repository measurement contract. It does not promise injury prevention or
present foot loading as internal knee force. All four supplied illustrations
are conceptual AI artwork, not validated anatomy, placement instructions, or
personalized exercise prescriptions.

Completion or Skip sets `kintra.knee-guide.v1.completed` to `true` using Expo's
`expo-sqlite/localStorage/install` preference API on native and browser
localStorage on web. No measurement data is stored by this feature. If storage
is unavailable, entry still works and completion lasts for the current launch;
the guide may recur on a later launch. Get started now always opens the guide for
demonstrations, regardless of this preference. The welcome screen remains available.
Home's Knee guide link always allows replay. Change the versioned key if a later
guide needs to be shown again. The preference remains separate from measurement data.

The carousel uses native ScrollView paging, updates progress after scrolling
settles, and disables programmatic scroll animation with reduced motion.
Illustrations use `contain`, offscreen slides are hidden from accessibility,
slide text can scroll at small heights/large text sizes, and all actions remain
outside the slide scroll area. A failed image leaves the copy and navigation
available with an explicit illustration-unavailable message.

Verification: lint and TypeScript passed, as did production exports for web,
iOS and Android. Playwright tested the exported web app at 375 x 812,
1280 x 900 and 812 x 375: all four slides/images, Next/Back/dots, horizontal
paging, orientation alignment, completion/Skip persistence and replay passed.
Reduced motion, doubled web copy, blocked local storage and failed-image
fallback also passed, with no JavaScript runtime errors. Native swipe,
screen-reader behavior, persistent storage on a physical device and native
Dynamic Type still require device testing. Temporary QA scripts/screenshots
and native bundles are outside the repository.

### Demo setup and Home feedback

Setup remains a local walkthrough. Continue never waits for simulated time,
movement counts, sensor states, or an activity choice: it completes that demo
step and preserves a chosen movement/activity. Strength training is the visible
default activity. Timers are optional. Back and close retain progress for this
launch; reloading the app resets setup. Completion reveals Home's example history.

`src/data/home-bend-demo.ts` generates six complete bends: the first three at
85 degrees and the last three at 65 degrees, plus three earlier matching sets
at 88, 85, and 82 degrees. It uses the Live simulation and
feedback engine, with consistent angle/gyro/gravity scaling. The 85-degree baseline
is the median of the prior set medians. These examples are never written into
the user's saved Live sets. Completing setup does not learn a real baseline.

`home-movement-feedback.tsx` leads with shallower later bends, two schematic leg
positions (blue early, orange late, with a faded early-position outline), and six
rep markers. The first/last group medians differ by 20 degrees; whole-set typical
range is 75 degrees. The earlier-set reference remains 85 degrees and is explained
in the evidence sheet, alongside per-rep measurements.

The intentional-change check-in has planned and unexpected branches. Unexpected
changes suggest checking fit and repeating comfortable bends with the same setup.
An optional self-reported tired check-in switches to a rest suggestion, consistent
with [AAOS Safe Exercise](https://www.orthoinfo.org/staying-healthy/safe-exercise/).
Answers change suggestions without changing measurements or diagnosing fatigue
or injury. They last for the current launch and remain selected across tabs.
The comparison is descriptive; neither the reference nor its deviation is a
validated exercise target or injury threshold. Setup/review stays a compact action.

Browser verification covered all four images, no-wait setup, Home before/after,
six-bend evidence and Live navigation, and Get started after prior completion,
at 375 x 812, 1280 x 900, and 812 x 375 with reduced motion and no page errors.
The story pass verified exact early/late values, all check-in branches, checked
semantics, six-rep evidence, and retained context after visiting Live. Eight
feedback regression tests and independent fixture arithmetic checks passed.
TypeScript, lint, and web/iOS exports passed. Physical iPhone interaction,
VoiceOver, and native text scaling still require device testing.

### Generated landing references

Run `python -B scripts/run_baseline_demo.py` from the repository root to refresh
`src/data/baseline-results.json`. `learned-baselines.ts` exposes the generated
results, and `landing-baseline.tsx` displays them on Trends and monitored knee
detail when Landings is selected. Those compact views use Athlete A, balanced
evaluation and five reference sessions. The Demo Lab controls switch among three
synthetic participant histories, thirteen held-out evaluation scenarios, both sides,
and 3/5/10/20 reference sessions; selections affect the Lab only. The Lab also
includes the activity-confirmation demonstration and Python-generated insights. History & quality
shows session medians, MAD, exclusions, and descriptive comparisons. Python is
the only learner; the app consumes frozen snapshots offline. Running/walking
charts have no learned reference. See `../docs/baseline-demo.md` for assumptions.

The user approved the current look, blue comparison accents, and horizontal activity cards. Continue from this design and keep changes small. Remaining work includes native safe-area/device checks, branded icon/splash assets, and real data/device integration when requested. No deployment or app-store setup is complete.

Branch: `gael`. Remote: `origin`, `https://github.com/GG1627/dte-designathon-2026.git`. Earlier implementation, visual polish, and activity-card commits were pushed successfully.

### Simulated Live tab

`/live` is available in the native and web tab bars. It starts paused and offers
slow knee bends, repeated flexion, standing still, and changing-depth bends,
plus Play/Pause, Zero knee, Reset, and raw IMU readings behind Reading details.
Switching presets resets playback and
the display offset. Playback advances only while the tab and app are active.
The diagram interpolates sensor angles with Reanimated; reduced motion disables
interpolation. All values are labeled simulated. Knee-bend sets have separate
local history; they do not update the existing running/walking/landing demo data.

`src/data/live-simulation.ts` defines `LiveSample`: source, sequence, milliseconds,
and each segment's display angle, acceleration in m/s², gyro in rad/s, and validity.
The UI converts raw values to g and degrees/s to match the teammate's serial viewer.
The 20 Hz generator models idealized gravity and X-axis rotation; it has no noise
or linear acceleration. Zero knee is only a display offset, not calibration.

Start set captures up to five minutes of simulated samples. Finish set presents
a descriptive takeaway and next step before numbers. Typical range, rep duration,
range variation, and the takeaway open evidence sheets with per-rep angles,
time to peak, angular speed/acceleration, and the calculation rules. Optional
depth/pace targets come from the user's exercise plan. Setup and effort check-ins
add context; a changed setup blocks the usual comparison.

`src/data/knee-feedback.ts` is dependency-free and segments complete bends without
crossing invalid samples, sequence gaps, or timestamp breaks. Partial edges are
excluded. Its 6-degree and 0.4-second segmentation gates are prototype engineering
rules, not exercise recommendations. Hardware/mixed sources remain unsupported
for exercise interpretation until calibration and angle estimation are validated.
The rules describe changes without diagnosing fatigue, injury, or their cause.

Save set stores up to 30 summaries using the existing native/web localStorage
setup under `kintra.simulated-knee-bends.v1`; raw samples are not persisted.
Saving is explicit and failures do not claim success. Saved check-ins are read-only.
References require three earlier matching sets with at least three complete bends,
confirmed planned setup, the same preset/target/version/source, and valid data.
The reference is the median of up to five session medians; current/future sets
are excluded. These are demo sufficiency rules, not validated reference thresholds.

There is no Bluetooth transport, device permission, raw export, or Python
execution in this screen. A future serial replay/BLE decoder can produce the same
display contract after firmware units, timing, framing, and angle estimation are
confirmed. The existing canonical hardware adapter still requires its own quality
and calibration fields; `LiveSample` alone is not a valid analysis recording.

Verification: TypeScript, lint, web and iOS bundle exports, browser playback/presets/zero/reset/raw
readings, reduced motion, mobile/desktop layout, and tab navigation passed. Mathematical checks
confirmed gravity magnitude, angle bounds, and gyro/angle derivative consistency.
Feedback verification: eight regression tests cover complete/partial/stationary
bends, changing depth, invalid/gapped/reversed timestamps, nonfinite sensor values,
hardware provenance, context/reference exclusions, and user targets. Run
`node --experimental-strip-types tests/knee-feedback.test.mjs` from `rn-app`.
TypeScript, lint, and web/iOS exports passed. Browser checks covered capture/review,
tappable details, target validation, setup priority, save/reload, reference matching,
blocked-storage fallback, and mobile/desktop layout with no runtime errors.
Native controls, VoiceOver, persistent storage, and motion performance still require
physical iPhone testing; browser checks do not establish native device behavior.

The parallel React/Vite serial website has a coordination handoff at
`../docs/serial-web-handoff.md`. Reuse the pure sample/feedback contracts and keep
simulated and hardware provenance distinct.
