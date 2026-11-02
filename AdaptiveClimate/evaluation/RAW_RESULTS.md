# Raw-temperature follow-up, 2026-11-02

## Input and merge

The local file is `history (8).csv`, not `history (8)(1).csv`. Its 36,498 rows,
31 entities and required signal names match the user's description. It was
merged with history (5) and (6), preserving original timestamp strings, all
climate attributes, source filenames and SHA-256 hashes. Identical overlapping
records were deduplicated (3,241); five conflicting entity/timestamp records are
marked unusable rather than overwritten. Each file's start-boundary rows are
marked conservatively. The merged JSONL remains local outside the repository;
`raw_temperature_report.json` contains reproducible aggregate evidence only.

New verified HA mappings: supply `sensor.thermostaat_heating_temperature`, actual
CH `binary_sensor.thermostaat_heating_active`, DHW
`binary_sensor.thermostaat_hot_water_active`, flame
`binary_sensor.thermostaat_flame_on`. These are separate from requested water
temperature or room heat demand. Master climate attributes are preserved, not
flattened into temperature-only records.

## Coverage and reporting

| Signal | Rows | Median change gap, seconds | Maximum gap, seconds | unknown/unavailable rows |
|---|---:|---:|---:|---:|
| Stijn raw temperature | 1237 | 45.224 | 4950.152 | 4 |
| Nick raw temperature | 1203 | 37.303 | 15177.732 | 4 |
| Actual boiler temperature | 4768 | 7.237 | 3345.536 | 1 |
| CH activity | 67 | 960.105 | 38320.983 | 1 |
| DHW activity | 43 | 53.005 | 43003.255 | 1 |
| Thermostat uptime | 890 | 300.018 | 300.613 | 1 |

Long change gaps are not proof of stale physical measurements. Conversely, a
held value is not proof the device is still reachable. CH/DHW event streams
reconstruct recorded states, with invalid/unavailable intervals preserved; no
interpolation, demand substitution or invented boiler events was performed.
Do not extrapolate a final binary state beyond export coverage as confirmed
operation. The uptime boundary value is already about 229,534 seconds: the model
was not newly booted at export start, so cold-start coefficients cannot reproduce
the running model's initial state. Entity identity of the legacy `diyless`
uptime name also needs registry confirmation before using it as a precise clock.

## Strict result

**Zero certified origins; no strict accuracy score.** The previous scorer and
thresholds remain unchanged. New diagnostics separately audit change-time pairs
without promoting them to accepted strict results. Forecast cycle/issue identity,
physical acquisition latency, and continuous health remain unverified.

Health-status exports have 358 Stijn / 323 Nick change events, including
`held_unconfirmed` and invalid/unavailable states. The source publishes status
only when the string changes. Applying the existing 360-second confirmation rule
over the full 60-minute horizon accepts none of the bounded pairs. This is a
limitation of evidence, not a diagnosis of continuous outages. A bounded pair
does not pass merely because its start/end raw temperatures are recent.

The already available input-age diagnostics may support a future independent
publication/health reconstruction. That requires validating their relationship
to actual sensor receipts, API outage states and issue cycles, not relabeling
status changes as periodic health confirmations. No threshold was relaxed here.

The receipt-clock audit implemented in this increment compares each finite
age-diagnostic event's `timestamp - age` against the most recent past raw
temperature change. Stijn: 25,549/25,590 comparisons agree within 2 seconds,
median absolute difference .364 seconds, p95 .540 seconds. Nick:
25,597/25,641, median .397 seconds, p95 .529 seconds. There are 1,218/1,172
observed age decreases respectively. This strongly supports the mapping and
receipt timing; it does not establish physical acquisition time. Outliers and
availability transitions must be reconciled before using the age streams as
strict health evidence. These comparisons are highly correlated diagnostics,
not independent accuracy samples. The strict scorer's confirmation rule remains
unchanged; a separate validated reconstruction can supply better evidence later.

## Exclusion funnel

