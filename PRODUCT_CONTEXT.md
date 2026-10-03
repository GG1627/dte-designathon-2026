# Product Context: A Personalized Wearable Platform for Joint Mechanics

> Read this document before proposing features, designing screens, choosing architecture, or implementing this project. It describes the product vision and the reasoning behind it. It is not a claim that the hardware, algorithms, or medical outcomes have already been validated.

**Working shorthand:** “WHOOP for joints.”

**Product name:** Kintra. The wearable platform and companion app share this name.

**Current stage:** Designathon concept with a working mobile UI, synthetic personal-baseline learner, and ideal raw-IMU/Madgwick software experiment. Hardware and real-sensor accuracy are not validated. See [pipeline integration](docs/pipeline-integration.md) and [the app handoff](rn-app/HANDOFF.md) for implementation boundaries and design decisions.

## 1. The idea in two sentences

We are creating a modular wearable system that learns a person's individual joint mechanics, tracks the movement and workload of selected joints, and helps them understand changes in their function over time. Through wearable measurements, personal baselines, and potentially periodic strength assessments, the system translates biomechanical data into understandable information about joint workload, functional capacity, and recovery-related trends.

## 2. Why this product should exist

Athletes can track steps, workouts, heart rate, sleep, and overall exertion, but those summaries do not necessarily explain what is happening at a particular knee, ankle, elbow, or shoulder.

Someone might feel generally recovered while noticing that one knee is moving differently. Two training sessions might produce similar cardiovascular effort while placing different demands on an elbow. A person returning to training might want to understand whether their range of motion and measured strength are improving, rather than relying entirely on memory or a vague sense of how they feel.

Our product aims to make these local changes easier to see and discuss. It creates a longitudinal profile for each monitored joint, with the person serving as their own reference.

The central questions are:

- What did I ask this joint to do today?
- How did it move during that activity?
- Is its behavior changing relative to my usual pattern?
- What do repeatable assessments tell me about its current function?
- Which measurements explain the change?

The purpose is to support awareness and better-informed conversations and training decisions. Demonstrating actual injury reduction would require additional research; it is a desired outcome, not an established property of this concept.

## 3. What “WHOOP for joints” means

The analogy describes the experience: ongoing monitoring, learning the individual, showing understandable summaries, and helping someone follow trends over time. It does not mean copying WHOOP's interface, branding, proprietary formulas, or exact scoring scale.

Our focus is localized biomechanics. A user's right knee and left knee can have separate profiles, and their elbow can have an entirely different activity history and assessment protocol.

The differentiating idea is the combination of:

1. Joint-specific monitoring during activity.
2. An individual baseline that develops over time.
3. Context-aware comparisons between similar activities or assessments.
4. Optional standardized assessments of function and strength.
5. Explanations that connect a summary back to its supporting measurements.

“Learns from you” must mean more than inserting the user's name into a dashboard. It means the interpretation depends on their own recorded history, joint, activity, measurement conditions, and data quality.

## 4. Product scope: a platform for multiple joints

The product vision includes the major joints, especially knees, ankles, elbows, and shoulders. A knee can be the first implementation or worked example without becoming the identity of the entire product.

The physical concept is a family of joint-specific attachments built around reusable sensing electronics. A common pod design could fit different housings, while the attachment geometry and calibration remain specific to the anatomy.

| Joint | Conceptual attachment | Example motion focus | Important design consideration |
| --- | --- | --- | --- |
| Knee | Low-profile thigh and shin mounts, potentially integrated into a sleeve | Flexion/extension, ROM, repetition patterns | Stable placement across two segments without unnecessarily restricting motion |
| Ankle | Lower-leg attachment plus foot or shoe attachment | Dorsiflexion/plantarflexion and selected inversion/eversion metrics | A lower-leg cuff alone does not establish foot orientation |
| Elbow | Upper-arm and forearm attachments | Flexion/extension, movement speed, repetition exposure | Motion does not reveal the weight held in the hand |
| Shoulder | Upper-arm attachment plus torso reference | Arm elevation and upper-arm orientation relative to torso | This is not a direct measurement of the full scapular or glenohumeral motion |

