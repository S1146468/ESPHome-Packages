# Read-only two-room MPC integration foundation

This increment prepares measurement, identification and replay. It does not
implement an optimizer, command publisher or any HA actuator service call.
Experimental models must not be promoted to active control from three days of
exploratory history. Newly collected data is reserved for independent evaluation.

## Responsibilities and boundary

ESP32 retains PID, window protection, DHW/OpenTherm and weather compensation.
Optional observer telemetry describes existing computations only. A separate
collector stores raw events and explicit gaps without changing devices.
Offline model fitting produces experimental model artifacts with room identity,
training period, units, feature provenance and parameter bounds. The final learner
and optimizer must run locally on the ESP32, or on an independently validated
ESP32-P4 upgrade. There is no required external optimization server. HA remains
a measurement/weather/archive interface; loss of HA must not stop existing local
PID safety behavior. The eventual embedded optimizer reads a consistent snapshot
and publishes recommendations as diagnostics only, with no actuator handles or
calls. A recommendation is never interpreted as permission to execute it.

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
5. Run embedded recommendations without actuator paths and compare with PID,
   including disagreement cases and impossible/unavailable heating requests.
6. Active control requires a separate proposal, confirmed physical constraints,
   independent validation and explicit authorization. No such deployment is part
   of this increment.

## Hardware decision and benchmark gate

Do not choose model complexity from the current board alone. First measure the
existing esp32dev under representative two-room PID/OpenTherm, API, Wi-Fi reconnect,
logging and DHW/window workloads. Collect minimum free internal heap, largest
contiguous internal allocation, task stack high-water marks, cycle/optimization
latency distribution and maximum, loop blocking, watchdog events, missed/late
OpenTherm transactions and firmware static RAM/flash. Benchmark both optional
telemetry disabled and enabled. Do not infer runtime headroom from link size.

No device connection, target execution trace or new firmware deployment is
available in this session, so these target measurements remain unperformed.
Host tests are correctness evidence only. Keep the mathematical C++ core separate
from ESPHome, clocks and communications; fixed-size workspaces and explicit
iteration/time budgets will allow equivalent benchmarks across ESP32 variants.
The Python candidates are offline research implementations, not the final learner.

If an independently validated model/optimizer exceeds measured budgets, evaluate
a specific P4 board before simplifying away a meaningful accuracy gain. P4 has no
integrated Wi-Fi/Bluetooth; select and validate its external networking path,
power, GPIO/pin assignments and board revision. ESPHome provides esp32_hosted for
supported companion arrangements, but current documentation is not proof that a
particular board/firmware pair works with the pinned ESPHome 2026.10.0 project.
Compile and test that exact combination, network-loss behavior and OpenTherm
timing/pins before choosing it. No automatic target change is authorized here.

Sources: [Espressif P4 introduction](https://docs.espressif.com/projects/esp-idf/en/latest/esp32p4/get-started/index.html),
[ESPHome Hosted networking](https://esphome.io/components/esp32_hosted/).
