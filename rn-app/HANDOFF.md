# Kintra app handoff

Updated October 3, 2026. Read [PRODUCT_CONTEXT.md](../PRODUCT_CONTEXT.md) before changing product behavior and follow the repository and app `AGENTS.md` instructions.

## Current state

Kintra names both the wearable platform and companion app. This is a designathon UI prototype built with Expo SDK 57, React Native, and Expo Router. It uses synthetic observations, not live sensor readings.

| Route | Implemented experience |
| --- | --- |
| `/` | Branded welcome, K mark, "Your movement, understood." Get started opens `/onboarding` until the guide is completed/skipped, then `/home`. |
| `/onboarding` | Four illustrated knee-education slides; swipe, Next, Back, tappable progress dots, Skip and Explore the app. Replay through Home's Knee guide link. |
| `/home` | Both monitored joints visible first, latest activity card, quiet daily duration summary, device sheet. |
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
the guide may recur on a later launch. The welcome screen remains available.
Home's Knee guide link always allows replay. Change the versioned key if a later
guide needs to be shown again. Clearing this key and reloading resets the first-visit flow.

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