The athlete wears the modules relevant to their activity. They do not need to wear every module at once.

Examples include a runner monitoring selected lower-limb joints, a pitcher monitoring elbow and shoulder mechanics, and a volleyball player monitoring a combination of upper- and lower-limb joints.

**Important architecture clarification:** Reusing one pod design does not imply that one physical sensor measures every joint simultaneously. Relative joint motion generally requires information about both adjacent body segments. Bilateral monitoring also requires suitable sensors on both sides, unless the product uses a separate standardized assessment procedure.

The same hardware family can be shared across configurations. The biomechanics model, baseline, assessment, and interpretation cannot be assumed identical across all joints.

## 5. Who the product is for

The primary envisioned user is an athlete or physically active person who wants to understand joint-specific demands and functional changes over time.

They may be interested in:

- Understanding a particular joint that receives repeated training exposure.
- Seeing how movement patterns evolve throughout a session.
- Comparing equivalent activities across days or weeks.
- Tracking repeatable assessments alongside activity history.
- Sharing an understandable summary with a coach or clinician.

Coaches and clinicians are potential secondary users. Rehabilitation is a possible future use case, but it does not automatically make the prototype a validated rehabilitation tool or return-to-sport assessment.

Do not silently shift the product into a clinic-only device, a generic workout tracker, or a product only for injured people. Those would be separate product decisions.

## 6. The three product pillars

### 6.1 Joint Load: what the joint has been asked to do

Joint Load represents accumulated activity exposure associated with the monitored joint.

Initial inputs could include movement count, activity duration, motion range, speed-related features, segment acceleration events, and time spent in selected movement ranges. More advanced versions could incorporate estimated joint moments when suitable force information and a validated model are available.

An early score should be described as an **exposure index** or a **load-related estimate**. It should not imply that motion measurements directly reveal internal tissue stress.

The useful experience is being able to answer: “Was this a typical day for this joint, or did I accumulate substantially more exposure than usual?”

### 6.2 Joint Capacity: what repeatable assessments show

Capacity describes measured functional performance under defined conditions, potentially including ROM, force or torque in a standardized strength test, and consistency across repetitions.

Continuous movement monitoring alone does not measure maximum strength. A strength measurement requires a known resistance or reaction force and an appropriate mechanical setup.

Capacity should remain a profile of measured capabilities rather than a fabricated universal percentage. For example, the product could show the most recent knee-extension assessment compared with the same person's previous assessments at the same joint angle and setup.

Do not interpret a higher assessed capacity as proof that a specific training exposure is safe. A comparison between measured capacity and recent demand is an exploratory product direction that needs its own validation.

### 6.3 Recovery-related trends: how function is changing

The product should help someone follow whether repeatable functional measurements are returning toward their usual range after training.

Potential inputs include a standardized movement check, changes in ROM, measured assessment performance, activity-specific asymmetry, recent exposure, and optional self-reported soreness or stiffness.

These signals do not directly measure cartilage healing, ligament recovery, or tissue readiness. The initial experience should emphasize **functional trends** and **changes from baseline**. A validated readiness or recovery score is a longer-term research goal.

The design can accommodate these three pillars without pretending all three are equally supported by the first prototype.

## 7. Measurement vocabulary and boundaries

Keep the following distinctions consistent in code, UI, data schemas, presentations, and documentation.

