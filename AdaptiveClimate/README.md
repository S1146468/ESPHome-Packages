# Adaptive Climate

A reusable, **observation-only** ESPHome external component. It learns a compact
room-temperature response model and publishes conditional 15-, 30- and 60-minute
forecasts. It does not control heating, change PID gains, command valves or write
OpenTherm values. Your existing thermostat remains responsible for heating.

Targets ESPHome **2026.10.0** and ESP32 with ESP-IDF. Neither PID, OpenTherm nor
Home Assistant is a mandatory component dependency. The observer uses existing
ESPHome numeric sensors and binary sensors, whatever supplies them.

## Contents

```text
AdaptiveClimate/
  ObserveRoom.yaml                  Reusable per-room diagnostic package
  components/adaptive_climate/
    __init__.py                    Configuration schema and code generation
    adaptive_climate.h/.cpp         Input tracking and ESPHome diagnostics
    thermal_model.h                RLS estimator, lag model and forecasts
  examples/single_room.yaml         Complete build without HA or a controller
  examples/two_rooms.yaml           Complete two-room, read-only HA example
  tests/                           Model, schema and real YAML binding tests
  docs/                            Extraction provenance and validation
  requirements-test.txt            Pinned ESPHome/test dependencies
```

## Install alongside an existing thermostat

Add the following to your existing YAML, **merging** the entries into any existing
`external_components:` and `packages:` mappings. Keep all existing heating,
sensor, API and network definitions unchanged. Replace the seven example IDs with
your existing ESPHome input IDs. No extra sensor or thermostat definition is needed.

```yaml
external_components:
  - source:
      type: git
      url: https://github.com/S1146468/ESPHome-Packages
      ref: feature/adaptive-climate-standalone
      path: AdaptiveClimate/components
    components: [adaptive_climate]

packages:
  room_observer:
    url: https://github.com/S1146468/ESPHome-Packages
    ref: feature/adaptive-climate-standalone
    files:
      - path: AdaptiveClimate/ObserveRoom.yaml
        vars:
          observer_id: living_room_model
          observer_name: Living Room
          room_temperature_id: existing_room_temperature
          outdoor_temperature_id: existing_outdoor_temperature
          valve_command_id: existing_valve_command_percent
          supply_temperature_id: existing_actual_supply_temperature
          heating_active_id: existing_heating_active
          window_open_id: existing_window_contact
          dhw_active_id: existing_dhw_active
          observer_stale_after: 15min
```

For local use, copy this directory next to your device YAML, set the external
component source to `{type: local, path: AdaptiveClimate/components}`, and use
`!include {file: AdaptiveClimate/ObserveRoom.yaml, vars: ...}`. Paths are relative
to the configuration containing them. The complete examples use `../components`
and `../ObserveRoom.yaml` because they live inside `examples/`.

Use the same inspected branch/commit for package and component. Pin a commit for
reproducible use. Loading the component alone does not add an observer instance.

## Required input contract

All seven inputs are required. IDs refer to ESPHome objects, not HA entity strings.
When importing from HA, define a `homeassistant` sensor/binary_sensor with your HA
entity ID and pass its ESPHome `id` to the observer. See the two-room example.

| Include variable | Component field | Type and meaning |
| --- | --- | --- |
| `room_temperature_id` | `room_temperature` | Numeric sensor, room temperature in °C, valid 0–45 |
| `outdoor_temperature_id` | `outdoor_temperature` | Numeric sensor, outdoor temperature in °C, valid −40–50 |
| `valve_command_id` | `valve_command` | Numeric sensor, requested valve opening **0–100%**, not 0–1 |
| `supply_temperature_id` | `supply_temperature` | Numeric sensor, **measured actual** heating supply temperature in °C, valid 0–100 |
| `heating_active_id` | `heating_active` | Binary sensor, true when heating is reported active/available |
| `window_open_id` | `window_open` | Binary sensor, true means window open |
| `dhw_active_id` | `dhw_active` | Binary sensor, true means domestic hot water active |

Do not substitute a requested water-temperature setpoint for actual supply
temperature. A boiler request is not proof of flame or heat delivery. A valve
command is not measured position or proportional heat output. Match the operating
state to the heating circuit being observed and document its meaning.

The component captures **raw, pre-filter numeric publications**. Required units
and calibration must already be correct at that point; downstream conversion,
inversion or calibration filters are not applied to the observer. If conversion
is needed, make a separate event-driven sensor that publishes correctly scaled
values only when its real source updates, and pass that ID. Do not alter existing
control sensors or periodically republish a cached value to bypass freshness.

`observer_stale_after` defaults to 15 minutes and accepts 1–60 minutes. It applies
to all four numeric inputs independently. Unchanged inputs that are not republished
can expire; a history change event or retained HA state is not evidence of a live
physical sensor. Choose a timeout based on real source reporting behaviour.
Binary inputs require a known state but are latched, without freshness timestamps.
Upstream availability remains a limitation; see below.

