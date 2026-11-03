# Thermal learner development increment — 3 November 2026

This is an implemented **opt-in shadow candidate**, not a production learner
replacement or deployment approval. The PID, OpenTherm commands, safety logic,
weather compensation and actuator bindings are unchanged. Nothing was flashed.
Work starts at `47250224ef53c26aeb77e41d95967f718e74bc72`, preserving the newer
complete-candidate work after the requested `a7c299c` revision.

## Evidence and root causes

All five exports in `astra_thermal_model_history_exports.zip` were read. Source
hashes are in `evaluation/diagnosis_20261103.json` and `shadow_comparison.json`.
Raw household histories remain local under ignored `.build/data/`.

The November 3 file contains 50,142 rows and 74 entities. It has **no independent
raw room-temperature history for either room**. `sensor.climate_*_temp` is an EMA
diagnostic; it is not substituted for raw observations or scoring targets.

Cycle counts exclude the synthetic export-start state, invalid states, and one
duplicate `(q,t)` publication per room following an availability interruption.
The carried-in start state is used only to detect the first counter drop.

| Room | Unique cycles | Accepted | Rejected | Suspended | Baseline | Forecasts | Resets |
|---|---:|---:|---:|---:|---:|---:|---:|
| Stijn | 149 | 97 | 42 | 6 | 4 | 14 | 6 |
| Nick | 149 | 141 | 0 | 5 | 3 | 132 | 0 |

Stijn resets at 00:03:17, 02:23:18, 03:43:19, 04:38:20, 08:38:22 and
12:23:23 Netherlands time. The first reset closes a rejection run that started
before the export. The other five follow six consecutive rejected cycles.
Every reset is reported as `disturbance_rejected`, not an invalid-input reset.

For **26 of the 42 rejections**, the immediately preceding receipt-age diagnostic
(at most 30 seconds old) establishes that no raw room publication occurred in
the entire previous device observation interval, with a further 30-second margin.
The held input therefore has exactly zero measured change. Its rejection must
be **absolute model residual >1°C**, not measured rate >0.15°C/min. The cycle IDs
are retained in the diagnosis JSON. For the remaining 16, the export cannot
distinguish the rate and residual branches: the old cycle record merges them.
No independent raw reconstruction or exact historical coefficient trace is
claimed. New model details distinguish these branches directly.

The accepted cycles also overcount information: **27/97 Stijn** and **65/141 Nick**
use a room publication older than 15 minutes. Availability of a valid held state
does not make each five-minute poll an independent observation. The same value
can legitimately be available; the error is repeated estimator conditioning on
that same unconfirmed endpoint, followed by treating delayed changes as short
five-minute changes.

Nick's cycle `q=165` at **12:23:26.013 +01:00** records:

| Horizon | Forecast °C |
|---|---:|
| 15 minutes | 15.217697 |
| 30 minutes | 13.827486 |
| 60 minutes | 12.042380 |

Nick's valve command is zero throughout this export except explicit
unavailability. DHW suspensions within the period zero the reference radiator
state; subsequent zero valve drive keeps it zero. Thus this late curve obeys
`T(h)=E+(T(0)-E)*(1-a)^h`. Solving its curvature gives **a=0.019999979/min**,
**E=9.8999925°C**, and **T(0)=17.0999996°C**. The heat-loss coefficient is at
its **0.02/min upper bound**, to forecast rounding precision. A 50-minute time
constant explains the 5.06°C hourly cooling. Heating gain and future PID
assumptions cannot generate this particular zero-proxy curve. Constant offset
and outdoor temperature remain inseparable in `E=outdoor+offset/a`; the export
does not directly expose the actual raw outdoor input or coefficients. This is
a model-output diagnosis, **not a measured 60-minute forecast error**.

### Verified implementation mechanisms

* The reference resets all coefficients, covariance, samples and excitation
  after six rate/residual outliers. Invalid arguments alone do not increment
  this run. Repeated model mismatch is conflated with estimator failure.