| Term | Meaning in this project |
| --- | --- |
| Raw measurement | A calibrated sensor output, such as angular velocity or measured force |
| Derived metric | A value calculated from signals, such as joint ROM or repetition count |
| Model estimate | A result that depends on additional assumptions or a learned model, such as estimated net joint moment |
| Product score | An engineered summary of chosen inputs, not a sensor reading |
| Personal baseline | A person's reference distribution for a specific joint, activity or test, and measurement configuration |
| Functional trend | A change in measured performance over time |
| Joint health | A broad physiological concept that the wearable cannot directly quantify from motion alone |

Mechanical strain technically means deformation relative to original length. A sleeve strain sensor measures deformation of its sensing element. It does not directly measure strain inside a ligament.

An accelerometer measures specific force at its mounting location. It is not a force plate, and an acceleration peak is not automatically a joint-impact force in newtons.

Net joint moment, internal joint contact force, and individual ligament force are different quantities. Even a well-estimated net moment is not a direct measurement of ACL force or cartilage loading.

## 8. What the system could track

The table describes conceptual capabilities, not implemented features or guaranteed accuracy.

| Metric | Typical units | Input or method | Interpretation limit |
| --- | --- | --- | --- |
| Joint angle | Degrees | Calibrated relative segment orientations or an instrumented mechanism | Accuracy depends on alignment, anatomy, fit, and movement |
| Range of motion | Degrees | Angle range within a defined activity or assessment | Task ROM is not necessarily maximum available ROM |
| Segment angular velocity | Degrees/second or radians/second | Gyroscope | Sensor axes must be mapped to a useful frame |
| Joint angular velocity | Degrees/second or radians/second | Relative kinematics or differentiated joint angle | A single segment's gyro value is not automatically joint angular velocity |
| Angular acceleration | Degrees/second² or radians/second² | Filtered differentiation | Derivatives amplify noise |
| Segment acceleration | g or meters/second² | Accelerometer, with gravity treatment defined | Represents acceleration-related signals, not direct joint force |
| Repetition/event count | Count | Event detection on motion signals | Depends on activity and detection quality |
| Activity duration | Seconds or minutes | Session segmentation | Unrecorded time must remain visible |
| Movement consistency | Metric-dependent | Repeat-to-repeat variation in defined features | Variation is not inherently harmful |
| Time in selected movement ranges | Seconds | Angle and event rules | No universal dangerous-angle threshold is assumed |
| Left/right asymmetry | Percent or physical-unit difference | Comparable bilateral measurements | Specify the feature and formula; motion asymmetry is not load asymmetry |
| Assessed force | Newtons | Calibrated load cell in a defined test fixture | Measures force through that fixture |
| Assessed torque | Newton-meters | Force and perpendicular lever arm, or calibrated torque sensor | Requires geometry, stabilization, and load-path characterization |
| Estimated net joint moment | Newton-meters, possibly normalized by body mass | Kinematics, external loads, body model, or validated prediction model | Research-stage capability for supported tasks |
| Cumulative exposure | Defined index units, or moment-time units if appropriate | Aggregation across valid events or time | Not a direct tissue-damage measure |
| Perceived soreness/stiffness | User-reported scale | Optional check-in | Subjective input, distinct from sensor measurements |

Optional research inputs include surface EMG, pressure sensing, textile deformation sensing, temperature, bioimpedance, and joint acoustics. These are possible extensions, not mandatory hardware or established diagnostic features.

## 9. Conceptual hardware architecture

### 9.1 The shared sensor platform

A reusable electronics design could contain a six-axis IMU, a low-power processor with Bluetooth communication, a rechargeable power system, and local buffering. Sensor identification, timestamps, calibration metadata, and quality checks are part of the architecture.

Optional external inputs could support an instrumented assessment accessory or other sensors. Component selection is open; do not invent an existing board layout, battery life, waterproof rating, size, or bill of materials.

### 9.2 Joint-specific attachments

The wearable design should establish repeatable sensor placement, keep the device secure during activity, and accommodate the movement of the relevant joint.

Useful mechanical design questions include:

