# Signal mapping and export instructions

## Current availability (supersedes initial missing-data notes below)

`history (8).csv` now supplies both raw room sensors, both master climates with
attributes, original window contacts, actual boiler signals and uptime. Confirmed
boiler entity IDs are `sensor.thermostaat_heating_temperature`,
`binary_sensor.thermostaat_heating_active`, `binary_sensor.thermostaat_hot_water_active`
and `binary_sensor.thermostaat_flame_on`. The water target is
`sensor.thermostaat_target_water_temperature`; uptime is
`sensor.diyless_thermostat_uptime` (legacy device identity should be checked).
Do not request these histories again. Remaining evidence gaps concern physical
sample times, exact device issue times, initial estimator state and unrecorded
connection events—not absent raw/boiler history. See EVENT_HEALTH.md.

## What is verified

Sources inspected: `Thermostat/ClimatePID/ClimateDevice.yaml`,
`Thermostat/OpenTherm.yaml`, `AdaptiveClimate/ObserveRoom.yaml`,
`AdaptiveClimate/examples/thermostaat_freshness.yaml` at 533b3d7.
The user supplied mappings directly from `/config/esphome/thermostaat.yaml`
on Home Assistant (not a Windows path). Full YAML and HA entity registry were
not supplied. Observer code/package are pinned to 533b3d7; thermostat packages
follow `main`. No known local overrides; interval 5 seconds, ESPHome 2026.10.0,
ESP-IDF, esp32dev, node `thermostaat`. Flashed firmware remains unverified.
ESPHome IDs are NOT HA entity IDs; names can be renamed in HA. The generic
Thermostat.yaml substitutions are not evidence of your deployed bindings.

| Signal | Package identity / semantics | HA export mapping |
|---|---|---|
| Supply | OpenTherm `t_boiler`, ID `ch_temperature`, name **Heating Temperature** | `sensor.thermostaat_heating_temperature`, available |
| Actual CH | OpenTherm `ch_active`, ID `${boiler_active}`, name **Heating Active** | `binary_sensor.thermostaat_heating_active`, available |
| DHW | OpenTherm `dhw_active`, ID `dhw_active`, name **Hot Water Active** | `binary_sensor.thermostaat_hot_water_active`, available |
| Flame | OpenTherm `flame_on`, name **Flame On** | `binary_sensor.thermostaat_flame_on`, available; not a replacement for CH |
| Raw room Stijn/Nick | `climate_stijn_temperature` / `climate_nick_temperature` | `sensor.temp_sensor_kamer_stijn_temperature` / `sensor.temp_sensor_kamer_nick_temperature`; both available |
| EMA diagnostic | `${device.id}_temperature_temp`, alpha 0.1, periodic template | `sensor.climate_stijn_temp`, `sensor.climate_nick_temp` confirmed present; NOT raw targets |
| Local PID climate | User-confirmed IDs `verwarming_stijn` / `verwarming_nick`, PID temperature input `${device.id}_temperature` | Nick `climate.climate_nick_verwarming_nick` present; Stijn HA entity unresolved/absent |
| HA master climate | `${master}` supplies mode and target to local climate | `climate.verwarming_stijn_master` / `climate.verwarming_nick_master`; both available with attributes |
| Effective commands | `${device.id}_valve_opening_degree`, percent | `sensor.climate_stijn_valve_opening_degree`, `sensor.climate_nick_valve_opening_degree` present |
| Window | `${device.id}_window`, imported from `${sensor.window}` | `binary_sensor.climate_stijn_window`, `binary_sensor.climate_nick_window` present; user-confirmed sources `binary_sensor.raam_sensor_kamer_stijn_contact` / `binary_sensor.raam_sensor_kamer_nick_contact` |

The raw room import has a heartbeat filter. Observer raw-state callbacks precede
that filter; heartbeat repetitions cannot prove new room measurements. PID reads
the room import, not the separate EMA diagnostic. The EMA template skips NaN
updates, so its previously published finite temperature can remain visible.

The freshness branch's thermostat snapshot rounds heat output to an integer.
Fetched main at 7d925a7 instead uses `roundf(x / 5.0f) * 5.0f`, matching the
user's reported 5% rounding; this resolves the source-version discrepancy.
Both multiply raw output by 100 and clamp. The raw
heat output is already window-adjusted by the output callback. The raw PID
debug sensor is a different stage. Valve-opening percentage is a command,
not position feedback. The freshness example binds `pid_output_*` with scale
100, but the user confirms actual deployed YAML uses the valve commands with
scale 1 for BOTH rooms. Preserve these bindings; export both signals to
investigate changes across historical firmware versions.