If an installation has no DHW circuit or no window contact, it must explicitly
supply the appropriate binary sensor and accept that assumption. The package does
not silently create always-off substitutes for missing safety-related inputs.

## Multiple rooms and direct configuration

Include `ObserveRoom.yaml` once per room, each with a unique `observer_id` and
diagnostic `observer_name`. Each instance owns its model, observation history and
fault state. Shared outdoor/supply/operating-state IDs are allowed when physically
appropriate. There is no two-room hard limit; device resources limit total instances.

The package is optional. The same external component accepts direct configuration:

```yaml
adaptive_climate:
  - id: room_model
    mode: observe
    room_temperature: existing_room_temperature
    outdoor_temperature: existing_outdoor_temperature
    valve_command: existing_valve_command_percent
    supply_temperature: existing_actual_supply_temperature
    heating_active: existing_heating_active
    window_open: existing_window_contact
    dhw_active: existing_dhw_active
    stale_after: 15min
    prediction_30min:
      name: Room Forecast 30min
    status:
      name: Room Model Status
```

`ObserveRoom.yaml` exposes all six numeric diagnostics and status. Direct
configuration allows selecting just the diagnostics you need. Only `mode: observe`
is accepted; no actuator/output binding exists.

## Interpreting learning and predictions

The three-parameter RLS model learns cooling response, heating-proxy response and
an offset, with constrained coefficients and guarded covariance updates. It uses
a provisional ten-minute heating lag to approximate radiator residual heat. It
updates every five minutes and uses actual elapsed time, with bounded timing gaps.
These are empirical response coefficients, not identified room heat capacity or
measured heat power.

Forecasts appear after 24 accepted intervals (roughly two hours of uninterrupted
learning, plus initial collection). They assume the current outdoor temperature,
valve command, supply-derived heat input and heating-active state continue. They
do not anticipate what the existing thermostat will do next. The lag state decays
during reported heating-off periods, which can still teach cooling dynamics.

| Diagnostic | Interpretation |
| --- | --- |
| Forecast 15/30/60min | Conditional predicted room temperature, °C; not a target or heating instruction |
| Model Residual RMSE | Square root of exponentially weighted, pre-update one-step squared error (new weight 0.05); not a forecast confidence interval |
| Model Training Samples | Accepted training intervals, not raw sensor publications |
| Model Heating Excitation | Range of the dimensionless training heat proxy; not an identifiability proof or confidence percentage |
| Model Status | Collection or suspension reason, described below |

Statuses include `waiting_for_inputs`, `collecting_data`,
`missing_or_stale_input`, `missing_operating_state`, `invalid_input`, `window_open`,
`domestic_hot_water`, `timing_gap`, `disturbance_rejected`, `low_excitation`, and
`learning_unvalidated`. `low_excitation` can still publish diagnostic forecasts;
it is not approval to use them for control. No status asserts validated accuracy.

Missing/stale/invalid inputs, open windows and DHW suspend learning and clear
forecasts. Observations are not paired across an interruption. Implausible rates
or large prediction residuals are rejected; six consecutive large-residual
failures reset the model. Raw invalid numeric publications invalidate immediately;
other input guards run once per second. The full numerical safeguards are retained
unchanged from the source component (see the source manifest).

## Limitations

- Experimental forecasts must not drive heating automations. Real-room prediction
  accuracy, calibrated uncertainty, and comfort/energy benefit are not established.
- Fixed ten-minute lag and five-minute held inputs miss faster valve/burner changes.
- Binary states may remain latched when upstream devices disconnect. Numeric raw
  timestamps measure ESPHome reception, not necessarily physical measurement time.
- No persistence: reboot resets learning; this component writes no model state to
  flash. Confidence intervals and controller adaptation are not implemented.
- It does not inspect or modify thermostat setpoints, PID parameters, hydraulic
  constraints, or boiler protection. Existing heating behaviour is outside its scope.
- Build-time memory statistics do not establish runtime free heap, largest block,
  loop latency or Wi-Fi performance on your complete device configuration.

## Build and test

Use Python 3.12–3.14. From the repository root:

```sh
python -m pip install -r AdaptiveClimate/requirements-test.txt
python -m pytest AdaptiveClimate/tests -q
g++ -std=c++17 -O2 -Wall -Wextra -pedantic AdaptiveClimate/tests/test_thermal_model.cpp -o thermal-tests
./thermal-tests
esphome compile AdaptiveClimate/examples/single_room.yaml
esphome compile AdaptiveClimate/examples/two_rooms.yaml
```

The single-room example deliberately uses uninitialised input stubs and will not
learn until wired to real sensors. The two-room example contains placeholder HA
entities and Wi-Fi credentials; configure a private API key before any authorised
deployment. Neither example contains a heating controller or actuator action.
Compiling does not upload firmware. See [validation](docs/validation.md).
