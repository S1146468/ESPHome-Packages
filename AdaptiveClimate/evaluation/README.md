# Initial measurement audit — 2026-11-02

Newest increment: [event-driven health reconstruction and sensitivity results](EVENT_HEALTH.md).
The event-only status heartbeat assumption is corrected in a separate, explicitly
labelled held-state analysis. Original strict scoring remains available.

Latest follow-up: [raw-temperature results and coverage](RAW_RESULTS.md).
The missing raw/boiler exports have now been supplied; earlier missing-file
statements below describe the initial audit only.

**Superseded scoring interpretation:** the table below uses an EMA diagnostic,
not the observer's raw input. It is preserved for reproducibility only and must
not be cited as thermal prediction accuracy. See `SCORING.md` and `MAPPINGS.md`
for the next increment, strict evaluation contract and missing-data gates.

Status: partial evaluation foundation. No thermal-model or actuator changes.
This is not a completed MPC implementation or acceptance report.

## Provenance

Local Adaptive Climate checkout and freshly fetched upstream freshness branch
both resolve to 533b3d7. Upstream main has advanced to 7d925a7 (weather
compensation smoothing change); it has not been merged into this branch.
The actual deployed firmware commit and user's complete thermostat configuration
have not been established from these files. Entity names alone cannot prove them.

inventory.json records hashes and per-entity counts, invalid values, ranges,
event gaps and coverage for both supplied exports (128 and 23 entities).
Unit metadata is absent. Event gaps are not device reporting intervals.
Boundary rows may be synthetic export states, not new measurements.
The forecast example contains valid times but no historical retrieval archive.

## Preliminary numerical finding

recorded_scores.json compares recorded forecast events with the last recorded
sensor.climate_{room}_temp state at the horizon. It reports MAE, RMSE, bias,
absolute error percentiles and matched sample counts. Persistence uses exactly
the same origins. Initial boundary forecast rows are excluded. Invalid states
remain invalid; there is no interpolation or backward fill. Evaluation stops
at the last room-temperature event rather than extrapolating beyond coverage.

| Room | Horizon min | N | Forecast MAE | Persistence MAE | Forecast bias |
|---|---:|---:|---:|---:|---:|
| Stijn | 15 | 710 | .345 | .091 | -.331 |
| Stijn | 30 | 707 | .696 | .162 | -.654 |
| Stijn | 60 | 701 | 1.449 | .267 | -1.304 |
| Nick | 15 | 817 | .271 | .060 | -.267 |
| Nick | 30 | 814 | .535 | .106 | -.523 |
| Nick | 60 | 808 | 1.058 | .176 | -1.016 |

These are descriptive, event-weighted comparisons over the supplied period,
not held-out candidate selection or fresh physical measurement accuracy.
Held room state may conceal outages; repeated unchanged forecast publications
may be missing from an event export. Forecast origins must be reconciled with
model status and measurement health before using these figures for acceptance.
The temperature entity mapping also needs confirmation against deployed YAML.
No accuracy improvement is claimed.

## Source audit findings

The observer has independent model instances, bounded three-parameter RLS,
five-minute observation updates, ten-minute radiator lag and constant-drive
forecasts. Training residual RMSE is not multi-step forecast accuracy.
Window and DHW conditions suspend observations. Suspension discards radiator
state, which is potentially problematic for residual heat after interruptions.
Five-minute sampling holds the preceding heating proxy and misses intervening
boiler/valve transitions. Neither issue has yet been experimentally isolated.

The component subscribes to raw sensor callbacks; scaling depends on the
selected sensor stage. The valve-opening sensor is the appropriate percentage
command interface, with scale 1.0, rather than treating raw heat-output values
as equivalent. Command is not physical position. No command path was changed.

## Missing evidence and next implementation gates

The supplied entity inventory lacks measured boiler supply temperature, actual
CH activity and DHW activity. It also lacks Stijn's climate entity. These gaps
prevent faithful baseline replay and two-room closed-loop identification.
Do not invent these inputs from valve command or TRV local temperature.
TRV local temperature is present (265 Stijn / 111 Nick rows); it is not radiator
surface temperature. Ventilation demand is not measured airflow.

Collect existing supply, CH, DHW, both climate entities/targets, raw independent
room sensors, effective valve commands, window states, model status and existing
input-health diagnostics through HA Recorder. Avoid duplicating the ten-second
age diagnostics in a second database. Confirm units from HA entity metadata.
Record forecast retrieval time, source, valid time, values and missingness in an
append-only archive; do not overwrite snapshots or substitute observed weather.

Next: validate health masks and exact deployed mappings; implement chronological
train/validation/test splits with horizon embargoes; replay the original C++
observer; compare radiator/TRV, weather and multi-state candidates on common
origins, including heating/cooling/transition strata. Preserve a final untouched
period and obtain substantially more seasonal coverage.

## Architecture direction (not implemented)

Keep PID, safety, weather compensation and OpenTherm on ESP32. Run experimental
identification and optimization externally, with a recommendations-only output
and no actuator credentials or service-call path. Test 60–180 minute horizons
and command intervals before choosing either. Coordinate both room predictions
against shared boiler availability, DHW and windows; command and energy costs
are proxies until hydraulic constraints and energy metering are established.

Persistence should later use versioned, validated coefficients and covariance,
bounded writes, checksums and cold-start fallback. Do not restore pre-reboot
radiator state as current without elapsed-time reconciliation. No persistence,
optimizer, forecast collector, firmware build or runtime resource measurement
is delivered by this initial audit. No deployment changes are required.

## Reproduction

Use Python standard library. Run inventory.py with both CSV paths and --output;
run score_recorded.py with the main CSV path and output JSON path.
Run `python -m unittest discover -s AdaptiveClimate/evaluation -p test_*.py`.