## Exact diagnostic entities present in the CSV

Stijn model prefix: `sensor.server_thermostaat_stijn_`

Nick model prefix: `sensor.kamer_nick_adaptive_climate_nick_nick_`

Append `forecast_15min`, `forecast_30min`, `forecast_60min`, `model_status`,
`model_training_samples`, `model_heating_excitation`, `model_residual_rmse`.

Input-health prefixes:
`sensor.kamer_stijn_adaptive_climate_stijn_stijn_` and
`sensor.kamer_nick_adaptive_climate_nick_nick_`.
Append `input_freshness_status`, `room_temperature_input_age`,
`outdoor_temperature_input_age`, `valve_command_input_age`,
`supply_temperature_input_age`. Prefix inconsistency is an entity naming fact,
not proof of different firmware. Keep names exactly as exported.

## Resolve names without changing any firmware

1. Open the actual thermostat configuration and record both `sensor.temperature`,
   `sensor.window`, `master`, climate IDs, observer input IDs and scales, package
   refs and local overrides. Retain the configuration in use during the history
   period, not only today's configuration. Redact secrets before sharing.
2. In HA Settings → Devices & services → ESPHome → thermostat device, locate
   **Heating Temperature**, **Heating Active**, **Hot Water Active**, **Flame On**,
   and both room climates. Copy their exact Entity IDs from entity settings.
   If disabled or excluded from Recorder, historical values may not exist.
3. In Developer Tools → Template, use the following read-only inventory for
   each known thermostat entity (replace the first value). It creates no sensors:

```jinja
{% set anchor = 'sensor.climate_stijn_valve_opening_degree' %}
{% set d = device_id(anchor) %}
{% for entity in device_entities(d) if d %}
{% set s = states[entity] %}
{{ {'entity_id': entity, 'name': s.name, 'state': s.state,
    'unit': s.attributes.get('unit_of_measurement'),
    'last_changed': s.last_changed.isoformat(),
    'last_updated': s.last_updated.isoformat(),
    'last_reported': s.last_reported.isoformat(),
    'temperature': s.attributes.get('temperature'),
    'current_temperature': s.attributes.get('current_temperature'),
    'hvac_action': s.attributes.get('hvac_action')} | to_json }}
{% endfor %}
```

Sub-devices may separate room and boiler entities: repeat using an entity on the
main thermostat device. Copy the state/unit/attributes of both raw room sensors
and the KNMI entities separately. Current metadata does not establish historical
configuration; report any sensor/unit/config changes during the period.

## Historical export

In HA History select **2026-10-30 12:00 through 2026-11-02 13:00 Europe/Amsterdam**
(11:00 through 12:00 UTC), or the latest available end today. Include earlier
history for warm-up if retained. Select all mapped signals above, all listed
diagnostics, `sensor.temperature`, `sensor.knmi_latest_update`, solar irradiance,
wind speed, both TRV local temperatures and ventilation demand/status entities.
Use the upper-right menu → **Download data**. Preserve original CSV timestamps
and unknown/unavailable rows; do not resample in a spreadsheet. Split files by
signal group if necessary, with identical start/end dates.

For climates include state (mode), target `temperature`, `current_temperature`,
`hvac_action`, and range targets if used. Export attribute-only changes too.
If the UI export omits these, supply a full HA Recorder history export with
attributes; a temperature-only graph is insufficient. Include uptime/restart
and connection/availability history if recorded. Do not export credentials.

HA History exports state history, not a guaranteed publication log. Synthetic
start rows do not identify when a forecast was issued. `last_changed` differs
from `last_updated` and `last_reported`. Existing exports cannot reconstruct
identical repeated forecasts, physical sample timestamps, or overwritten issue
times. A captured last_reported is a publication time, not sensor measurement
time. Identify that distinction in provenance. Hourly statistics cannot replace
event history for this experiment.

For future collection retain existing Recorder entities first. A read-only
external collector should log receipt UTC, entity last_changed/updated/reported,
raw value, units and availability, with separate model forecast cycle/issue
identity when verifiable. Include explicit reconnect/gap records; polling cached
states must never reset measurement timestamps. If issue identity is unavailable,
label resulting scores as publication-time approximations, not strict results.
Do not create duplicate sensors just to duplicate existing history.

References: [HA History](https://www.home-assistant.io/integrations/history/),
[HA state timestamps](https://www.home-assistant.io/docs/configuration/state_object/).