* RLS uses unscaled `[minutes*(outdoor-room), minutes*heat, minutes]`, an equal
  initial covariance of 10 for differently scaled physical parameters, and
  forgetting 0.999 per accepted poll. The prior standard deviation is about
  3.16 in each coefficient's units, enormous relative to the allowed ranges.
* Parameters are individually clipped after an unconstrained RLS update while
  covariance contracts for the unconstrained solution. The resulting vector can
  disagree strongly with the observation even when the unconstrained fit did
  not. Bounds do not constitute a physically validated model.
* At constant temperature difference, loss and offset columns are collinear.
  With zero heat, heating gain is unobserved. Historical heat range and 24
  accepted polls do not establish current identifiability, yet forecasts are
  published even as `low_excitation`.
* The reference holds the preceding proxy for five minutes, missing intervening
  CH/valve/supply changes. `suspend()` zeros residual radiator heat. Its forecast
  uses end-of-minute radiator heat while learning uses interval mean heat.
* Joseph covariance updates and bounds exist; the source review and regression
  tests do not identify a different arithmetic/sign/unit defect as the cause
  of Nick's curvature. Covariance scaling, clipping and poor excitation are
  demonstrated failure mechanisms, not proof of his exact earlier training
  sequence. The export starts with an already trained model.

Delivered heat versus command, boiler water flow, supply at the radiator,
unobserved CH transitions, internal/solar gains, the constant-offset interpretation,
and the true radiator time constant remain unmeasured or confounded. Neither a
TRV-local temperature nor the room EMA is treated as radiator temperature.
The existing two-state idea is sufficient for the demonstrated integration
defects; adding another fitted physical state or selecting a new lag is not
justified by these data.

## Implemented C++ candidate

`components/adaptive_climate/shadow_model.h` is fixed-size portable C++17, with
no actuator interface, flash writes or dynamic storage. `shadow_model: false`
is the default. The production model's numerical operations are preserved;
only its read-only trace is added. The exact uninstrumented original lives in
`tests/reference/thermal_model.h`, with its extraction SHA-256 and 20,000 paired
numerical updates/forecasts checked against the instrumented reference.

The candidate:

1. Uses normalized rate features `[(mean_outdoor-midpoint_room)/10, mean_heat,1]`
   and coefficients `[10*a,b,c]`. Prior variances are `[.0004,.0025,.0001]` in
   these units. These are conservative provisional priors, not room calibration.
   Joseph updates, Cholesky checks, finite/bounded covariance and time-adjusted
   forgetting address conditioning. Forgetting is suspended without excitation.
2. Keeps the same hard **0.15°C/min and 1°C** disturbance limits. Accepted
   innovations above 0.2°C receive Huber downweighting through measurement
   variance; no parameters are updated for hard outliers. At six consecutive
   rejections it restores bounded diagonal uncertainty once, preserves the
   coefficients and sample history, and withholds forecasts until three inliers.
   Persistent mismatch remains unavailable; it is not silently trusted. A genuine
   numerical failure resets the estimator and is separately counted/reasoned.
3. Rejects an entire parameter step that crosses existing bounds, rather than
   clipping it and shrinking incompatible covariance. This can sacrifice
   adaptation at a true boundary; the explicit `constraint` state needs review.
4. Integrates the previous actual observed proxy until each raw input or binary
   flag transition. The ten-minute lag has an analytic mean and decay, both in
   learning and forecast rollouts. CH/DHW transitions retain residual radiator
   heat; DHW/window intervals cannot become training pairs. An unknown input gap
   invalidates heat attribution and requires a provisional three-time-constant
   settling period. No new physical time constant has been selected.
5. Trains only on distinct actual **raw room publications**, never on scheduled
   polls or filtered heartbeats. A new same-value publication can close a pair;
   unchanged values are not categorically rejected. Pairs accumulate 1–30 minutes
   of integrated heat/outdoor input and use their actual duration. Longer gaps
   start a new baseline; they cannot manufacture zero-change samples. Parameters
   survive such gaps. This sacrifices some long-gap learning to avoid pretending
   their temperature path is known. The midpoint-room approximation and
   event-selection bias remain limitations, especially over longer intervals.
