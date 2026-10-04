# Human-in-the-loop activity context

Kintra's prototype separates **detected movement** from **confirmed activity**:

```text
Timestamped processed knee and plantar-force signals
  → structured episode segmentation
  → descriptive movement-pattern features
  → broad movement candidate
  → athlete confirmation/correction
  → confirmed sport/activity context
  → compatible personal reference
  → comparison and descriptive insight
```

This is a deterministic **movement-pattern candidate detector**, not an AI sport
classifier or a validated activity-recognition system. No probabilities, ML,
GPS, clinical thresholds, action recommendations, or injury/fatigue inference
are provided. Walking-like classification is deferred; ambiguous motion remains
`unclassified`. Above/below plantar-contact threshold describes pressure support,
not independently established flight or ground-reaction force.

## Actual signals, features, and rules

`scripts/activity_context.py` reads only `samples` and nominal sampling rate.
It does not read activity/session names, annotations, phases, programmed scales,
or ground truth. It uses processed knee flexion, gyro-derived knee velocity,
plantar normal force, timestamps, sequences, and signal quality. Angular
acceleration is not used. Original measurements and audited biomechanical metric
calculations remain unchanged.

Active samples are joined into an episode until a long quiet gap. One neighbor
sample is retained at either edge so onset/offset transitions are visible.
Within an episode, complete contacts have both a below-to-above threshold onset
and an above-to-below threshold offset. Contacts truncated at a boundary are
excluded. Features include complete per-side contact count, duration, median
within-contact knee excursion, median peak absolute velocity, median contact
time, bilateral onset pair count, per-leg/bilateral non-contact intervals,
bilateral support fraction, onset interval CV, and knee repetition count.
Onset interval CV is a computed timing descriptor, separate from the unestablished
`measurement_reliability.cv_percent` field, which remains null.
Velocity crossings near a flexion peak count candidate knee repetitions only
when excursion from the episode minimum is substantial.

- **Repeated jump/landing:** at least three complete contacts on each side,
  three bilateral onset pairs, substantial excursion on both sides, and complete
  per-leg and bilateral non-contact intervals. A jump remains only a candidate.
- **Running-like:** sustained complete contacts, substantial bilateral knee
  excursion, short contacts, regular onset intervals, and alternating sides with
  separated onsets. Simultaneous bilateral landing onsets do not satisfy it.
- **Squat-like:** repeated substantial knee excursions with sustained bilateral
  support and no discrete complete contact onsets in the episode.
- **Low activity:** small excursion and low peak velocity together.
- **Unclassified:** all other patterns, insufficient signal quality, or gaps.

All boundaries below are `DetectorRules` engineering/demo defaults, require
validation, and do not establish physiological categories:

| Default | Purpose |
| --- | --- |
| 20 N contact threshold | Reuse Kintra's existing plantar-contact definition |
| 5 deg/s active velocity | Episode activation and suppression of tiny peak crossings |
| 3 s quiet gap | Keep nearby repetitions in an episode; split separated bouts |
| 3 repetitions | Require repetition rather than label a single contact; running requires at least 6 alternating onsets |
| 15° bilateral excursion | Require substantial motion in combination with contact/timing patterns |
| 3° low-activity excursion | Together with low velocity, distinguish near-static samples from ambiguous motion |
| 0.1 s minimum non-contact | Require separated contacts on each side and complete bilateral low-force intervals |
| 0.1 s bilateral onset tolerance | Pair near-simultaneous contacts; running onsets must be separated by more than this |
| 0.35 s maximum running contact | Require short contacts in addition to alternation/regularity |
| 0.2 maximum onset interval CV | Descriptive timing-regularity rule, not a confidence probability |
| 0.95 bilateral support fraction | Require sustained support for the squat-like candidate |
| 1e-8 s timestamp tolerance | Reuse conservative nominal interval and packet alignment tolerance |
| 1 neighbor frame at each edge | Preserve contact transition evidence at segmented boundaries |

At least two finite timestamped frames and a positive declared sampling rate are
required. Sequence gaps, timing mismatch, negative/missing/nonfinite force,
missing angle/velocity, or invalid dependent quality produce `unclassified` with
null features. No interpolation or missing-to-zero replacement occurs. This
first version rejects the entire recording for a signal fault rather than
attempting to certify unaffected episodes.

## Confirmation/provenance contract

Detection exports versioned episodes with `episode_id`, bounds,
`detected_movement`, `detector_status`, descriptive `features`, suggested
`candidate_activities`, and an initially unconfirmed `confirmation`:

```json
{"status":"unconfirmed","confirmed_activity":null,"source":"detector_only"}
```