- Can the wearer attach it consistently without specialist help?
- Does the pod have a keyed orientation or clear placement reference?
- Can the mount resist slipping without excessive pressure?
- Does the attachment interfere with sport equipment or normal motion?
- Can electronics detach so the textile portion can be cleaned?
- Can different body sizes be accommodated?
- Can the system detect or communicate a poor fit?

The physical design matters because movement between a sensor, clothing, skin, and the underlying body segment can distort measurements. Attractive geometry alone is not enough; fit and repeatability are part of the sensing system.

### 9.3 Separate daily monitoring from strength testing

The notes explore a wearable that moves freely during activity and supports periodic strength testing. Preserve this as a valuable design direction, but the mechanism remains unresolved.

A lightweight activity module does not automatically provide a safe reaction structure for substantial isometric forces. A separate stabilized accessory, rather than a lockable wearable hinge, may prove more realistic.

Any proposed test design must explain what resists the user's effort, where the load travels, how torque is calculated, and how mounting motion affects the result. Do not turn an illustrative maximum-effort test from brainstorming into a validated user protocol.

## 10. How the system learns from the user

### 10.1 Baselines belong to a context

A baseline should be associated with the person, joint, side, activity or standardized test, and relevant configuration.

Running, walking, throwing, and a controlled assessment should not be combined into one undifferentiated “normal” distribution. A change in exercise weight, footwear, mounting position, or test angle can affect interpretation.

The baseline is learned from sufficient comparable, valid observations. There is no established fixed number of onboarding days in this concept.

### 10.2 Compare changes, then explain them

For a stable feature and context, an initial implementation could compare a new value with a personal median or mean and a measure of variation.

Examples of descriptive outputs include:

- “Your movement range was lower than in recent comparable sessions.”
- “Your right-side repetition pattern differed more from the left than usual.”
- “This session included more rapid movement events than your recent sessions.”
- “Your latest standardized assessment was similar to your previous result.”

These describe observed changes. They do not establish an injury, a physiological cause, or a safe training limit.

### 10.3 Avoid learning away an important change

A system that immediately updates its baseline with every new measurement could normalize a persistent decline or a fit problem.

Consider keeping a historical reference and a more recent rolling baseline, with versioning and quality rules. A user should be able to see whether a change is relative to their original reference or recent pattern.

Do not assume every baseline is healthy. Personalization means learning what is usual, not proving that the usual pattern is ideal.

### 10.4 Data sufficiency is part of the experience

Before enough comparable data exists, say that the baseline is developing. If a joint was not recorded, show that it was not recorded. If a feature is unsupported by the connected hardware, explain that it is unavailable.

A missing measurement is not zero exposure, normal function, or full recovery.

## 11. Algorithm direction

The product does not require a large AI model for every step. The intended approach combines signal processing, biomechanical modeling where appropriate, and personalization.

### 11.1 Measurement pipeline

1. Collect timestamped raw measurements from the relevant sensors.
2. Convert readings to calibrated units and identify missing, clipped, or unreliable samples.
3. Synchronize devices and account for their segment placement.
4. Estimate orientation using an appropriate fusion method.
5. Apply sensor-to-segment calibration and calculate relative motion.
6. Segment the activity into meaningful events or windows.
7. Compute supported metrics and attach data-quality information.
8. Compare with an appropriate personal reference.
9. Aggregate valid observations into session and longitudinal summaries.
10. Explain the summary and preserve its provenance.

Candidate orientation methods include complementary filters, Madgwick/Mahony-style filters, or Kalman-filter approaches. Selecting one does not eliminate alignment errors, drift, soft-tissue motion, or ambiguity in complex joint rotations.

For general three-dimensional motion, use relative rotations with an explicit frame convention rather than blindly subtracting Euler-angle values. Under a convention where each rotation maps a calibrated segment frame into the world frame:

```text
R_relative = transpose(R_proximal) * R_distal
```

