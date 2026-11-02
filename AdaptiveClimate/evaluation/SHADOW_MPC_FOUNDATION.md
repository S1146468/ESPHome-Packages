# Read-only two-room MPC integration foundation

This increment prepares measurement, identification and replay. It does not
implement an optimizer, command publisher or any HA actuator service call.
Experimental models must not be promoted to active control from three days of
exploratory history. Newly collected data is reserved for independent evaluation.

## Responsibilities and boundary

ESP32 retains PID, window protection, DHW/OpenTherm and weather compensation.
Optional observer telemetry describes existing computations only. A separate
collector stores raw events and explicit gaps without changing devices.
Offline model fitting produces versioned model artifacts with room identity,
training period, units, feature provenance and parameter bounds. An eventual
external optimizer reads those artifacts and a consistent observation snapshot.
It writes recommendations to a local append-only file or read-only dashboard.
Its process must have no actuator client, service-call implementation or command
topic. A recommendation is never interpreted as permission to execute it.

## Required optimizer input contract

- Separate Stijn/Nick raw room estimates and uncertainty, TRV-local observations
  if validated, current effective valve command, room target and heat/off mode.
- Shared actual CH state, supply temperature, DHW state, weather-compensation
  target and boiler fault/availability. Actual CH is not requested heat demand.
- Window state per room. Unknown states remain unknown, never guessed closed.
- Measurement source/publication/receipt times, observer cycle sequence and
  device monotonic timestamp, collection session identity and outage intervals.
- Room-specific model version and radiator-state estimate with uncertainty.
- Current KNMI conditions, and archived Met.no forecasts carrying retrieval and
  valid times. Future observed weather must not masquerade as a forecast.
- Documented command bounds and shared hydraulic constraints. Boiler minimum
  run time, valve rate limits and minimum flow are not presently established.

## Initial recommendation protocol (design, not implemented)

Evaluate 60/120/180-minute horizons and 5/10/15-minute command intervals offline
on common origins, then freeze the choice before independent validation.
Use a bounded candidate command set and room-temperature/comfort penalties,
command-change penalty and a clearly labelled heat-demand proxy. No energy
savings claim without energy metering. Shared boiler availability gates both
rooms; window-open and climate-off gate the respective room. DHW interrupts
heating assumptions for both rooms. Avoid assuming supply temperature responds
instantly to requested heat. Residual radiator heat persists after commands stop.

Each output should contain recommendation ID, collection-session/cycle IDs,
issue time, expiry time, both room commands, predicted trajectories and uncertainty,
model versions, constraints used, objective terms, and one of:
`experimental_recommendation`, `insufficient_evidence`, `infeasible`, `expired`.
Missing observations/targets/modes or unknown safety constraints produce
`insufficient_evidence`, not a guessed command. Existing PID continues regardless.

## Validation gates

1. Sustain collection through restarts, HA outages and sensor unavailable events;
   reconcile atomic cycle telemetry with receipt times and avoid duplicate issues.
2. Verify candidate forecasts against raw temperatures on genuinely new data;
   report persistence, original observer and candidate errors on identical origins.
3. Separately evaluate constant-drive predictions, retrospective known-input
   thermal rollouts and controller-aware predictions. A fitted thermal model does
   not predict future PID decisions by itself.
4. Test two-room shared-boiler simulations with DHW/windows, delayed supply,
   uncertain heat delivery and sensor gaps. Check constraint compliance and
   optimization latency. Simulation results alone do not establish readiness.
5. Run external recommendations without actuator paths and compare with PID,
   including disagreement cases and impossible/unavailable heating requests.
6. Active control requires a separate proposal, confirmed physical constraints,
   independent validation and explicit authorization. No such deployment is part
   of this increment.