Rules applied in order: split/embargo; invalid/boundary/conflicting forecast;
raw origin no older than 60 seconds; raw horizon outcome no older than 60 seconds.
Unknown/unavailable records block matching rather than being skipped. The first
four rejection columns plus bounded pairs sum to the total. Health is a further
rejection of ALL bounded pairs. Origins are common between recorded and
persistence within each room/horizon, not forced common across horizons.

| Room/min | Total | Split/embargo | Invalid/boundary | Origin raw | Outcome raw | Bounded pairs | Health rejected |
|---|---:|---:|---:|---:|---:|---:|---:|
| Stijn/15 | 741 | 37 | 25 | 528 | 120 | 31 | 31 |
| Stijn/30 | 741 | 37 | 25 | 528 | 122 | 29 | 29 |
| Stijn/60 | 741 | 37 | 25 | 528 | 117 | 34 | 34 |
| Nick/15 | 838 | 42 | 14 | 634 | 111 | 37 | 37 |
| Nick/30 | 838 | 42 | 14 | 634 | 120 | 28 | 28 |
| Nick/60 | 838 | 42 | 14 | 634 | 128 | 20 | 20 |

## Exploratory comparison, not accepted forecast accuracy

The following uses the correct raw temperatures and bounded change-time matches,
but is BEFORE the failed continuous-health/issue-time gates. It is event-weighted,
with sparse, nonrepresentative selection toward frequently changing temperatures.
It must not be used to claim a validated performance advantage or select a model.

UTC chronological boundaries were fixed in the analysis code before calculating
these results: start Oct 30 11:00, train end Oct 31 11:00, validation end Nov 1
11:00, test end Nov 2 11:00. A 60-minute embargo applies before each boundary.
No learner or hyperparameter was fitted. The period was already explored in the
earlier audit, so this is not a pristine holdout for future model selection;
reserve new later data for that purpose. No future heating/weather was used.

Test-period bounded comparisons, Celsius:

| Room/min | N | Recorded MAE | RMSE | Bias | Persistence MAE |
|---|---:|---:|---:|---:|---:|
| Stijn/15 | 10 | .266 | .314 | -.266 | .120 |
| Stijn/30 | 8 | .681 | .742 | -.368 | .325 |
| Stijn/60 | 12 | 1.306 | 1.350 | -1.306 | .292 |
| Nick/15 | 15 | .135 | .157 | -.134 | .067 |
| Nick/30 | 10 | .260 | .306 | -.249 | .130 |
| Nick/60 | 6 | .549 | .622 | -.537 | .217 |

Full train/validation/test metrics, p50/p95 absolute errors and counts are in the
JSON report. Negative bias persists in these bounded diagnostics: correcting
the EMA mapping alone does not remove it. Its magnitude/cause is not established
for all operating periods. Constant future heat assumptions, model coefficients,
residual heat, suspension and future PID changes remain competing explanations.

## Replay decision and exact missing evidence

The production C++ replay remains unchanged and its tests were rerun. No historical
replay accuracy is claimed: boot-time model coefficients/covariance/radiator state,
exact observation ticks, raw receipt callbacks and health suspension events are
not reconstructed. Boiler supply values changing less often than publication
frequency are another distinction: a change timestamp cannot establish freshness
at every observer tick. Running a freshly initialized model on invented 5-minute
ticks would be an assumed cold-start experiment, not replay of the recorded model.

Next useful evidence: a read-only log of observer issue/tick timestamps and
accepted/rejected updates, raw publication/availability and API connection events,
plus either model state at collection start or observation history from a known
reset. No restart or firmware deployment is requested here. Independently validate
the existing age-diagnostic stream as a receipt-clock proxy before deciding that
new logging is required. Raw history is now present; do not request it again.

## Reproduction

Run `analyze_exports.py` with history (5), (6), (8), and `--output` pointing to a
local data directory. Run the existing unittest suite with ADAPTIVE_REPLAY_EXE
set. Historical control files and the thermal learner are untouched.
Validation: 21 tests passed locally, including production-code replay tests.
