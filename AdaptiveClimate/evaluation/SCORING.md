# Trustworthy forecast evaluation — increment 2

## Result and correction

No corrected temperature-accuracy estimate is possible from the supplied files.
The raw observer temperatures confirmed by the user are **absent**. The earlier
MAE/bias table and recorded_scores.json remain reproducible legacy outputs, but
compare against a separate EMA diagnostic and must not be used to select a model.
`validated_scores.json` now explicitly reports blocked scoring with no numbers.
That is a missing-evidence result, not zero error or proof the predictor is bad.

The local thermostat snapshot is older than its deployed package track:
freshness branch rounds output to 1%; main at 7d925a7 rounds to 5%. User confirms
valve-opening inputs at scale 1, raw room sensors and 5-second PID interval.
This supports correct current command semantics, not proof of historical
firmware revision, physical valve movement, or heat delivered.

## Timestamp and validity contract

`validated_scoring.py` accepts normalized JSON after provenance reconciliation,
not an automatic conversion of an ambiguous History CSV. No normalizer should
set verification flags merely because expected column names are present.

Top-level fields:

- `metadata`: booleans `raw_temperature_mapping_verified`,
  `forecast_issue_times_verified`, `measurement_publication_times_verified`,
  `units_verified`; `temperature_unit: "degC"`; `models: ["original", ...]`;
  timezone-aware ISO `start`, `train_end`, `validation_end`, `end`.
- `measurements`: records `{room, time, value, available, boundary}`.
  `time` is a verified raw publication timestamp, not a periodic export/poll
  timestamp. Preserve unavailable rows; never drop them and reuse older values.
  If physical sample time is known, account for acquisition/transport delay
  during normalization; publication age alone does not bound physical sample age.
- `health`: records `{room, time, available, boundary}`. `available` means
  confirmed measurement/connection health, not heating demand. An unknown state
  is false. Preserve outages and reconnect gaps. Healthy cached text must not
  be repeatedly stamped as newly verified health. Model readiness at issue time
  must also be checked before admitting a forecast. Heating/window/DHW operation
  is distinct from measurement health: valid interruption scenarios should later
  be retained and stratified, not silently excluded as sensor faults.
- `forecasts`: `{room, time, model, horizon, value, boundary}`. `time` is the
  verified issue/cycle time; horizons are 15, 30, 60 minutes. Invalid or withdrawn
  forecasts use null values. All models/horizons must share an actual origin.
  Separate HA receipts milliseconds apart are not automatically a common issue
  time: reconcile using cycle evidence, retain latency, or reject the ambiguity.
- Optional `missing_entities` blocks scoring explicitly.

Rooms are `stijn` and `nick`. Tests contain a runnable synthetic schema example;
synthetic results are tests only, not historical validation.

Rules implemented:

1. Strict timezone parsing, duplicate rejection, finite values and Celsius range
   checks. Synthetic boundary records never establish a measurement or forecast.
2. Origin and horizon outcomes use only the most recent measurement at or before
   that time, at most 60 seconds old by default. No interpolation, backfill, or
   future-nearest lookup. This is bounded held-publication scoring, not an exact
   continuous physical temperature measurement. Event-driven sensors legitimately
   reporting less often may be rejected; report coverage rather than hide this.
3. Continuous health evidence is required through the maximum horizon, with a
   default 360-second confirmation limit; gaps and explicit failures reject the
   common origin. These limits are evaluation assumptions, not firmware changes
   or validated future MPC safety thresholds. Predeclare sensitivity analyses
   (e.g. 30/60/120-second outcome age) before viewing test outcomes.
4. Every candidate and persistence use the same origins and targets across all
   three horizons **within each room**. One room's rejection does not discard the
   other. Output includes exclusion counts and accepted measurement ages.
5. Event-weighted metrics count each valid forecast event. Grid-sampled metrics
   select the first common valid origin in each fixed 300-second bin; both use
   the same values with no forecast carrying. Grid sampling reduces event-density
   bias but is NOT complete time-weighted exposure accuracy. Missing bins remain
   missing. True time weighting requires full publication coverage, unavailable
   in the current event export. Never hold a prediction to fabricate new issues.

Metrics: MAE, RMSE, signed forecast-minus-observation bias, absolute-error p50/p95
(floor-index empirical quantiles), n. Autocorrelated errors are not independent
samples. Add day/block uncertainty intervals once sufficient days exist.

## Chronological evaluation

Split boundaries are explicit inputs, not selected after seeing results. Origins
within 3600 seconds before train/validation boundaries are purged. The entire
60-minute label interval must stay in its split. The final end caps test labels.
No randomized splits, cross-boundary label training, or future weather leakage.

This implements split assignment and evaluation, not parameter fitting. Fit
candidate hyperparameters only on training data, select them on validation,
freeze choices before opening the test set. For online adaptation, explicitly
allow only measurements already received at each origin; report adaptation
protocol alongside frozen-model results. Warm up replay on preceding history.
Persisted initial state must be known or the replay must be labelled cold-start.