Selection produces, for example:

```json
{"status":"confirmed","confirmed_activity":"basketball_training","source":"user_confirmed"}
```

Trusted sources are `user_confirmed`, `user_corrected`, and `manually_selected`.
A correction preserves detector class, features, and measurements, and appends
prior confirmation to `confirmation_history`. `detector_version` and
`activity_taxonomy_version` remain explicit. Suggested activities are interface
choices, not inferred sports. The non-exhaustive activity list includes
basketball, volleyball, soccer, running, plyometrics, strength training,
rehabilitation session, and other; nonempty custom labels are also supported.

`with_activity_confirmation` returns a copy and alters context/provenance only.
It can rematch already-extracted metrics without recomputing them. A whole-session
selection applies to all its episodes. Conflicting or unconfirmed episode labels
cannot authorize a whole-session reference; mixed-activity episode-level metric
comparison is future work.

`baseline_simulation.context` obtains the activity key from trusted confirmation,
not detector output or the original recording's `activity` label. Fitting excludes
unconfirmed sessions from eligible reference history even when their legacy
context happens to match. Current-session comparison retains descriptive values
but produces null differences with `activity_confirmation_required`. The app says:
“Confirm the activity to compare this session with your personal reference.”
Participant, joint, side, configuration/geometry/acquisition context, and
processing compatibility checks remain unchanged. Comparison also requires trusted
activity provenance for every contributing historical session; older fitted artifacts
without it report `reference_activity_confirmation_required` rather than being
automatically trusted. The reference method version is now `session-median-mad/1.2.0`.
Mismatched confirmed activities
are incompatible. References remain frozen.

Legacy synthetic reference/history adapters now explicitly record their declared
bilateral-landing task as `manually_selected`. This is a scripted demo assumption,
not a claim that real athlete confirmation exists. The old task-history explorer
remains labeled separately from the new sport-confirmation recording. Detection
never automatically calls these adapters or grants itself trusted provenance.
For real ingestion, trusted source fields would require authenticated user actions;
a JSON source string alone is not an authentication mechanism.

## Judge demo

```sh
python3 -B scripts/run_activity_context_demo.py
python3 -B scripts/run_baseline_demo.py
python3 -B scripts/run_baseline_demo.py --sensor-pipeline
```

The first command processes both five reference sessions and one held-out
three-landing session through the existing raw-IMU/Madgwick pipeline. Basketball
history is explicitly manually selected in this synthetic example. The current
recording initially remains detector-only. Identical current measurements then
produce these Python-generated choices:

| Choice | Result |
| --- | --- |
| Unconfirmed | Session metrics visible; comparison blocked |
| Basketball | Five compatible sessions, 30 reference events per side/metric; provisional reference available |
| Volleyball | No compatible volleyball history; basketball reference is not borrowed |
| Other choices/corrections | Their own activity context; no unrelated history substituted |

Results are saved to `data/baseline_demo/activity_context/demo.json` and bundled
in `rn-app/src/data/activity-context-results.json`. The knee/Trends area exposes
buttons to select these offline outcomes. React does not implement detection,
reference fitting, or matching. UI choice is local and not persisted as a live
athlete record; the generated JSON demonstrates the storage contract. Clear the
choice to return to unconfirmed. Neither choice updates historical reference
statistics or rewrites measurements.

“The sensors suggest the movement pattern. The athlete identifies the real-world
sport/context. Kintra uses both.” This protects context integrity without claiming
perfect sport recognition.

## Evidence boundaries and future validation

Published wearable-IMU research investigates movement recognition from combinations
of acceleration, angular velocity, timing, and related features. Running and
jumping primitives can occur in multiple sports; mechanically similar signals
alone do not establish what sport an athlete intended. Human confirmation is the
conservative product choice here, not a demonstrated classifier performance claim.

**TODO — citation verification:** before adding formal movement-recognition
citations, verify appropriate peer-reviewed sources and their sensor setups,
populations, validation protocols, and relevance to this knee/insole detector.
Existing monitoring/reliability sources in the other documents do not validate
these recognition heuristics. No new author/title/DOI is invented here.

Needed next: real annotated recordings across people and sessions, sensor fit and
calibration checks, noise/dropout policies, boundary/false-positive evaluation,
activity taxonomy testing, and persistent authenticated confirmation handling.
Biomechanical reference metrics still use the existing annotated landing windows;
detected episodes do not replace those audited metric definitions.
The current deterministic detector is a prototype architecture, not a validated
classifier. It does not establish hardware accuracy, clinical meaning, or a
scientifically sufficient personal reference.