6. Requires excitation of the full feature matrix, three recovered inliers, a
   room publication within 15 minutes, settled heat attribution and a bounded
   nominal propagated uncertainty before exposing each forecast. The information
   determinant threshold `1e-4`, 0.1°C observation-noise floor, and 1°C nominal
   half-width limit are provisional visibility policies. The factor 1.96 does
   **not** establish calibrated 95% coverage. Input, sensor-acquisition and
   future-control uncertainties are not fully modeled. No forecast is clipped
   to make an implausible trajectory look accurate.

HA publications confirm receipt of a state, not necessarily acquisition of a new
physical reading; reconnections and upstream caching remain possible. The model
therefore labels outputs **conditional_unvalidated**. Availability, receipt age,
learning eligibility and forecast eligibility are deliberately separate. A
cached held input is usable while it is not a new learning endpoint.

Forecasts hold origin outdoor temperature and future heating proxy constant,
while radiator heat evolves. They are **conditional constant-input scenarios**.
A future prescribed input trajectory would need a separate explicit rollout
interface. Actual closed-loop PID/boiler prediction is not implemented or claimed.

## Historical quantitative comparison

`shadow_replay.cpp` executes both actual C++ learners. `compare_shadow.py` uses
the existing October 30–November 2 development period, excludes export boundary
and conflicting states, and uses identical five-minute forecast origins and
independent raw held endpoints no older than 900 seconds. It cold-starts both
models. The reference observes the grid; the candidate additionally receives
actual exported input events and learns at room publications. That difference
is the intended algorithm change and is not hidden. HA change times approximate
receipt times; this is **not exact flashed-firmware replay**.

The conservative policy masks missing age diagnostics between exported events.
It yields zero candidate learning pairs and zero common forecast origins: the
unknown-heat settling requirement cannot be met. This does not mean the real
sensors failed. It means these change-only exports cannot prove continuously
observed input health for that protocol.

A separate **held-status sensitivity** assumes cached usable firmware input
status establishes continuity despite gaps/repeated values in age telemetry.
Its outputs are exploratory held-state evidence, not confirmed physical readings.
No threshold was selected on these scores. All periods have already been used
for development; none is an untouched final test set.

Under that assumption, across 864 grid origins per room:

| Room/model | Attempted pairs | Accepted | Rejected | Resets |
|---|---:|---:|---:|---:|
| Stijn/reference | 701 | 643 | 58 | 3 |
| Stijn/shadow | 502 | 502 | 0 | 0 |
| Nick/reference | 731 | 717 | 14 | 1 |
| Nick/shadow | 533 | 533 | 0 | 0 |

Pairs and acceptance percentages are **not equivalent populations**: the shadow
skips held polls, settling and long publication gaps and uses robust rate fitting.
The reset counts are from this cold-start development replay, not a claim to
reproduce the November 3 device's initial model or its six resets.

| Room/horizon | Common N | Reference MAE/RMSE/bias °C | Shadow MAE/RMSE/bias °C | Persistence MAE/RMSE/bias °C |
|---|---:|---|---|---|
| Stijn/15 | 219 | 2.095 / 2.144 / -2.095 | .098 / .141 / -.004 | .118 / .178 / -.003 |
| Stijn/30 | 174 | 3.695 / 3.781 / -3.695 | .144 / .213 / -.036 | .180 / .249 / -.001 |
| Stijn/60 | 25 | 6.130 / 6.146 / -6.130 | .290 / .484 / .014 | .352 / .510 / .080 |
| Nick/15 | 188 | 1.595 / 1.604 / -1.595 | .067 / .089 / .010 | .059 / .090 / .015 |
| Nick/30 | 92 | 2.741 / 2.754 / -2.741 | .088 / .111 / .032 | .079 / .117 / .034 |
| Nick/60 | 9 | 4.113 / 4.118 / -4.113 | .113 / .128 / -.015 | .122 / .160 / -.078 |