## Conditional versus PID-operated outcomes

**Current observer:** constant future outdoor and heat-drive assumptions, with
decaying radiator state. Comparing these predictions to actual raw temperatures
while PID changes valves measures constant-input forecasts against PID-operated
outcomes. It does not mean the observer predicts future PID decisions.

**Conditional diagnostic:** drive a frozen fitted thermal model with a specified
trajectory. If that trajectory is realized future valve/supply/CH observations,
label it explicitly **oracle-input retrospective**, never real-time accuracy.
Keep weather assumptions identical when isolating heating-trajectory error.
Do not update coefficients using future room observations during the rollout.
Future weather observations are likewise oracle inputs, not historical forecasts.

**Genuine closed-loop prediction:** would require target/mode history and a
validated model of PID state/decisions, shared boiler response and disturbances.
It is not implemented. Missing CH, DHW, supply and raw temperature histories
currently prevent even a faithful conditional replay.

## Deterministic production-code replay

`replay.cpp` includes the existing `thermal_model.h` without modifying it. It
maintains separate Observer instances and emits status, samples, coefficients
and three constant-drive forecasts. No estimator is ported or reimplemented.

Compile: `c++ -std=c++17 -O2 AdaptiveClimate/evaluation/replay.cpp -o replay`

Whitespace-separated stdin rows (no header; # comments allowed):

```
# room elapsed_ms room_degC outdoor_degC valve_percent supply_degC CH window DHW valid
stijn 0 20 10 50 50 1 0 0 1
nick 0 19 10 25 50 1 0 0 1
stijn 300000 20.1 10 50 50 1 0 0 1
```

This is a synthetic format illustration, not supplied measurements. Times are
monotonic elapsed milliseconds per room. `valid=0` invokes suspend and the
numeric fields are ignored by learning. Include invalidation events between
five-minute observation ticks, not only ticks themselves. Input-policy/API
guards live outside Observer in firmware; the data normalizer must reconstruct
them from measured evidence. The executable does not assert missing health.
Shared CH/supply/DHW must come from the same stream for both rooms. No inference
from commanded demand is allowed. CSV output is deterministic for identical
input/compiler; host float results are not claimed bit-identical to ESP32.

The model starts cold. Reproducing a running device's predictions also requires
its boot history, accepted/rejected samples and parameter history; a cold-start
replay is a reference experiment, not proof of the flashed device's exact state.

## Negative-bias investigation and next experiment

The observed negative discrepancy remains unexplained. It must not yet be
attributed to heat-loss learning or corrected by changing coefficient bounds.

| Hypothesis | Evidence / next discriminating check |
|---|---|
| EMA target mismatch | Confirmed signal mismatch; recompute with raw outcome and origin temperature first. EMA can create either error sign depending on trend. |
| Wrong heating scale | Current user mapping is percentage at scale 1; compare historical command export with model excitation and firmware revision before ruling out earlier mismatches. |
| Overestimated loss / offset clamp | Replay emits coefficients; examine loss/gain/offset hitting bounds (loss 0–.02, gain 0–.30, offset ±.03) alongside signed errors. Existing exports do not contain these coefficients. |
| Fixed lag / residual heating | Observer uses a fixed 10-minute lag; suspend clears radiator heat state. Stratify cooling tails and time since window/DHW/API suspension after raw scoring is sound. |
| Missing CH or valve transitions | Observer holds preceding five-minute heating proxy; replay a common measured stream and compare with an explicitly labelled higher-resolution conditional input experiment. |
| Future PID changes | Compare constant-drive versus realized-input conditional rollouts at common origins without future learning. Improvement here diagnoses input assumptions, not better real-time forecasting. |
| Quantization | Raw source resolution and event gaps are missing. Quantify increments, age and floor effects; do not infer precision from EMA decimal places. |

Next concrete experiment: export the missing streams in MAPPINGS.md; establish
raw publication/outage masks; freeze splits; score original publications and
persistence at common valid origins; cold-start replay the unchanged C++ model
with a documented warm-up and compare model status/training counts. Only then
test fixed lag alternatives and TRV-minus-room features on validation, keeping
the final test interval unopened. No new learner or control algorithm is included.

## Validation

Local results on 2026-11-02: **18 evaluation tests passed**, including two
compiled replay tests (no skips); **52 existing AdaptiveClimate Python/schema
tests passed**. Replay compiled successfully with the installed Zig C++ compiler
in C++17/O2 mode after restricted-process temporary-file failures were resolved
by a permitted host build. This is host validation, not an ESP32 timing or memory
benchmark. GitHub CI results are separate from these local results.

Run Python tests with `ADAPTIVE_REPLAY_EXE` set to the compiled executable's
absolute path. Without it, replay tests explicitly skip and that is not a full
pass. `python -m unittest discover -s AdaptiveClimate/evaluation -p 'test_*.py'`.
The GitHub workflow compiles the host replay and sets the environment variable.
No firmware build/deployment is needed for this evaluation-only increment;
all runtime component, PID, OpenTherm and thermostat YAML files are unchanged.
