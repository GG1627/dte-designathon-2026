# Kintra app handoff

Updated October 3, 2026. Read [PRODUCT_CONTEXT.md](../PRODUCT_CONTEXT.md) before changing product behavior and follow the repository and app `AGENTS.md` instructions.

## Current state

Kintra names both the wearable platform and companion app. This is a designathon UI prototype built with Expo SDK 57, React Native, and Expo Router. It uses synthetic observations, not live sensor readings.

| Route | Implemented experience |
| --- | --- |
| `/` | Branded welcome, K mark, "Your movement, understood." Get started replaces this route with `/home`. |
| `/home` | Recorded minutes, coverage ring, running/walking duration bars, joint ROM and cycles, reference scales, insight, horizontal activity cards. |
| `/trends` | Joint/week/month/activity filters, movement-range chart, reference band, period comparisons, exact-data sheet, recordings and empty states. |
| `/joints` | Monitored/unmonitored joints, simulated connection status, links to details. |
| `/joint/[id]` | Measurements, baseline context, device/placement sheet, sample functional assessment information. |
| `/session/[id]` | Recording summary and measurement context. |

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
- The ring is valid recording coverage; duration bars show shares of recorded time; joint scales show degrees and a labeled personal reference. These are not goal completion or health scores.
- Orange shows observed movement; blue shows the reference. Developing baselines have no reference band.
- Filtered charts have a short fade/small movement with reduced-motion support: Reanimated on native, CSS on web. Tabs retain platform behavior.
- ScrollView automatic adjustment owns top insets. Adding manual `insets.top` padding as well caused excess space above headers.
- `Link asChild` did not forward callback Pressable styles correctly in this preview. Joint/activity cards use static styles to keep their horizontal layouts intact.

## Data and limitations

- `src/data/demo.ts` contains deterministic samples anchored to October 3, 2026; they do not advance with the actual date.
- Right knee and ankle are monitored. Other joints have no data. The ankle baseline is developing.
- The lower-leg pod is shared by knee and ankle; simulating it offline affects both.
- Connection toggles/checklist confirmations live in `demo-provider.tsx` memory and reset on reload.
- Trends compare the same joint/activity and exclude recordings below 80% valid coverage. References are illustrative.
- No Bluetooth, backend, authentication, persistent storage, hardware calibration, or validated inference pipeline is connected.
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

Lint and TypeScript passed after the latest activity-card fix. Home and week/month Trends were visually reviewed in a 375 x 812 browser preview; recent-activity cards were reviewed after their fix. Native iOS/Android behavior and release-build motion have not been verified. No automated interaction test suite was added.

### Windows generated-route cache issue

Expo's watcher intermittently generates incorrect `.expo/types/router.d.ts` paths on Windows after edits, such as `/home/index` instead of `/home` and paths outside the route directory. Do not change valid routes or cast links to suppress this. Regenerate ignored declarations, then rerun TypeScript:

```powershell
node -e "process.env.EXPO_ROUTER_APP_ROOT=require('node:path').resolve('src/app'); require('./node_modules/expo/node_modules/@expo/cli/node_modules/@expo/router-server/build/typed-routes').regenerateDeclarations('.expo/types');"
npx tsc --noEmit
```

The internal tooling path is specific to the installed SDK 57 layout; check it if Expo changes. Do not commit `.expo` files or patch dependencies as a workaround.

## Resuming work

The user approved the current look, blue comparison accents, and horizontal activity cards. Continue from this design and keep changes small. Remaining work includes native safe-area/device checks, branded icon/splash assets, and real data/device integration when requested. No deployment or app-store setup is complete.

Branch: `gael`. Remote: `origin`, `https://github.com/GG1627/dte-designathon-2026.git`. Earlier implementation, visual polish, and activity-card commits were pushed successfully.