Extract anatomically defined angles from that relative rotation using the documented model. A single flexion angle can be a sensible first scope for a supported joint; full three-dimensional anatomy requires more care.

### 11.2 Event recognition

Start with manually selected activities and explainable event rules for supported motions. Thresholds, peak detection, and a small state machine can support a focused prototype.

Machine learning could later classify activities or improve event detection if appropriate labeled data exists. A model should be evaluated on users and sessions that were not used for training. Activity recognition accuracy is not evidence that the load estimate or readiness interpretation is correct.

### 11.3 Exposure summaries

An initial exposure index could aggregate dimensionless, context-normalized features across valid events. The weights and mapping to a displayed score would be engineering choices requiring evaluation.

```text
event_exposure = weighted combination of supported normalized features
session_exposure = sum of valid event exposures
```

Document the event definition, features, normalization, weights, and model version. Avoid double counting highly correlated inputs. Compare equivalent activities and account for recording coverage.

If a future system has a validated joint-moment estimate, it could calculate moment-time exposure:

```text
D = integral(abs(M(t)) dt)
```

This has units of N·m·s. It is an exposure summary, not accumulated injury or tissue damage. Nonlinear weighting of moment would change the units and interpretation and would need separate justification.

### 11.4 Force estimation is a separate capability

Two IMUs can support relative-motion estimation, but they do not fully determine external forces. Similar arm motions can occur while holding very different weights.

Inverse dynamics requires appropriate motion data, body-model parameters, and relevant external loads. Pressure insoles can contribute plantar normal-pressure information and a pressure-derived center of pressure, but a typical pressure-only insole does not capture the complete three-dimensional force and moment information of a force plate.

Research options include additional force sensing, constrained task models, or models trained against laboratory references. Do not imply that adding a pressure insole automatically solves full joint loading.

### 11.5 Personal anomaly detection

An initial baseline comparison can use robust percent changes and standardized deviations. A multivariable model is an optional later step.

For example, a Mahalanobis distance could consider correlated features together:

```text
d = sqrt((x - mu)^T * inverse(Sigma_regularized) * (x - mu))
```

This requires adequate comparable data and stable covariance estimation. The result indicates difference from a reference distribution, not injury probability or a direct health score.

### 11.6 Recovery and capacity inference

Do not invent a biological recovery equation or assume that yesterday's load determines today's readiness. Functional checks, subjective feedback, and activity history might support exploratory interpretations, but the relationship needs validation.

Longitudinal exposure is not itself a direct measure of tissue capacity. Acute/chronic summaries can be descriptive trends; they should not be treated as universal injury thresholds.

## 12. How this should shape the mobile app

The app is the interface to the product's story: individual joints, personal context, meaningful changes, and clear explanations. It should not become a collection of generic fitness statistics just because those screens are easy to build.

### 12.1 Information structure

Design around an athlete who can have multiple monitored joints and sides, several wearable devices, many activity sessions, and periodic assessments.

Keep these entities separate:

- **Person:** preferences, relevant profile information, and consent settings.
- **Joint instance:** anatomy and side, such as right elbow.
- **Hardware device:** physical pod identity and current placement.
- **Session:** activity, recording time, connected configuration, and coverage.
- **Assessment:** a defined protocol, conditions, and measured results.
- **Baseline:** context, source observations, and version.
- **Metric:** value, unit, source, quality, and calculation version.

A hardware pod can be reassigned to another attachment. Historical data must retain where it was worn at the time. The identity of a device is not the identity of the joint.

### 12.2 Useful app capabilities

The following are product-aligned opportunities, not a frozen screen specification:

| Capability | Why it belongs |
| --- | --- |
| Joint overview | Helps the athlete understand which joints have current data and notable changes |
| Joint detail | Connects workload, movement metrics, assessments, and history for one joint |
| Device setup and placement guidance | Supports repeatable attachment and reliable measurements |
| Baseline progress | Explains what the system has learned and what remains unknown |
| Activity recording and session summary | Gives exposure metrics the context they need |
| Standardized functional check | Supports comparable observations across time |
| Assessment history | Makes strength or ROM trends meaningful when the test setup is known |
| Optional soreness/stiffness check-in | Adds the user's experience while preserving its subjective source |
| Trend exploration | Allows comparisons across similar sessions or assessments |
| Explanation of a summary | Shows which measurements contributed and how trustworthy they are |
| Data export or sharing | Could support discussions with a coach or clinician |

An anatomical selector or body map could be useful, but it is a design option rather than a requirement. Screen count, navigation, visual identity, and technology stack remain open.

### 12.3 Score presentation

No numerical scale or production formula has been chosen. A 0–100 score, WHOOP-like scale, category label, or raw exposure summary should be selected based on clarity and evidence.

If a mockup uses illustrative scores, identify them as demo data. For example, “Joint Load 74” does not mean “74% healthy,” “74% damaged,” or “74% likely to be injured.”

A useful summary should answer:

1. What does this label mean?
2. Which measurements contributed?
3. Compared with which sessions or baseline?
4. How much valid recording supports it?
5. What information is missing?

### 12.4 Example interaction

An athlete selects their monitored right knee and starts a session. Afterward, the app shows recorded activity duration, supported movement metrics, and an exposure comparison with similar prior sessions. If the recorded motion pattern differs from the baseline, the app explains the specific change and the recording quality.

Later, the athlete completes a standardized functional check. The app stores it separately from the training session and compares it with previous checks under equivalent conditions. If a strength accessory was not used, the app does not fill in an imagined strength result.

The user can understand the change without studying raw sensor traces. Detailed data can remain available for people who want it.

### 12.5 Essential states

Design for new users, learning baselines, unsupported metrics, unmonitored joints, disconnected sensors, incomplete recordings, failed calibration, and incompatible assessments.

Distinguish an observed measurement, a model estimate, a user report, and a synthetic demonstration value. Show stale assessments with their dates. Avoid precise-looking scores when the supporting information is insufficient.

### 12.6 Tone and emotional experience

Use clear, calm language. The app should help people understand their patterns without treating ordinary variation as a diagnosis or creating anxiety through unexplained red warnings.

Do not reward accumulating more joint exposure as if it were always better. Do not imply that a reassuring score grants permission to train through pain. Explain observations in everyday terms, with physical units and technical details available where useful.

## 13. Novelty and product differentiation

Motion sensors, smart braces, dynamometers, and rehabilitation tracking already exist as technology categories. A sensor attached to a joint is not sufficient evidence of novelty.

The intended differentiation is the integrated experience: a reusable modular wearable platform, joint-specific mechanical design, ongoing monitoring, standardized functional checks, and a personal longitudinal model with understandable explanations.

Treat market uniqueness and patentability as research questions. Do not claim that no competitor exists or that the product is the first of its kind without a separate, current investigation.

The concept should earn its value through fit, repeatability, useful context, and interpretation rather than through the number of sensors or the use of the word AI.

## 14. Product principles

1. **Personalization is central.** Compare equivalent observations with the person's own history.
2. **The platform includes multiple joints.** A focused first implementation should support that larger vision.
3. **Hardware and interpretation work together.** Attachment quality affects the meaning of the data.
4. **Every output has provenance.** Know whether it was measured, derived, estimated, or reported.
5. **Useful explanations accompany summaries.** A number without context is insufficient.
6. **Unsupported information remains unavailable.** Missing values do not become reassuring defaults.
7. **Monitoring and assessment complement each other.** Movement exposure and strength are distinct capabilities.
8. **Claims follow validation.** Good motion measurements alone do not validate injury prediction or readiness.
9. **Everyday wearability matters.** The design should make repeated use practical.
10. **The user stays in control.** Treat detailed body and activity data as private and make sharing intentional.