Each row uses exactly the same origins for all three models. Horizons have
different populations; do not compare their MAE as a horizon effect. The JSON
retains common origins, counts, coefficient ranges, forecast availability and
CH/valve/DHW/warming/cooling/unchanged strata. The 60-minute availability is
only 26/269 Stijn and 9/129 Nick bounded target opportunities before intersecting
the reference; the candidate explicitly withholds uncertain long rollouts.
Overlapping forecasts are correlated. Tiny/empty strata and uncertain health
prevent strong uncertainty bounds or causal attribution. In particular Nick
persistence wins MAE at 15 and 30 minutes. These results justify collecting
shadow data, **not replacing the production learner**.

The reference loss spans 0–.02/min and the offset reaches both ±.03 bounds in
this replay. Candidate loss spans .000610–.002000/min (Stijn),
.000910–.002462/min (Nick), with no parameter-bound rejections or numerical
resets. The positive learned offsets are empirical unmodeled gains, not verified
solar/internal heat. Longer independent data must establish whether the priors
and constraints preserve real adaptation.

## Validation and deployment gate

Host tests cover reference parity, six-rejection resets versus preservation,
invalid and corrupted-covariance recovery, unchanged raw publications versus
held polls, long heating-off periods, CH/DHW transitions and residual heat,
constraint warnings, Nick's exact cooling curve, forecast uncertainty gating,
64-bit diagnostic bounds and more than one simulated year of finite learning.
The original numerical tests and all 36 existing offline tests also run.
Synthetic convergence establishes implementation behavior only.

ESPHome is pinned to 2026.10.0. The target is esp32dev with ESP-IDF 5.5.6 and
the esp-14.2.0_20260121 Xtensa compiler. Xtensa object-size symbols establish
`sizeof(ThermalModel)=104`, `sizeof(Observer)=128`, `sizeof(ShadowModel)=132`,
and `sizeof(ShadowObserver)=208` bytes. The frozen reference is 68/92 bytes;
the trace adds 36 bytes per reference room, plus 208 bytes for each shadow
observer. Component fields, text entities and callback allocations are additional.
The observer uses fixed arrays and no allocation in its numerical update.
Desktop timing is not ESP32 timing. Actual runtime heap, worst update latency,
stack high-water mark and future MPC headroom remain unmeasured; there is no
evidence requiring an ESP32-P4 upgrade.

Firmware sizes/build results are recorded in `firmware_validation_20261103.md`.
The complete `deployment/thermostaat_shadow.yaml` is a separately prepared
build-only candidate. Expanded PID/OpenTherm/output/safety/sensor domains match
the existing complete candidate; its thermostat package remains pinned at
`7d925a7`. The original complete YAML remains untouched. As already documented
in deployment/README.md, equivalence of that old supplied package pin to the
actually flashed thermostat revision is not established. This candidate cannot
therefore be assumed safe to install over an unknown working revision.

The smallest next experiment is an explicitly approved observer-only shadow
addition to a known-matching working configuration, with rollback available.
Collect both raw room sensors, existing cycle records, new model details and
shadow forecasts, CH/DHW/valve/supply transitions and receipt-age/health records
for a new untouched future block. Check numerical/reset reasons and input
attribution before judging accuracy. Measure heap/stack and latency on that
device. Do not tune on that block before reporting it. Active MPC remains off.

Reproduction (data stay local):

```sh
g++ -std=c++17 -O2 AdaptiveClimate/evaluation/shadow_replay.cpp -o shadow-replay
python AdaptiveClimate/evaluation/diagnose_20261103.py 'history(1).csv' --output diagnosis.json
python AdaptiveClimate/evaluation/compare_shadow.py 'history (5)(1).csv' 'history (6)(1).csv' 'history (8).csv' 'history (8)(1).csv' --replay ./shadow-replay --output comparison.json
```

See `docs/shadow_diagnostics.md` for the opt-in schema and diagnostic decoding.
