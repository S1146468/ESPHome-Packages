# Optional observation-cycle record

The component can publish a single atomic JSON text state at the end of each
five-minute `update()` call. It is disabled unless `cycle_record` is configured.
There are no actuator bindings or service calls. This addition does not change
thermal_model.h, RLS equations, radiator lag, PID, OpenTherm or existing diagnostics.
No firmware has been deployed by this development work.

## Configuration for a future reviewed build

Merge this into the actual thermostat configuration alongside existing packages;
do not replace that configuration with the build-only fixture. Both component
and observer source references must resolve to the reviewed instrumentation commit.

```yaml
adaptive_climate:
  - id: !extend stijn_thermal_model
    cycle_record:
      name: "Stijn Observation Cycle"
      device_id: adaptive_climate_stijn
  - id: !extend nick_thermal_model
    cycle_record:
      name: "Nick Observation Cycle"
      device_id: adaptive_climate_nick
```

`examples/cycle_diagnostics.yaml` is a compile-only fixture using uninitialised
input stubs. Do not install those stubs on the real thermostat. Optional text
sensor schema has no new required inputs, no default new entities and no output
interfaces. Existing room IDs and packages remain intact.

After a separately approved build is installed, identify the two new HA entity
IDs in the entity registry and append them to `evaluation/collection_entities.json`.
Do not infer their IDs from display names or start collecting guessed entities.
The event collector preserves each changing atomic state and its HA receipt times.

## Record format (version 1)

```json
{"v":1,"q":32,"t":9000000,"o":"accepted","r":"low_excitation","n":30,"f":[20.0,20.0,20.0]}
```

- `v`: format version.
- `q`: monotonically increasing update sequence **within this room instance and
  boot**, starting at 1. Independent room counters. It is not persisted: no flash
  writes are introduced. Counter reset and decreasing `t` identify a possible
  reboot; correlate with existing uptime and collector connection/session history.
  Do not treat `(room,q)` as globally unique across boots.
- `t`: integer device `millis_64()` captured at entry to that observation update.
  This is the actual monotonic observation-cycle timestamp, not UTC or the raw
  sensor's acquisition time. HA receipt time must be retained separately. It
  survives the 32-bit millis wrap; direct integer text avoids float precision loss.
- `o`: `accepted`, `rejected`, `suspended`, or `baseline`. Accepted means the
  unchanged learner accepted the observation, including before its 24-sample
  forecast readiness gate. Rejected means disturbance rejection. Suspended means
  the input/window/DHW/API guard prevented this update. Baseline means no learning
  update (initial baseline, insufficient elapsed time, or timing gap).
- `r`: unchanged production status/reason for this cycle.
- `n`: model accepted-sample count AFTER this cycle. A model reset may decrease
  this count; it is not the cycle sequence.
- `f`: forecasts in Celsius for `[15,30,60]` minutes from this cycle; unavailable
  or non-finite predictions are JSON `null`. They are the same computed values
  passed to existing forecast sensors, formatted to six decimal places. These
  values retain the production constant-future-drive assumption.

One publication associates forecasts, learning outcome, sample count and timestamp
without joining six independent HA updates. Each sequence changes even if
forecasts repeat, avoiding same-value forecast suppression when this entity is
recorded. The payload is kept below HA's 255-character state limit; bounded stack
buffers and known literal reason strings are used. The platform's text sensor
publication still involves its normal string/API handling. No runtime heap/latency
benchmark on the user's ESP32 is claimed.

The update record is **not** a full event log: faults can suspend the observer
between scheduled updates via callbacks/guard checks. Existing status/availability
and input-age streams must still be collected. A disconnected ESP cannot deliver
its record live; HA's latest state is not a durable queue. Event collection and
sequence-gap detection remain required. Do not backfill missing cycles.

## Estimator replay scope

This record establishes cycle grouping/timing and learning outcomes, not complete
model restoration. The unchanged estimator keeps covariance and radiator state
private. Coefficients alone are insufficient to reproduce RLS, so no misleading
"replay snapshot" is exposed. Exact replay needs measurements and interruption
history from a known baseline/reset, or a separately versioned full-state capture
including covariance, prior observation and radiator state. That would require
additional interfaces and exceed this minimal text state's intended scope.

The host test executes the real component with and without instrumentation and
checks identical forecasts/sample counts, independent rooms, invalid/suspended
updates, rejected learning, JSON null forecasts and 64-bit clocks/sequences.
Schema/code-generation tests verify disabled compatibility and optional fixture.