## 15. What is settled and what remains open

| Topic | Current position |
| --- | --- |
| Core concept | A personalized wearable platform for joint mechanics and functional trends |
| Product analogy | WHOOP for joints, as an experience shorthand |
| Anatomical scope | Multiple major joints; knee, ankle, elbow, and shoulder are the main examples |
| Core differentiator | Learning the individual's joint- and activity-specific patterns over time |
| Physical direction | Shared sensing electronics with joint-specific attachments |
| Product outputs | Joint Load, Capacity, and recovery-related trends are the envisioned pillars |
| Direct tissue-health measurement | Not established by this concept |
| Strength assessment | Valuable potential extension; mechanical implementation and protocol unresolved |
| First supported joint/activity | Open; the knee is a possible starting point |
| Sensor count and exact components | Open |
| Optional pressure or EMG inputs | Open; not assumed necessary for every configuration |
| App stack and screen structure | Open |
| Score formula and scale | Open; no clinically validated formula supplied |
| Final product name | Open |
| Commercial or medical validation | Future work; not completed |

## 16. Instructions for Codex and future collaborators

When asked to understand or build this product:

- Use this document as product context, then follow the specific task the user gives.
- Preserve the multi-joint vision and the emphasis on learning the individual.
- Explain how proposed features serve that vision.
- Keep measurement capabilities consistent with the connected hardware and available data.
- Avoid inventing a finished algorithm, dataset, validation result, or hardware integration.
- Keep demonstration values distinguishable from real measurements.
- Treat feature ideas in this document as options unless explicitly described as settled.
- Do not make all optional research sensors prerequisites for a useful prototype.
- Do not silently turn functional-trend summaries into diagnostic or return-to-sport decisions.
- Prefer a coherent, understandable experience over displaying every conceivable metric.
- Keep hardware placement, calibration, supported activity, and data quality visible in the underlying architecture.
- Document assumptions when narrowing the first implementation to a particular joint or activity.

If asked to design the mobile app, begin with the athlete's questions and the available measurements. Propose a product-aligned experience rather than treating this as a generic fitness dashboard. If hardware integration is outside the current task, a well-labeled simulated experience can illustrate the product without implying that the sensing system is complete.

If asked to implement algorithms, separate signal processing, metric calculation, baseline comparison, and score mapping. Preserve raw inputs and model versions where practical so results can be understood and evaluated later.

## 17. Evidence and source boundaries

This document synthesizes the team's discussion and the supplied brainstorming notes in `Pasted text(2).txt`. The notes contain exploratory proposals and illustrative numbers; they are not a finalized technical specification. Specific numerical accuracy claims, medical thresholds, strength-test procedures, and readiness percentages from brainstorming have not been adopted as validated requirements.

Primary technical references consulted for the foundational distinctions:

- [WHOOP: How does WHOOP Strain work?](https://www.whoop.com/us/en/thelocker/how-does-whoop-strain-work-101/) explains its own product's exertion metric. Used for the experience analogy, not to derive our algorithm.
- [OpenSim: Getting Started with Inverse Dynamics](https://opensimconfluence.atlassian.net/wiki/spaces/OpenSim/pages/53090063) describes motion data, external loads, model inputs, and net joint torque outputs.
- [OpenSim: Joint Reactions Analysis](https://opensimconfluence.atlassian.net/wiki/spaces/OpenSim/pages/53089600) distinguishes inverse-dynamics outputs from modeled joint reactions.
- [Xsens MVN technical white paper](https://www.xsens.com/hubfs/Downloads/Whitepapers/MVN_Whitepaper.pdf) discusses inertial motion estimation, sensor-to-segment relationships, and soft-tissue effects.

These references support technical foundations. They do not validate this proposed product, its scores, its clinical usefulness, or its injury-prevention effect. Algorithms, app capabilities, and mechanical arrangements described above are proposed design directions unless stated otherwise.
